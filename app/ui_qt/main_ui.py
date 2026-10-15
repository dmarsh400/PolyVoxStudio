import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QPushButton,
)
from PySide6.QtCore import QObject, Signal, Qt

from app.ui_qt.book_processing_tab import BookProcessingTab
from app.ui_qt.characters_tab import CharactersTab
from app.ui_qt.voices_tab import VoicesTab
from app.ui_qt.audio_processing_tab import AudioProcessingTab
from app.ui_qt.gpu_monitor_tab import GpuMonitorTab
from app.ui_qt.debug_tab import DebugTab
from app.ui_qt.settings_tab import SettingsTab
from app.ui_qt.clone_voices_tab import CloneVoicesTab


def get_stylesheet_dark():
    """Modern dark theme stylesheet."""
    return """
    QMainWindow, QWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    QTabWidget::pane {
        border: 1px solid #404040;
    }
    QTabBar::tab {
        background-color: #2d2d2d;
        color: #e0e0e0;
        padding: 8px 16px;
        border: 1px solid #404040;
    }
    QTabBar::tab:selected {
        background-color: #1976D2;
        color: white;
        border-bottom: 3px solid #1976D2;
    }
    QTabBar::tab:hover {
        background-color: #404040;
    }
    QPushButton {
        background-color: #404040;
        color: #e0e0e0;
        border: 1px solid #505050;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #505050;
    }
    QPushButton:pressed {
        background-color: #1976D2;
    }
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #404040;
        border-radius: 4px;
        padding: 6px;
    }
    /* NOTE: do NOT style QComboBox QAbstractItemView here.
       On X11 that rule prevents combo popups from ever mapping. */
    QListWidget, QTableWidget {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #404040;
        gridline-color: #404040;
    }
    QListWidget::item:selected, QTableWidget::item:selected {
        background-color: #1976D2;
    }
    QListWidget::item:hover, QTableWidget::item:hover {
        background-color: #404040;
    }
    QHeaderView::section {
        background-color: #404040;
        color: #e0e0e0;
        padding: 6px;
        border: 1px solid #505050;
    }
    QProgressBar {
        border: 1px solid #404040;
        border-radius: 4px;
        background-color: #2d2d2d;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #4CAF50;
    }
    QLabel {
        color: #e0e0e0;
    }
    QMessageBox {
        background-color: #1e1e1e;
    }
    """


class _LogDispatcher(QObject):
    """Marshals log messages from any thread onto the Qt main thread."""
    message = Signal(str)


class PolyVoxApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PolyVox Studio v3.0")
        self.resize(1280, 860)

        # Apply modern dark theme stylesheet
        self.setStyleSheet(get_stylesheet_dark())

        self.gpu_enabled = True
        self.chapters = []

        self.book_processing_tab = None
        self.characters_tab = None
        self.voices_tab = None
        self.audio_processing_tab = None
        self.clone_voices_tab = None
        self.gpu_tab = None
        self.debug_tab = None
        self.settings_tab = None

        # Background worker threads (e.g. audio synthesis) call log_debug();
        # route it through a signal so QTextEdit is only ever touched on the GUI thread.
        self._log_dispatcher = _LogDispatcher(self)
        self._log_dispatcher.message.connect(self._handle_log_message, Qt.ConnectionType.QueuedConnection)

        self.notebook = QTabWidget()
        self.setCentralWidget(self.notebook)

        self.build_book_processing_tab()
        self.build_characters_tab()
        self.build_voices_tab()
        self.build_audio_processing_tab()
        self.build_clone_voices_tab()
        self.build_gpu_tab()
        self.build_debug_tab()
        self.build_settings_tab()

    def build_book_processing_tab(self):
        self.book_processing_tab = BookProcessingTab(
            set_book_text_cb=self.set_book_text,
            go_to_characters_cb=lambda: self.notebook.setCurrentWidget(self.characters_tab),
            log_debug=self.log_debug,
        )
        self.notebook.addTab(self.book_processing_tab, "Book Processing")

    def build_characters_tab(self):
        self.characters_tab = CharactersTab(
            get_book_text=lambda: self.chapters,
            send_to_voices_cb=self._send_lines_to_voices,
            log_debug=self.log_debug,
            gpu_enabled=lambda: self.gpu_enabled,
        )
        self.notebook.addTab(self.characters_tab, "Characters")

    def build_voices_tab(self):
        self.voices_tab = VoicesTab(debug_callback=self.log_debug)
        self.notebook.addTab(self.voices_tab, "Voices")

    def build_audio_processing_tab(self):
        self.audio_processing_tab = AudioProcessingTab(log_debug=self.log_debug)
        self.notebook.addTab(self.audio_processing_tab, "Audio Processing")
        if self.voices_tab:
            self.voices_tab.audio_tab = self.audio_processing_tab
            self.log_debug("[MainUI] Linked VoicesTab -> AudioProcessingTab")

    def build_clone_voices_tab(self):
        self.clone_voices_tab = CloneVoicesTab()
        self.notebook.addTab(self.clone_voices_tab, "Clone Voices")

    def build_gpu_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        toggle_btn = QPushButton("Toggle GPU Debug")
        toggle_btn.clicked.connect(self.toggle_gpu)
        layout.addWidget(toggle_btn)

        self.gpu_tab = GpuMonitorTab(log_debug=self.log_debug)
        layout.addWidget(self.gpu_tab)

        self.notebook.addTab(container, "GPU Monitor")

    def build_debug_tab(self):
        self.debug_tab = DebugTab()
        self.notebook.addTab(self.debug_tab, "Debug")

    def build_settings_tab(self):
        self.settings_tab = SettingsTab(
            gpu_tab=self.gpu_tab,
            voices_tab=self.voices_tab,
            log_debug=self.log_debug,
            change_appearance_mode=self.change_appearance_mode,
        )
        self.notebook.addTab(self.settings_tab, "Settings")

    def _send_lines_to_voices(self, characters, lines, character_colors=None):
        if self.voices_tab:
            self.voices_tab.load_character_lines(characters, lines, character_colors)
            self.notebook.setCurrentWidget(self.voices_tab)

    def set_book_text(self, chapters):
        self.chapters = chapters
        if self.characters_tab:
            self.characters_tab.set_book_text(chapters)

    def log_debug(self, message: str):
        # Safe to call from any thread: emitting queues delivery onto the GUI thread.
        print(message)
        self._log_dispatcher.message.emit(message)

    def _handle_log_message(self, message: str):
        if self.debug_tab:
            self.debug_tab.log(message)

    def toggle_gpu(self):
        self.gpu_enabled = not self.gpu_enabled
        self.log_debug(f"[MainUI] GPU enabled: {self.gpu_enabled}")

    def change_appearance_mode(self, mode: str):
        # Qt styling can be expanded to a full theme later.
        self.log_debug(f"[MainUI] Appearance mode set to {mode}")

    def closeEvent(self, event):
        try:
            self.log_debug("[MainUI] Shutting down application...")
            if self.gpu_tab:
                self.gpu_tab.stop()
        finally:
            super().closeEvent(event)


def run_app():
    app = QApplication.instance() or QApplication(sys.argv)
    window = PolyVoxApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())
