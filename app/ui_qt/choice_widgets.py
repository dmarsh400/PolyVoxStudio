from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class PopupChoice(QPushButton):
    currentTextChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._current = ""
        self._popup = None
        self._closing = False
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.open_popup)

    def addItems(self, items):
        self._items = [str(item) for item in items]
        if self._items and not self._current:
            self.setCurrentText(self._items[0])

    def count(self):
        return len(self._items)

    def currentText(self):
        return self._current

    def setCurrentText(self, text):
        text = str(text)
        changed = text != self._current
        self._current = text
        self.setText(f"{text}  ▼")
        if changed:
            self.currentTextChanged.emit(text)

    def findText(self, text, flags=Qt.MatchExactly):
        try:
            return self._items.index(text)
        except ValueError:
            return -1

    def setCurrentIndex(self, index):
        if 0 <= index < len(self._items):
            self.setCurrentText(self._items[index])

    def setMaximumWidth(self, width):
        super().setMaximumWidth(width)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down):
            self.open_popup()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        event.ignore()

    def open_popup(self):
        if self._popup is not None or not self._items:
            return

        popup = QListWidget()
        popup.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        popup.setStyleSheet(
            "QListWidget { background: #2d2d2d; color: #e0e0e0; border: 1px solid #707070; }"
            "QListWidget::item { padding: 5px 8px; }"
            "QListWidget::item:hover { background: #404040; }"
            "QListWidget::item:selected { background: #1976D2; color: #ffffff; }"
        )
        for label in self._items:
            QListWidgetItem(label, popup)

        if self._current in self._items:
            popup.setCurrentRow(self._items.index(self._current))

        metrics = popup.fontMetrics()
        row_height = metrics.height() + 10
        longest = max(metrics.horizontalAdvance(item) for item in self._items)
        width = max(self.width(), longest + 36)
        height = min(row_height * min(len(self._items), 12), 320) + 6
        popup.resize(width, height)

        anchor = self.mapToGlobal(QPoint(0, 0))
        screen = QApplication.screenAt(anchor) or QApplication.primaryScreen()
        if screen is not None:
            bounds = screen.availableGeometry()
            x = min(max(anchor.x(), bounds.left()), max(bounds.left(), bounds.right() - width))
            y = anchor.y() + self.height()
            if y + height > bounds.bottom():
                y = anchor.y() - height
            popup.move(x, y)
        else:
            popup.move(self.mapToGlobal(QPoint(0, self.height())))

        popup.itemClicked.connect(self._select_item)
        popup.installEventFilter(self)
        popup.destroyed.connect(self._popup_destroyed)
        self._popup = popup
        popup.show()
        popup.raise_()
        popup.activateWindow()
        if popup.currentRow() >= 0:
            popup.scrollToItem(popup.currentItem())

    def _select_item(self, item):
        self.setCurrentText(item.text())
        self._close_popup()

    def _popup_destroyed(self, *_args):
        self._popup = None
        self._closing = False

    def _close_popup(self):
        if self._popup is None or self._closing:
            return
        self._closing = True
        popup = self._popup
        self._popup = None
        popup.removeEventFilter(self)
        popup.hide()
        QTimer.singleShot(0, popup.deleteLater)

    def eventFilter(self, obj, event):
        if obj is self._popup and event.type() == QEvent.WindowDeactivate:
            self._close_popup()
        return super().eventFilter(obj, event)


class ChoiceDialog(QDialog):
    def __init__(self, parent, title, label, options, current_index=0):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(420, 300)

        layout = QVBoxLayout(self)
        prompt = QLabel(label, self)
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        self.list_widget = QListWidget(self)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for option in options:
            QListWidgetItem(str(option), self.list_widget)
        if options:
            self.list_widget.setCurrentRow(max(0, min(current_index, len(options) - 1)))
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @classmethod
    def get_item(cls, parent, title, label, options, current_index=0):
        if not options:
            return "", False
        dialog = cls(parent, title, label, options, current_index)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        item = dialog.list_widget.currentItem() if accepted else None
        return (item.text() if item else ""), bool(accepted and item)
