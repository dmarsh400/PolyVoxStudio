import os
import re
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QSpinBox,
)
from pydub import AudioSegment

from app.core.voices import synthesize_text


class _UiDispatcher(QObject):
    run = Signal(object)


class AudioProcessingTab(QWidget):
    def __init__(self, log_debug=None, parent=None):
        super().__init__(parent)
        self.log_debug = log_debug or (lambda msg: print(msg))
        self.jobs = []
        self.processing = False
        self.output_root = Path("output/audio")
        self.start_time = None
        self.max_retries = 2
        self._ui_dispatcher = _UiDispatcher(self)
        self._ui_dispatcher.run.connect(self._run_ui_callback)

        self._build_layout()

    def _run_ui_callback(self, fn):
        try:
            fn()
        except Exception as exc:
            self.log_debug(f"[AudioProcessingTab] UI callback failed: {exc}")

    def _build_layout(self):
        layout = QVBoxLayout(self)

        title = QLabel("Audio Processing")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status + controls
        controls = QHBoxLayout()
        layout.addLayout(controls)

        start_btn = QPushButton("▶ Start")
        start_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: 600; padding: 6px;")
        start_btn.clicked.connect(self.start_processing)
        controls.addWidget(start_btn)

        stop_btn = QPushButton("⏹ Stop")
        stop_btn.clicked.connect(self.stop_processing)
        controls.addWidget(stop_btn)

        clear_btn = QPushButton("🗑 Clear Queue")
        clear_btn.clicked.connect(self.clear_queue)
        controls.addWidget(clear_btn)

        controls.addWidget(QLabel("Max Retries:"))
        self.retry_spin = QSpinBox()
        self.retry_spin.setValue(self.max_retries)
        self.retry_spin.setRange(0, 5)
        self.retry_spin.valueChanged.connect(lambda v: setattr(self, 'max_retries', v))
        self.retry_spin.setMaximumWidth(60)
        controls.addWidget(self.retry_spin)

        out_btn = QPushButton("📂 Open Output")
        out_btn.setToolTip("Open the folder containing exported chapter audio")
        out_btn.clicked.connect(self.open_output_folder)
        controls.addWidget(out_btn)

        choose_out_btn = QPushButton("Change…")
        choose_out_btn.setToolTip("Choose the root folder for generated audio")
        choose_out_btn.clicked.connect(self.select_output_folder)
        controls.addWidget(choose_out_btn)

        # Jobs table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Speaker", "Text Preview", "Status", "Retries"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 70)
        layout.addWidget(self.table, 1)

        # Status display
        self.status = QLabel("Ready")
        self.status.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.status, 0)

    @staticmethod
    def _style_status_item(item: QTableWidgetItem, normalized_status: str):
        if normalized_status in {"done", "\u2713 done"}:
            item.setBackground(QColor("#2E7D32"))
            item.setForeground(QColor("#FFFFFF"))
        elif "failed" in normalized_status:
            item.setBackground(QColor("#C62828"))
            item.setForeground(QColor("#FFFFFF"))
        elif normalized_status == "processing":
            item.setBackground(QColor("#1565C0"))
            item.setForeground(QColor("#FFFFFF"))
        elif normalized_status.startswith("retry"):
            item.setBackground(QColor("#0D47A1"))
            item.setForeground(QColor("#FFFFFF"))

    def _safe_ui(self, fn):
        self._ui_dispatcher.run.emit(fn)

    def add_jobs(self, jobs):
        for job in jobs:
            job.setdefault("retries", 0)
        self.jobs.extend(jobs)
        self._render_jobs()
        self.status.setText(f"Queue size: {len(self.jobs)}")

    def _render_jobs(self):
        self.table.setRowCount(len(self.jobs))
        for i, job in enumerate(self.jobs):
            status_text = job.get("status", "queued")
            retries = job.get("retries", 0)
            
            self.table.setItem(i, 0, QTableWidgetItem(str(job.get("idx", i))))
            self.table.setItem(i, 1, QTableWidgetItem(job.get("speaker", "Unknown")))
            
            text_preview = job.get("text", "")[:80]
            self.table.setItem(i, 2, QTableWidgetItem(text_preview))
            
            status_item = QTableWidgetItem(status_text)
            self._style_status_item(status_item, status_text.lower())
            self.table.setItem(i, 3, status_item)
            
            self.table.setItem(i, 4, QTableWidgetItem(str(retries)))

    def _set_job_status(self, row, status):
        if 0 <= row < self.table.rowCount():
            status_item = QTableWidgetItem(status)
            normalized = status.lower()
            self._style_status_item(status_item, normalized)
            self.table.setItem(row, 3, status_item)

    def _set_job_retries(self, row, retries):
        if 0 <= row < self.table.rowCount():
            self.table.setItem(row, 4, QTableWidgetItem(str(retries)))

    @staticmethod
    def _safe_name(value: str) -> str:
        raw = (value or "Chapter_Unknown").strip()
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
        return cleaned.strip("_") or "Chapter_Unknown"

    def _merge_wavs_to_mp3(self, wav_files, output_mp3: Path) -> bool:
        if not wav_files:
            return False
        try:
            merged = AudioSegment.empty()
            for wav_path in wav_files:
                if not wav_path.exists():
                    continue
                merged += AudioSegment.from_wav(str(wav_path))
            if len(merged) == 0:
                return False
            output_mp3.parent.mkdir(parents=True, exist_ok=True)
            merged.export(str(output_mp3), format="mp3")
            return True
        except Exception as exc:
            self.log_debug(f"[AudioProcessingTab] Failed to merge chapter MP3 {output_mp3.name}: {exc}")
            return False

    def _consolidate_chapter_mp3s(self, chapter_wavs, chapter_order):
        chapters_dir = self.output_root / "chapters"
        chapters_dir.mkdir(parents=True, exist_ok=True)

        exported = 0
        for chapter_idx, chapter_name in enumerate(chapter_order, start=1):
            wav_files = sorted(chapter_wavs.get(chapter_name, []), key=lambda t: t[0])
            wav_paths = [path for _, path in wav_files]
            output_mp3 = chapters_dir / f"Chapter{chapter_idx}.mp3"
            if self._merge_wavs_to_mp3(wav_paths, output_mp3):
                exported += 1
                self.log_debug(
                    f"[AudioProcessingTab] Exported {output_mp3.name} from chapter '{chapter_name}' "
                    f"with {len(wav_paths)} line(s)"
                )

        return exported

    def start_processing(self):
        if self.processing:
            return
        if not self.jobs:
            QMessageBox.warning(self, "No jobs", "Queue is empty.")
            return

        self.processing = True
        self.start_time = time.time()
        
        def show_progress():
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
        self._safe_ui(show_progress)
        
        worker = threading.Thread(target=self._process_jobs_thread, daemon=True)
        worker.start()

    def _process_jobs_thread(self):
        self.output_root.mkdir(parents=True, exist_ok=True)
        total = len(self.jobs)
        completed = 0
        times = []
        chapter_wavs = {}
        chapter_order = []

        for i, job in enumerate(self.jobs):
            if not self.processing:
                break

            attempt = 0
            success = False
            
            while attempt <= self.max_retries and not success:
                voice_entry = job.get("voice_entry", {})
                speaker = job.get("speaker", "Unknown")
                text = job.get("text", "")
                chapter_name = job.get("chapter", "Chapter_Unknown")
                chapter_slug = self._safe_name(chapter_name)
                out_dir = self.output_root / "lines" / chapter_slug
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"line_{i:05d}_{speaker.replace(' ', '_')}.wav"

                self._safe_ui(lambda idx=i: self._set_job_status(idx, "processing"))
                job_start = time.time()
                
                try:
                    synthesize_text(
                        voice_entry=voice_entry,
                        text=text,
                        out_path=str(out_path),
                        job_idx=i,
                        speaker_name=speaker,
                        emotion=job.get("emotion"),
                        emotion_intensity=job.get("emotion_intensity", 1.0),
                    )
                    job["status"] = "done"
                    self._safe_ui(lambda idx=i: self._set_job_status(idx, "✓ done"))
                    success = True
                    
                    elapsed = time.time() - job_start
                    times.append(elapsed)
                    if chapter_name not in chapter_order:
                        chapter_order.append(chapter_name)
                    chapter_wavs.setdefault(chapter_name, []).append((i, out_path))
                    self._safe_ui(lambda idx=i: self._set_job_status(idx, "done"))
                    completed += 1
                    
                except Exception as exc:
                    attempt += 1
                    job["retries"] = attempt
                    self._safe_ui(lambda idx=i, retries=attempt: self._set_job_retries(idx, retries))
                    
                    if attempt > self.max_retries:
                        job["status"] = f"failed: {str(exc)[:40]}"
                        self._safe_ui(lambda idx=i, msg=str(exc): self._set_job_status(idx, f"✗ failed"))
                        self.log_debug(f"[AudioProcessingTab] Failed job {i} after {attempt} attempts: {exc}")
                    else:
                        msg = f"retry {attempt}/{self.max_retries}"
                        self._safe_ui(lambda idx=i, m=msg: self._set_job_status(idx, m))
                        self.log_debug(f"[AudioProcessingTab] Retrying job {i}: {exc}")

            # Update progress bar and ETA
            progress_pct = int((completed / total) * 100)
            eta_text = ""
            if times:
                avg_time = sum(times) / len(times)
                remaining = (total - completed) * avg_time
                eta_text = f" | ETA: ~{int(remaining)}s"
            
            def update_progress():
                self.progress_bar.setValue(progress_pct)
                self.status.setText(f"Processed {completed}/{total}{eta_text}")
            
            self._safe_ui(
                lambda pct=progress_pct, done=completed, total_jobs=total, eta=eta_text:
                (
                    self.progress_bar.setValue(pct),
                    self.status.setText(f"Processed {done}/{total_jobs}{eta}")
                )
            )

        consolidated_count = 0
        if chapter_order:
            self._safe_ui(lambda: self.status.setText("Consolidating chapter MP3 files..."))
            consolidated_count = self._consolidate_chapter_mp3s(chapter_wavs, chapter_order)

        self.processing = False
        
        def finish(exported=consolidated_count):
            self.progress_bar.setVisible(False)
            done_count = sum(1 for j in self.jobs if j.get("status") == "done")
            self.status.setText(
                f"✓ Finished: {done_count}/{total} completed | Chapter MP3s: {exported} in {self.output_root / 'chapters'}"
            )
        
        self._safe_ui(finish)

    def stop_processing(self):
        self.processing = False
        self.status.setText("Stopping...")

    def clear_queue(self):
        if self.processing:
            QMessageBox.warning(self, "Busy", "Stop processing before clearing queue.")
            return
        self.jobs.clear()
        self._render_jobs()
        self.status.setText("Queue cleared")

    def select_output_folder(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            str(self.output_root.resolve()),
        )
        if directory:
            self.output_root = Path(directory)
            self.status.setText(f"Output folder: {self.output_root}")

    def open_output_folder(self):
        output_dir = self.output_root / "chapters"
        output_dir.mkdir(parents=True, exist_ok=True)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir.resolve())))
        if not opened:
            QMessageBox.warning(self, "Unable to open folder", f"Could not open: {output_dir.resolve()}")
            return
        self.status.setText(f"Chapter audio folder: {output_dir.resolve()}")
