from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
)


class DebugTab(QWidget):
    def __init__(self, log_debug=None, parent=None):
        super().__init__(parent)
        self.log_debug = log_debug or (lambda msg: print(msg))

        layout = QVBoxLayout(self)
        title = QLabel("Debug Console")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)

    def log(self, message: str):
        self.text_area.append(message)
        self.log_debug(f"[DebugTab] {message}")

    def log_message(self, message: str):
        self.log(message)

    def clear_log(self):
        self.text_area.clear()
        self.log_debug("[DebugTab] Cleared log")
