import hashlib
import os
import threading

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
)
from app.ui_qt.choice_widgets import PopupChoice


class _UiDispatcher(QObject):
    run = Signal(object)


class BookProcessingTab(QWidget):
    def __init__(self, set_book_text_cb, go_to_characters_cb, log_debug=None, parent=None):
        super().__init__(parent)
        self.set_book_text_cb = set_book_text_cb
        self.go_to_characters_cb = go_to_characters_cb
        self.log_debug = log_debug or (lambda msg: print(msg))

        self.current_book_path = None
        self.raw_text = ""
        self.chapters = []
        self.font_size_threshold = 1.3
        self._ui_dispatcher = _UiDispatcher(self)
        self._ui_dispatcher.run.connect(self._run_ui_callback)

        self._build_layout()

    def _run_ui_callback(self, fn):
        try:
            fn()
        except Exception as exc:
            self.log_debug(f"[BookProcessingTab] UI callback failed: {exc}")

    def _build_layout(self):
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        right = QVBoxLayout()
        root.addLayout(left, 2)
        root.addLayout(right, 3)

        # Title
        title = QLabel("Book Processing")
        title.setStyleSheet("font-weight: 700; font-size: 12px;")
        left.addWidget(title)

        # Import/Detect controls
        controls = QHBoxLayout()
        left.addLayout(controls)

        import_btn = QPushButton("📖 Import")
        import_btn.clicked.connect(self._import_book)
        controls.addWidget(import_btn)

        detect_btn = QPushButton("🔍 Detect Chapters")
        detect_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: 600; padding: 4px;")
        detect_btn.clicked.connect(self._detect_chapters)
        controls.addWidget(detect_btn)

        controls.addWidget(QLabel("Threshold:"))
        self.threshold_dropdown = PopupChoice()
        self.threshold_dropdown.addItems([
            "Conservative (1.5x)",
            "Balanced (1.3x)",
            "Sensitive (1.2x)",
        ])
        self.threshold_dropdown.setCurrentText("Balanced (1.3x)")
        self.threshold_dropdown.currentTextChanged.connect(self._on_threshold_change)
        self.threshold_dropdown.setMaximumWidth(150)
        controls.addWidget(self.threshold_dropdown)

        # Chapters list
        chapters_label = QLabel("Chapters")
        chapters_label.setStyleSheet("font-weight: 700; font-size: 11px; margin-top: 8px;")
        left.addWidget(chapters_label)

        self.chapter_list = QListWidget()
        self.chapter_list.setSelectionMode(self.chapter_list.SelectionMode.ExtendedSelection)
        self.chapter_list.itemSelectionChanged.connect(self._on_chapter_select)
        left.addWidget(self.chapter_list, 1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        left.addWidget(self.progress_bar)

        # Status + send button
        bottom = QHBoxLayout()
        left.addLayout(bottom)

        self.status_label = QLabel("No book loaded")
        self.status_label.setStyleSheet("font-size: 9px; color: #666;")
        bottom.addWidget(self.status_label, 1)

        send_btn = QPushButton("→ Send to Characters")
        send_btn.setStyleSheet("background-color: #1976D2; color: white; font-weight: 600; padding: 6px;")
        send_btn.clicked.connect(self._send_to_characters)
        bottom.addWidget(send_btn, 0)

        # Preview panel
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight: 700; font-size: 11px;")
        right.addWidget(preview_label)

        self.chapter_preview = QTextEdit()
        self.chapter_preview.setReadOnly(True)
        right.addWidget(self.chapter_preview, 1)

    def _safe_ui(self, fn):
        self._ui_dispatcher.run.emit(fn)

    def _import_book(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open book",
            "",
            "Supported formats (*.txt *.epub *.pdf);;Text (*.txt);;EPUB (*.epub);;PDF (*.pdf)",
        )
        if not file_path:
            return

        self.update_status(f"Loading: {os.path.basename(file_path)}...")
        worker = threading.Thread(target=self._load_book_thread, args=(file_path,), daemon=True)
        worker.start()

    def _load_book_thread(self, file_path):
        try:
            from app.core.chapter_chunker import load_book, smart_chapter_detection

            self.raw_text = load_book(file_path)
            self.current_book_path = file_path
            file_name = os.path.basename(file_path)
            file_size = len(self.raw_text)
            size_kb = file_size / 1024

            self._safe_ui(lambda: self.update_status("⏳ Auto-detecting chapters..."))
            try:
                detected = smart_chapter_detection(
                    self.raw_text,
                    min_chapter_length=1000,
                    max_chunk_size=50000,
                    font_size_threshold=self.font_size_threshold,
                )
                self.chapters = detected or []
            except Exception as detect_exc:
                self.log_debug(f"[BookProcessingTab] Auto-detect failed, using full text fallback: {detect_exc}")
                self.chapters = []

            if not self.chapters:
                # Always provide at least one transferable section.
                self.chapters = [{"title": "Full Book", "text": self.raw_text}]

            chapter_titles = [c.get("title", "Untitled") for c in self.chapters]
            avg_length = sum(len(c.get("text", "")) for c in self.chapters) / len(self.chapters) if self.chapters else 0

            def update():
                self.update_status(
                    f"✓ {file_name} | {len(self.chapters)} chapter(s) detected (avg {avg_length/1000:.1f}K chars)"
                )
                self.update_chapter_list(chapter_titles)
                if self.chapters:
                    self.update_preview(self.chapters[0].get("text", "")[:2000])
                else:
                    self.update_preview(self.raw_text[:2000])
                QMessageBox.information(
                    self,
                    "Book Loaded and Analyzed",
                    (
                        f"Successfully loaded:\n{file_name}\n\n"
                        f"Size: {size_kb:.1f} KB\n"
                        f"Characters: {file_size:,}\n\n"
                        f"Detected sections: {len(self.chapters)}\n\n"
                        "Sections are ready to send to Characters."
                    ),
                )

            self._safe_ui(update)
            self.log_debug(
                f"[BookProcessingTab] Imported and auto-detected: {file_path} "
                f"({size_kb:.1f} KB, {len(self.chapters)} chapters)"
            )
        except ImportError as exc:
            self.log_debug(f"[BookProcessingTab] Missing dependency: {exc}")
            self._safe_ui(
                lambda: QMessageBox.critical(
                    self,
                    "Missing Dependency",
                    (
                        f"Cannot load this file format:\n{exc}\n\n"
                        "Install required packages:\n"
                        "  - For EPUB: pip install ebooklib beautifulsoup4\n"
                        "  - For PDF: pip install PyPDF2"
                    ),
                )
            )
        except Exception as exc:
            self.log_debug(f"[BookProcessingTab] Failed to load file: {exc}")
            self._safe_ui(lambda: QMessageBox.critical(self, "Error", f"Failed to load file:\n{exc}"))

    def _detect_chapters(self):
        if not self.raw_text:
            QMessageBox.warning(self, "No text", "Load a book first.")
            return

        try:
            from app.core.chapter_chunker import smart_chapter_detection

            self.update_status("⏳ Analyzing chapter structure...")
            
            def show_progress():
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            self._safe_ui(show_progress)
            
            detected = smart_chapter_detection(
                self.raw_text,
                min_chapter_length=1000,
                max_chunk_size=50000,
                font_size_threshold=self.font_size_threshold,
            )
            self.chapters = detected
            self.update_chapter_list([c["title"] for c in self.chapters])
            avg_length = sum(len(c["text"]) for c in self.chapters) / len(self.chapters) if self.chapters else 0
            
            def finish():
                self.progress_bar.setVisible(False)
                self.update_status(f"✓ Detected {len(self.chapters)} chapter(s) (avg: {avg_length/1000:.1f}K chars)")
            
            self._safe_ui(finish)
            
            self.log_debug(f"[BookProcessingTab] Detected {len(self.chapters)} chapters")
            QMessageBox.information(
                self,
                "Chapters Detected",
                (
                    f"Found {len(self.chapters)} chapter(s)/section(s)\n\n"
                    f"Average size: {avg_length/1000:.1f}K characters\n\n"
                    "Select chapters and click 'Send to Characters' to continue."
                ),
            )
        except Exception as exc:
            self.log_debug(f"[BookProcessingTab] Chapter detection failed: {exc}")
            self._safe_ui(lambda: self.progress_bar.setVisible(False))
            QMessageBox.critical(self, "Error", f"Chapter detection failed:\n{exc}")

    def _on_threshold_change(self, value: str):
        if "1.5x" in value:
            self.font_size_threshold = 1.5
        elif "1.3x" in value:
            self.font_size_threshold = 1.3
        else:
            self.font_size_threshold = 1.2
        self.log_debug(f"[BookProcessingTab] Font size threshold set to {self.font_size_threshold}x")

    def _on_chapter_select(self):
        selected = self.chapter_list.selectedIndexes()
        if not selected:
            return
        idx = selected[0].row()
        if idx < len(self.chapters):
            self.update_preview(self.chapters[idx]["text"][:20000])

    def _send_to_characters(self):
        if not self.raw_text:
            QMessageBox.warning(self, "No text", "Load a book first.")
            return

        selected_rows = [idx.row() for idx in self.chapter_list.selectedIndexes()]
        book_id = hashlib.sha1((self.raw_text or "").encode("utf-8", errors="ignore")).hexdigest()

        def _clean_section(title: str, text: str):
            clean_text = (text or "").replace("\x00", "").strip()
            return {
                "title": (title or "Untitled").strip() or "Untitled",
                "text": clean_text,
                "book_id": book_id,
            }

        if not self.chapters:
            selected_chapters = [_clean_section("Full Book", self.raw_text)]
        elif not selected_rows:
            # If nothing is selected, transfer all currently detected chapters/sections.
            selected_chapters = [
                _clean_section(c.get("title", "Untitled"), c.get("text", ""))
                for c in self.chapters
            ]
        elif len(selected_rows) > 3:
            QMessageBox.critical(self, "Too Many Chapters", "Please select no more than 3 chapters.")
            return
        else:
            selected_chapters = [
                _clean_section(self.chapters[i].get("title", "Untitled"), self.chapters[i].get("text", ""))
                for i in selected_rows
            ]

        selected_chapters = [c for c in selected_chapters if c.get("text", "").strip()]
        if not selected_chapters:
            QMessageBox.warning(self, "No chapter text", "Selected chapter(s) had no usable text.")
            return

        sizes = ", ".join(f"{c['title']}={len(c['text'])}" for c in selected_chapters[:4])
        if len(selected_chapters) > 4:
            sizes += ", ..."
        self.log_debug(
            f"[BookProcessingTab] Sending {len(selected_chapters)} section(s) to Characters | chars: {sizes}"
        )

        self.set_book_text_cb(selected_chapters)
        self.go_to_characters_cb()

    def update_chapter_list(self, chapters):
        self.chapter_list.clear()
        self.chapter_list.addItems(chapters)

    def update_preview(self, text):
        self.chapter_preview.setPlainText(text)

    def update_status(self, text):
        self.status_label.setText(text)
