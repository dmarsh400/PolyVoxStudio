import json
import hashlib
import threading
import re
import copy
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import List

from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFileDialog,
    QInputDialog,
    QProgressBar,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QLineEdit,
    QSpinBox,
    QFormLayout,
)

from app.core import character_detection
from app.ui_qt.choice_widgets import ChoiceDialog


class _UiDispatcher(QObject):
    run = Signal(object)


class _SplitLineEditor(QTextEdit):
    submit_requested = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and (event.modifiers() & Qt.ControlModifier):
            self.submit_requested.emit()
            return
        super().keyPressEvent(event)


class _SplitLineDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Split Line")
        self.setMinimumWidth(650)

        layout = QVBoxLayout(self)
        label = QLabel("Edit the line, press Enter to split the line where the cursor is, then click OK (or Ctrl+Enter).")
        label.setWordWrap(True)
        layout.addWidget(label)

        self.editor = _SplitLineEditor(self)
        self.editor.setPlainText(text)
        self.editor.submit_requested.connect(self.accept)
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self.editor.toPlainText()


class CharactersTab(QWidget):
    def __init__(self, get_book_text, send_to_voices_cb=None, log_debug=None, gpu_enabled=True, parent=None):
        super().__init__(parent)
        self.get_book_text = get_book_text
        self.send_to_voices_cb = send_to_voices_cb
        self.log_debug = log_debug or (lambda msg: print(msg))
        self.gpu_enabled = gpu_enabled
        self._undo_snapshot = None
        self._undo_description = ""

        self.chapters = []
        self.lines = []
        self.character_order = []
        self.visible_line_indexes = []
        self.speaker_colors = {}
        self.search_query = ""
        self.font_point_size = 10
        self.last_run_export = None
        self.pov_speaker_override = None
        self._sticky_global_priors = {}
        self._sticky_allowed_characters = set()
        self._sticky_pov_speaker = None
        self._sticky_book_id = None
        self._ui_dispatcher = _UiDispatcher(self)
        self._ui_dispatcher.run.connect(self._run_ui_callback)

        self._build_layout()

    def _run_ui_callback(self, fn):
        try:
            fn()
        except Exception as exc:
            self.log_debug(f"[CharactersTab] UI callback failed: {exc}")

    @staticmethod
    def _is_bright(color: QColor) -> bool:
        # Relative luminance approximation for readable foreground selection.
        return (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) > 150

    def _generate_speaker_color(self, index: int) -> QColor:
        # Golden-angle hue stepping gives good spread before reuse.
        hue = int((index * 137.508) % 360)
        return QColor.fromHsv(hue, 215, 255)

    def _rebuild_speaker_colors(self):
        self.speaker_colors = {}
        for i, speaker in enumerate(self.character_order):
            self.speaker_colors[speaker] = self._generate_speaker_color(i)
        # Keep narrator visually distinct but readable in dark mode.
        self.speaker_colors["Narrator"] = QColor("#9E9E9E")
        self.speaker_colors["Unknown"] = QColor("#BDBDBD")

    def _ensure_character_order_from_lines(self):
        # Some attribution runs return sparse/empty character_order; derive from lines to keep UI populated.
        speakers_in_lines = []
        seen = set()
        for row in self.lines:
            speaker = (row.get("speaker") or "Unknown").strip() or "Unknown"
            if speaker not in seen:
                seen.add(speaker)
                speakers_in_lines.append(speaker)

        if not self.character_order:
            self.character_order = speakers_in_lines
            return

        # Preserve detector ordering, append missing speakers from lines.
        for speaker in speakers_in_lines:
            if speaker not in self.character_order:
                self.character_order.append(speaker)

    def _build_layout(self):
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        right = QVBoxLayout()
        root.addLayout(left, 1)
        root.addLayout(right, 3)

        # --- Left Panel: Characters & Controls ---
        chars_label = QLabel("Detected Characters")
        chars_label.setStyleSheet("font-weight: 700; font-size: 11px;")
        left.addWidget(chars_label)

        self.character_list = QListWidget()
        self.character_list.setSelectionMode(self.character_list.SelectionMode.ExtendedSelection)
        left.addWidget(self.character_list, 1)

        # Detection controls
        detect_btn = QPushButton("▶ Detect Characters")
        detect_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: 600; padding: 6px;")
        detect_btn.clicked.connect(self.detect_characters)
        left.addWidget(detect_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        left.addWidget(self.progress_label)

        # Character management
        char_section_label = QLabel("Character Operations")
        char_section_label.setStyleSheet("font-weight: 700; font-size: 11px; margin-top: 10px;")
        left.addWidget(char_section_label)

        add_btn = QPushButton("➕ Add Character")
        add_btn.clicked.connect(self.add_character)
        left.addWidget(add_btn)

        merge_btn = QPushButton("🔗 Merge Selected")
        merge_btn.clicked.connect(self.merge_selected_characters)
        left.addWidget(merge_btn)

        rename_btn = QPushButton("✎ Rename Character")
        rename_btn.clicked.connect(self.rename_character)
        left.addWidget(rename_btn)

        delete_btn = QPushButton("🗑 Delete Selected")
        delete_btn.setStyleSheet("background-color: #C62828; color: white; font-weight: 600; padding: 6px;")
        delete_btn.clicked.connect(self.delete_selected_characters)
        delete_row = QHBoxLayout()
        delete_row.addWidget(delete_btn)

        self.undo_btn = QPushButton("↶ Undo")
        self.undo_btn.setEnabled(False)
        self.undo_btn.setToolTip("Undo the previous character or line operation")
        self.undo_btn.clicked.connect(self.undo_last_operation)
        delete_row.addWidget(self.undo_btn)
        left.addLayout(delete_row)

        # File operations
        file_section_label = QLabel("File Operations")
        file_section_label.setStyleSheet("font-weight: 700; font-size: 11px; margin-top: 10px;")
        left.addWidget(file_section_label)

        save_btn = QPushButton("💾 Save Assignments")
        save_btn.clicked.connect(self.save_assignments)
        left.addWidget(save_btn)

        load_btn = QPushButton("📂 Load Assignments")
        load_btn.clicked.connect(self.load_assignments)
        left.addWidget(load_btn)

        send_btn = QPushButton("→ Send to Voices")
        send_btn.setStyleSheet("background-color: #1976D2; color: white; font-weight: 600; padding: 6px;")
        send_btn.clicked.connect(self.send_to_voices)
        left.addWidget(send_btn)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 10px; color: #666; margin-top: 10px;")
        left.addWidget(self.status_label)

        # --- Right Panel: Lines ---
        line_section_label = QLabel("Dialogue Lines")
        line_section_label.setStyleSheet("font-weight: 700; font-size: 11px; margin-top: 10px;")
        right.addWidget(line_section_label, 0)

        line_settings = QFormLayout()
        right.addLayout(line_settings, 0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search dialogue lines by keyword(s)...")
        self.search_box.textChanged.connect(self._on_search_changed)
        line_settings.addRow("Search:", self.search_box)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 22)
        self.font_size_spin.setValue(self.font_point_size)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        line_settings.addRow("Font Size:", self.font_size_spin)

        line_controls = QHBoxLayout()
        right.addLayout(line_controls, 0)

        split_btn = QPushButton("Split")
        split_btn.setMaximumWidth(70)
        split_btn.clicked.connect(self.split_selected_line)
        line_controls.addWidget(split_btn)

        merge_line_btn = QPushButton("Merge")
        merge_line_btn.setMaximumWidth(70)
        merge_line_btn.clicked.connect(self.merge_selected_lines)
        line_controls.addWidget(merge_line_btn)

        delete_line_btn = QPushButton("Delete")
        delete_line_btn.setMaximumWidth(70)
        delete_line_btn.clicked.connect(self.delete_selected_lines)
        line_controls.addWidget(delete_line_btn)

        self.undo_line_btn = QPushButton("↶ Undo")
        self.undo_line_btn.setEnabled(False)
        self.undo_line_btn.setToolTip("Undo the previous character or line operation")
        self.undo_line_btn.clicked.connect(self.undo_last_operation)
        line_controls.addWidget(self.undo_line_btn)

        reassign_btn = QPushButton("Reassign Speaker")
        reassign_btn.clicked.connect(self.reassign_selected_lines)
        line_controls.addWidget(reassign_btn)

        self.lines_table = QTableWidget(0, 3)
        self.lines_table.setHorizontalHeaderLabels(["Chapter", "Speaker", "Text"])
        self.lines_table.horizontalHeader().setStretchLastSection(True)
        self.lines_table.setSelectionBehavior(self.lines_table.SelectionBehavior.SelectRows)
        self.lines_table.setEditTriggers(self.lines_table.EditTrigger.NoEditTriggers)
        self.lines_table.setAlternatingRowColors(True)
        self.lines_table.setToolTip("Hover over a line to see the full text.")
        right.addWidget(self.lines_table, 1)
        self._apply_font_size()

    def _save_undo_state(self, description: str):
        self._undo_snapshot = (copy.deepcopy(self.lines), list(self.character_order))
        self._undo_description = description
        self.undo_btn.setEnabled(True)
        self.undo_btn.setToolTip(f"Undo: {description}")
        self.undo_line_btn.setEnabled(True)
        self.undo_line_btn.setToolTip(f"Undo: {description}")

    def undo_last_operation(self):
        if self._undo_snapshot is None:
            return
        self.lines, self.character_order = self._undo_snapshot
        description = self._undo_description
        self._undo_snapshot = None
        self._undo_description = ""
        self.undo_btn.setEnabled(False)
        self.undo_btn.setToolTip("Undo the previous character or line operation")
        self.undo_line_btn.setEnabled(False)
        self.undo_line_btn.setToolTip("Undo the previous character or line operation")
        self._rebuild_speaker_colors()
        self._render_all()
        self.log_debug(f"[CharactersTab] Undid: {description}")

    def _safe_ui(self, fn):
        self._ui_dispatcher.run.emit(fn)

    def _apply_font_size(self):
        font = self.font()
        font.setPointSize(self.font_point_size)
        self.setFont(font)

        self.character_list.setFont(font)
        self.lines_table.setFont(font)
        self.lines_table.horizontalHeader().setFont(font)
        self.status_label.setFont(font)
        self.progress_label.setFont(font)
        self.lines_table.verticalHeader().setDefaultSectionSize(max(24, self.font_point_size * 3))

    def _on_font_size_changed(self, value: int):
        self.font_point_size = int(value)
        self._apply_font_size()
        self._render_all()

    def _on_search_changed(self, value: str):
        self.search_query = (value or "").strip().lower()
        self._render_selected_chapter()

    def _matches_search(self, text: str) -> bool:
        if not self.search_query:
            return True
        haystack = (text or "").lower()
        terms = [term for term in self.search_query.replace(",", " ").split() if term]
        if not terms:
            return True
        return all(term in haystack for term in terms)

    def set_book_text(self, chapters):
        self.chapters = chapters or []
        book_ids = {str(ch.get("book_id")) for ch in self.chapters if ch.get("book_id")}
        incoming_book_id = next(iter(book_ids)) if len(book_ids) == 1 else None
        if incoming_book_id and self._sticky_book_id and incoming_book_id != self._sticky_book_id:
            self._sticky_global_priors = {}
            self._sticky_allowed_characters = set()
            self._sticky_pov_speaker = None
            self.pov_speaker_override = None
            self.log_debug("[CharactersTab] New book detected; cleared previous book cast/POV priors")
        if incoming_book_id:
            self._sticky_book_id = incoming_book_id
        self.log_debug(f"[CharactersTab] Received {len(self.chapters)} chapter(s)")

    def detect_characters(self):
        if not self.chapters:
            QMessageBox.warning(self, "No chapters", "Send chapters from Book Processing first.")
            return

        self.status_label.setText("Detecting characters...")
        worker = threading.Thread(target=self._detect_characters_thread, daemon=True)
        worker.start()

    def _confirm_first_person_pov_if_needed(self):
        """Ask for POV speaker confirmation when book appears first-person."""
        book_text = "\n\n".join(
            (ch.get("text") or "")
            for ch in (self.chapters or [])
            if (ch.get("text") or "").strip()
        )
        if not book_text:
            self.pov_speaker_override = None
            return

        if not character_detection.is_first_person_narration(book_text):
            self.pov_speaker_override = None
            return

        value, ok = QInputDialog.getText(
            self,
            "First-Person Narrator Detected",
            "Confirm main POV speaker for first-person quotes (leave blank to auto-detect):",
            text=(self.pov_speaker_override or ""),
        )
        if not ok:
            # Keep previous explicit selection if user cancels.
            return

        normalized = (value or "").strip()
        self.pov_speaker_override = normalized or None

    @staticmethod
    def _looks_first_person_book(text: str) -> bool:
        return character_detection.is_first_person_narration(text)

    def _prompt_pov_speaker_dropdown(self, likely_name: str = ""):
        """Show post-detection POV chooser with current character names."""
        options = [name for name in self.character_order if name not in {"Narrator", "Unknown"}]
        if not options:
            options = []

        # Put likely name first, then current override, then remaining options.
        ordered: List[str] = []
        for preferred in [likely_name, self.pov_speaker_override]:
            if preferred and preferred in options and preferred not in ordered:
                ordered.append(preferred)
        for name in options:
            if name not in ordered:
                ordered.append(name)

        custom_option = "(Add custom name...)"
        menu = ["(Auto detect)", custom_option] + ordered
        default_index = 0
        if self.pov_speaker_override and self.pov_speaker_override in menu:
            default_index = menu.index(self.pov_speaker_override)
        elif likely_name and likely_name in menu:
            default_index = menu.index(likely_name)

        choice, ok = ChoiceDialog.get_item(
            self,
            "First-Person Narrator Detected",
            "Select the main POV character for this book (detection will rerun automatically):",
            menu,
            default_index,
        )
        if not ok:
            return

        if choice == "(Auto detect)":
            self.pov_speaker_override = None
            self.status_label.setText("POV speaker set to auto-detect.")
            return

        if choice == custom_option:
            custom_name, ok = QInputDialog.getText(
                self,
                "Custom Main POV Character",
                "Enter the main POV character name:",
                text=(self.pov_speaker_override or ""),
            )
            if not ok:
                return
            normalized = (custom_name or "").strip()
            if not normalized:
                self.status_label.setText("POV speaker unchanged (empty custom name).")
                return

            self.pov_speaker_override = normalized
            if normalized not in self.character_order:
                self.character_order.append(normalized)
                self._ensure_character_order_from_lines()
                self._rebuild_speaker_colors()
                self._safe_ui(self._render_all)
            self.status_label.setText(f"POV speaker override set to '{normalized}' for this book. Re-running detection...")
            QTimer.singleShot(150, self.detect_characters)
            return

        self.pov_speaker_override = choice
        self.status_label.setText(f"POV speaker override set to '{choice}' for this book. Re-running detection...")
        QTimer.singleShot(150, self.detect_characters)

    @staticmethod
    def _count_name_mentions(text: str, name: str) -> int:
        if not text or not name:
            return 0
        lowered = text.lower()
        parts = [p for p in re.split(r"\s+", name.strip()) if p]
        if not parts:
            return 0

        full = name.lower()
        full_hits = len(re.findall(rf"\b{re.escape(full)}\b", lowered))
        last_hits = 0
        if len(parts) >= 2:
            last_hits = len(re.findall(rf"\b{re.escape(parts[-1].lower())}\b", lowered))

        return (full_hits * 4) + last_hits

    def _detect_characters_thread(self):
        all_lines = []
        all_characters = []
        chapter_debug = []

        book_ids = {str(ch.get("book_id")) for ch in self.chapters if ch.get("book_id")}
        if len(book_ids) == 1:
            book_key = next(iter(book_ids))
        else:
            book_key = None

        # Fall back for callers that supply chapters without a book identity.
        book_signature_parts = []
        for chapter in self.chapters:
            title = chapter.get("title", "")
            text = chapter.get("text", "")
            if text and text.strip():
                book_signature_parts.append(f"{title}:{len(text)}:{text[:200]}")
        if book_key is None and book_signature_parts:
            book_key = hashlib.sha1("|".join(book_signature_parts).encode("utf-8", errors="ignore")).hexdigest()[:16]
        elif book_key is None:
            book_key = None

        try:
            chapter_inputs = [
                ch for ch in self.chapters
                if (ch.get("text") or "").strip()
            ]
            total_chapters = len(chapter_inputs)
            if total_chapters == 0:
                return

            # Pass 1: bootstrap chapter-level detections to build a book-level character prior.
            bootstrap = []
            bootstrap_characters = set()
            bootstrap_quote_counts = Counter()
            bootstrap_quote_conf_sum = Counter()
            combined_book_text = "\n\n".join(ch.get("text", "") for ch in chapter_inputs)
            looks_first_person = self._looks_first_person_book(combined_book_text)

            for idx, chapter in enumerate(chapter_inputs):
                title = chapter.get("title", "Untitled")
                text = chapter.get("text", "")

                def update_progress():
                    total_steps = total_chapters * 2
                    current = idx + 1
                    self.progress_bar.setValue(int((current / total_steps) * 100))
                    self.progress_label.setText(f"Pass 1/2: {idx + 1}/{total_chapters}")
                    self.progress_bar.setVisible(True)
                    self.progress_label.setVisible(True)

                self._safe_ui(update_progress)

                detection = character_detection.run_attribution(
                    text=text,
                    title=title,
                    book_key=book_key,
                    pov_speaker_override=self.pov_speaker_override,
                )
                if detection.get("detection_error"):
                    raise RuntimeError(f"Chapter '{title}': {detection['detection_error']}")
                chapter_lines = detection.get("lines", [])
                char_order = detection.get("character_order", [])

                bootstrap.append((chapter, detection))
                for name in char_order:
                    if isinstance(name, str) and name not in {"Narrator", "Unknown"}:
                        bootstrap_characters.add(name)
                for row in chapter_lines:
                    if not row.get("is_quote"):
                        continue
                    speaker = row.get("speaker")
                    if isinstance(speaker, str) and speaker not in {"Narrator", "Unknown"}:
                        bootstrap_quote_counts[speaker] += 1
                        try:
                            bootstrap_quote_conf_sum[speaker] += float(row.get("speaker_confidence", 0.0) or 0.0)
                        except Exception:
                            pass

            global_mentions = Counter()
            for name in bootstrap_characters:
                q_count = int(bootstrap_quote_counts.get(name, 0))
                conf_sum = float(bootstrap_quote_conf_sum.get(name, 0.0))
                conf_avg = (conf_sum / q_count) if q_count > 0 else 0.0

                # Keep mostly recurring quote speakers; avoid one-off narration mentions
                # becoming globally allowed cast members.
                include = False
                if q_count >= 4:
                    include = True
                elif q_count >= 2 and conf_avg >= 0.52:
                    include = True
                elif q_count >= 1 and self.pov_speaker_override and name == self.pov_speaker_override:
                    include = True

                if not include:
                    continue

                score = self._count_name_mentions(combined_book_text, name)
                if score > 0:
                    global_mentions[name] += score
            for name, cnt in bootstrap_quote_counts.items():
                if name in global_mentions:
                    global_mentions[name] += int(cnt) * 3

            if self.pov_speaker_override:
                global_mentions[self.pov_speaker_override] += 100

            allowed_book_characters = sorted(global_mentions.keys())
            total_global = sum(global_mentions.values())
            global_character_priors = {}
            if total_global > 0:
                global_character_priors = {
                    name: (float(score) / float(total_global))
                    for name, score in global_mentions.items()
                }

            # If chapters are processed one-by-one, carry global priors forward within
            # this UI session so the cast can build across consecutive runs.
            sticky_used = False
            if total_chapters == 1 and self._sticky_global_priors:
                sticky_used = True
                merged_scores = Counter()
                for name, prior in self._sticky_global_priors.items():
                    try:
                        merged_scores[name] += float(prior) * 1000.0
                    except Exception:
                        continue
                for name, prior in global_character_priors.items():
                    try:
                        merged_scores[name] += float(prior) * 1000.0
                    except Exception:
                        continue

                if self.pov_speaker_override:
                    merged_scores[self.pov_speaker_override] += 150.0
                if self._sticky_pov_speaker and self._sticky_pov_speaker == self.pov_speaker_override:
                    merged_scores[self._sticky_pov_speaker] += 80.0

                merged_allowed = set(self._sticky_allowed_characters)
                merged_allowed.update(allowed_book_characters)

                total_merged = float(sum(merged_scores.values()))
                if total_merged > 0:
                    global_character_priors = {
                        name: (float(score) / total_merged)
                        for name, score in merged_scores.items()
                        if score > 0
                    }
                allowed_book_characters = sorted(
                    name for name in merged_allowed if name in global_character_priors
                )

            # Refresh sticky cache for subsequent chapter-by-chapter runs.
            self._sticky_global_priors = dict(global_character_priors)
            self._sticky_allowed_characters = set(allowed_book_characters)
            self._sticky_pov_speaker = self.pov_speaker_override

            # Pass 2: final detections constrained/scored by global cast priors.
            for idx, chapter in enumerate(chapter_inputs):
                title = chapter.get("title", "Untitled")
                text = chapter.get("text", "")

                def update_progress_pass2():
                    total_steps = total_chapters * 2
                    current = total_chapters + idx + 1
                    self.progress_bar.setValue(int((current / total_steps) * 100))
                    self.progress_label.setText(f"Pass 2/2: {idx + 1}/{total_chapters}")
                    self.progress_bar.setVisible(True)
                    self.progress_label.setVisible(True)

                self._safe_ui(update_progress_pass2)

                detection = character_detection.run_attribution(
                    text=text,
                    title=title,
                    book_key=book_key,
                    global_character_priors=global_character_priors,
                    allowed_book_characters=allowed_book_characters,
                    pov_speaker_override=self.pov_speaker_override,
                )
                if detection.get("detection_error"):
                    raise RuntimeError(f"Chapter '{title}': {detection['detection_error']}")
                chapter_lines = detection.get("lines", [])
                char_order = detection.get("character_order", [])
                chapter_unknown_diag = detection.get("unknown_diagnostics", [])
                chapter_unknown_summary = detection.get("unknown_diagnostics_summary", {})
                chapter_main_inference = detection.get("main_character_inference", {})

                self.log_debug(
                    f"[CharactersTab] Chapter '{title}' input={len(text)} chars output={len(chapter_lines)} lines"
                )

                chapter_debug.append({
                    "title": title,
                    "input_characters": len(text),
                    "output_lines": len(chapter_lines),
                    "character_order": list(char_order),
                    "unknown_diagnostics_summary": chapter_unknown_summary,
                    "unknown_diagnostics": chapter_unknown_diag,
                    "main_character_inference": chapter_main_inference,
                    "lines": chapter_lines,
                })

                for row in chapter_lines:
                    all_lines.append({
                        "chapter": title,
                        "speaker": row.get("speaker", "Unknown"),
                        "text": row.get("text", ""),
                        "is_quote": bool(row.get("is_quote", False)),
                    })

                for name in char_order:
                    if name not in all_characters:
                        all_characters.append(name)

            self.lines = all_lines
            self.character_order = all_characters
            self._ensure_character_order_from_lines()
            self._rebuild_speaker_colors()

            self._safe_ui(self._render_all)

            # Offer post-detection POV choice once for first-person books.
            # If an override is already set, keep reusing it across chapter runs.
            if looks_first_person and self.character_order:
                quote_counts = Counter(
                    row.get("speaker")
                    for row in self.lines
                    if row.get("is_quote") and row.get("speaker") not in {"Narrator", "Unknown"}
                )
                likely = ""
                if quote_counts:
                    likely = quote_counts.most_common(1)[0][0]
                if self.pov_speaker_override:
                    if self.pov_speaker_override in self.character_order:
                        self._safe_ui(
                            lambda current=self.pov_speaker_override: self.status_label.setText(
                                f"Using saved POV speaker '{current}' for this book."
                            )
                        )
                else:
                    self._safe_ui(lambda likely=likely: self._prompt_pov_speaker_dropdown(likely))

            run_payload = {
                "character_order": list(self.character_order),
                "line_count": len(self.lines),
                "chapter_count": len(chapter_debug),
                "lines": list(self.lines),
                "pov_speaker_override": self.pov_speaker_override,
                "sticky_global_used": bool(sticky_used),
                "sticky_global_size": len(self._sticky_allowed_characters),
                "book_level_character_priors": dict(sorted(global_character_priors.items(), key=lambda kv: kv[1], reverse=True)[:25]),
                "unknown_diagnostics_summary": {
                    "total_unknown_quotes": sum(
                        int(ch.get("unknown_diagnostics_summary", {}).get("total_unknown_quotes", 0))
                        for ch in chapter_debug
                    ),
                    "reasons": {},
                },
                "chapters": chapter_debug,
            }

            aggregated_reasons = {}
            for chapter_info in chapter_debug:
                reasons = chapter_info.get("unknown_diagnostics_summary", {}).get("reasons", {})
                if not isinstance(reasons, dict):
                    continue
                for reason, count in reasons.items():
                    try:
                        aggregated_reasons[reason] = aggregated_reasons.get(reason, 0) + int(count)
                    except Exception:
                        continue
            run_payload["unknown_diagnostics_summary"]["reasons"] = aggregated_reasons
            out_path = self._export_detection_run(run_payload)
            if out_path:
                self.log_debug(f"[CharactersTab] GUI run saved: {out_path}")

            self.log_debug(
                f"[CharactersTab] Detection complete: {len(self.character_order)} characters, {len(self.lines)} lines"
            )
        except Exception as exc:
            self.log_debug(f"[CharactersTab] Detection failed: {exc}")
            err_text = str(exc)
            self._safe_ui(lambda err_text=err_text: QMessageBox.critical(self, "Error", f"Character detection failed:\n{err_text}"))

    def _render_all(self):
        self._ensure_character_order_from_lines()
        self._rebuild_speaker_colors()
        self.character_list.clear()
        for speaker in self.character_order:
            item = QListWidgetItem(speaker)
            color = self.speaker_colors.get(speaker, QColor("#FFFFFF"))
            item.setBackground(color)
            item.setForeground(QColor("#111111") if self._is_bright(color) else QColor("#FFFFFF"))
            item.setFont(self.character_list.font())
            self.character_list.addItem(item)
        self._render_selected_chapter(force_all=True)
        self.status_label.setText(f"✓ Detected {len(self.character_order)} characters across {len(self.lines)} lines")
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    def _export_detection_run(self, payload):
        """Write the latest detection output to a timestamped folder for debugging/sharing."""
        try:
            root = Path(__file__).resolve().parents[2]
            base_dir = root / "output" / "gui_runs"
            base_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"{timestamp}_{uuid4().hex[:6]}"
            run_dir = base_dir / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            payload = dict(payload or {})
            payload["run_id"] = run_id
            payload["generated_at"] = datetime.now().isoformat()

            out_path = run_dir / "gui_output.txt"
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

            self.last_run_export = str(out_path)
            self.log_debug(f"[CharactersTab] Exported GUI detection output to {out_path}")
            return out_path
        except Exception as exc:
            self.last_run_export = None
            self.log_debug(f"[CharactersTab] Failed to export GUI detection output: {exc}")
            return None

    def _render_selected_chapter(self, force_all=False):
        filtered = [
            (idx, row)
            for idx, row in enumerate(self.lines)
            if self._matches_search(row.get("text", "")) or self._matches_search(row.get("speaker", ""))
        ]

        self.visible_line_indexes = [idx for idx, _ in filtered]
        self.lines_table.setRowCount(len(filtered))
        for i, (_, row) in enumerate(filtered):
            speaker = row.get("speaker", "")
            speaker_color = self.speaker_colors.get(speaker)
            full_text = row.get("text", "")

            chapter_item = QTableWidgetItem(row.get("chapter", ""))
            speaker_item = QTableWidgetItem(speaker)
            text_item = QTableWidgetItem(full_text)

            for item in (chapter_item, speaker_item, text_item):
                item.setToolTip(full_text)
                item.setFont(self.lines_table.font())

            if speaker_color:
                speaker_fg = QColor("#111111") if self._is_bright(speaker_color) else QColor("#FFFFFF")
                chapter_bg = QColor(speaker_color).darker(120)
                chapter_fg = QColor("#111111") if self._is_bright(chapter_bg) else QColor("#FFFFFF")

                speaker_item.setBackground(speaker_color)
                speaker_item.setForeground(speaker_fg)

                chapter_item.setBackground(chapter_bg)
                chapter_item.setForeground(chapter_fg)
                chapter_font = chapter_item.font()
                chapter_font.setBold(True)
                chapter_item.setFont(chapter_font)

                # Use a darker tint in text column to preserve readability and emphasis.
                text_bg = QColor(speaker_color)
                text_bg = text_bg.darker(155)
                text_item.setBackground(text_bg)
                text_item.setForeground(QColor("#F5F5F5"))

            self.lines_table.setItem(i, 0, chapter_item)
            self.lines_table.setItem(i, 1, speaker_item)
            self.lines_table.setItem(i, 2, text_item)

    def send_to_voices(self):
        if not self.lines:
            QMessageBox.warning(self, "No lines", "Run detection before sending to Voices.")
            return
        if self.send_to_voices_cb:
            self.send_to_voices_cb(self.character_order, self.lines, self.speaker_colors)
        QMessageBox.information(self, "Sent", "Detected lines were sent to Voices tab.")

    def save_assignments(self):
        if not self.lines:
            QMessageBox.warning(self, "Nothing to save", "No detected lines to save.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save assignments", "characters_assignments.json", "JSON (*.json)")
        if not path:
            return

        payload = {
            "characters": self.character_order,
            "lines": self.lines,
        }
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.status_label.setText(f"✓ Saved assignments to {Path(path).name}")

    def load_assignments(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load assignments", "", "JSON (*.json)")
        if not path:
            return

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._save_undo_state("load assignments")
        self.character_order = data.get("characters", [])
        self.lines = data.get("lines", [])
        self._ensure_character_order_from_lines()
        self._rebuild_speaker_colors()

        self._render_all()
        self.status_label.setText(f"✓ Loaded assignments from {Path(path).name}")

    def merge_selected_characters(self):
        selected = self.character_list.selectedItems()
        if len(selected) < 2:
            QMessageBox.warning(self, "Select 2+", "Select at least 2 characters to merge.")
            return
        selected_names = sorted({item.text() for item in selected})
        merged_name, ok = ChoiceDialog.get_item(
            self,
            "Merge Characters",
            "Choose the character name to keep:",
            selected_names,
            0,
        )
        if not ok or not merged_name.strip():
            return
        self._save_undo_state("merge characters")
        selected_names = set(selected_names)
        for line in self.lines:
            if line.get("speaker") in selected_names:
                line["speaker"] = merged_name
        self.character_order = [n for n in self.character_order if n not in selected_names]
        if merged_name not in self.character_order:
            self.character_order.insert(0, merged_name)
        self._rebuild_speaker_colors()
        self._render_all()
        self.log_debug(f"[CharactersTab] Merged {len(selected_names)} characters → '{merged_name}'")

    def add_character(self):
        name, ok = QInputDialog.getText(self, "Add Character", "Character name:")
        if not ok:
            return

        new_name = (name or "").strip()
        if not new_name:
            QMessageBox.warning(self, "Invalid name", "Character name cannot be empty.")
            return
        if new_name in self.character_order:
            QMessageBox.information(self, "Already exists", f"'{new_name}' is already in the character list.")
            return

        self._save_undo_state("add character")
        self.character_order.append(new_name)
        self._rebuild_speaker_colors()
        self._render_all()
        self.log_debug(f"[CharactersTab] Added character '{new_name}'")

    def rename_character(self):
        selected = self.character_list.selectedItems()
        if len(selected) != 1:
            QMessageBox.warning(self, "Select 1", "Select exactly one character to rename.")
            return
        old_name = selected[0].text()
        new_name, ok = QInputDialog.getText(self, "Rename", f"New name for '{old_name}':")
        if not ok or not new_name.strip():
            return
        self._save_undo_state("rename character")
        for line in self.lines:
            if line.get("speaker") == old_name:
                line["speaker"] = new_name
        idx = self.character_order.index(old_name)
        self.character_order[idx] = new_name
        self._rebuild_speaker_colors()
        self._render_all()
        self.log_debug(f"[CharactersTab] Renamed '{old_name}' → '{new_name}'")

    def delete_selected_characters(self):
        selected = self.character_list.selectedItems()
        if not selected:
            return
        names = {item.text() for item in selected}
        affected_lines = sum(1 for line in self.lines if line.get("speaker") in names)
        reply = QMessageBox.question(
            self,
            "Delete Characters",
            f"Delete {len(names)} selected character(s) and {affected_lines} associated line(s)? You can undo this once.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._save_undo_state("delete characters")
        self.lines = [l for l in self.lines if l.get("speaker") not in names]
        self.character_order = [n for n in self.character_order if n not in names]
        self._rebuild_speaker_colors()
        self._render_all()
        self.log_debug(f"[CharactersTab] Deleted {len(names)} character(s)")

    def _selected_source_rows(self):
        table_rows = sorted(set(idx.row() for idx in self.lines_table.selectedIndexes()))
        source_rows = []
        for row in table_rows:
            if 0 <= row < len(self.visible_line_indexes):
                source_rows.append(self.visible_line_indexes[row])
        return source_rows

    def split_selected_line(self):
        source_rows = self._selected_source_rows()
        if not source_rows:
            QMessageBox.warning(self, "No selection", "Select a line to split.")
            return
        row = source_rows[0]
        if row < len(self.lines):
            dialog = _SplitLineDialog(self.lines[row].get("text", ""), self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            edited_text = dialog.text().replace("\r\n", "\n").strip()
            if not edited_text:
                QMessageBox.warning(self, "Invalid split", "The edited line cannot be empty.")
                return

            parts = [part.strip() for part in edited_text.split("\n", 1)]
            if len(parts) < 2 or not parts[0] or not parts[1]:
                QMessageBox.warning(
                    self,
                    "Split Required",
                    "Insert a newline in the box to split the line into two parts.",
                )
                return

            original = self.lines[row].copy()
            first_line = original.copy()
            second_line = original.copy()
            first_line["text"] = parts[0]
            second_line["text"] = parts[1]
            self._save_undo_state("split line")
            self.lines[row] = first_line
            self.lines.insert(row + 1, second_line)
            self._render_selected_chapter()
            self.log_debug(f"[CharactersTab] Split line {row}")

    def merge_selected_lines(self):
        rows = self._selected_source_rows()
        if len(rows) < 2:
            QMessageBox.warning(self, "Select 2+", "Select at least 2 consecutive lines to merge.")
            return
        if rows[-1] - rows[0] + 1 != len(rows):
            QMessageBox.warning(self, "Non-contiguous", "Selected lines must be consecutive.")
            return
        self._save_undo_state("merge lines")
        merged_text = " ".join(self.lines[r].get("text", "") for r in rows)
        self.lines[rows[0]]["text"] = merged_text
        for r in sorted(rows[1:], reverse=True):
            del self.lines[r]
        self._render_selected_chapter()
        self.log_debug(f"[CharactersTab] Merged {len(rows)} lines")

    def delete_selected_lines(self):
        rows = sorted(self._selected_source_rows(), reverse=True)
        if not rows:
            return
        reply = QMessageBox.question(
            self,
            "Delete Lines",
            f"Delete {len(rows)} selected line(s)? You can undo this once.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._save_undo_state("delete lines")
        for r in rows:
            if 0 <= r < len(self.lines):
                del self.lines[r]
        self._render_selected_chapter()
        self.log_debug(f"[CharactersTab] Deleted {len(rows)} line(s)")

    def reassign_selected_lines(self):
        rows = self._selected_source_rows()
        if not rows:
            QMessageBox.warning(self, "No selection", "Select lines to reassign.")
            return
        options = sorted(self.character_order)
        speaker, ok = ChoiceDialog.get_item(self, "Reassign Speaker", "Choose speaker:", options)
        if ok:
            self._save_undo_state("reassign speaker")
            for r in rows:
                if 0 <= r < len(self.lines):
                    self.lines[r]["speaker"] = speaker
            if speaker not in self.character_order:
                self.character_order.append(speaker)
            self._rebuild_speaker_colors()
            self.log_debug(f"[CharactersTab] Reassigned {len(rows)} line(s) to '{speaker}'")
            self._render_all()
