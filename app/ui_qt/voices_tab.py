import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QLineEdit,
)
from app.ui_qt.choice_widgets import PopupChoice
from app.core.emotion_cues import annotate_lines


VOICES_FILE = Path("voices_complete_xtts.json")
SELECTIONS_FILE = Path("app/voices_selections.json")


class VoicesTab(QWidget):
    def __init__(self, debug_callback=None, parent=None):
        super().__init__(parent)
        self.debug_callback = debug_callback or (lambda msg: print(msg))
        self.audio_tab = None
        self.character_lines = []
        self.character_names = []
        self.voice_catalog = []
        self.character_colors = {}

        self._load_voice_catalog()
        self._build_layout()

    def _load_voice_catalog(self):
        if VOICES_FILE.exists():
            data = json.loads(VOICES_FILE.read_text(encoding="utf-8"))
            self.voice_catalog = data.get("voices", []) + data.get("narrators", [])
        else:
            self.voice_catalog = []

    def _build_layout(self):
        layout = QVBoxLayout(self)

        title = QLabel("Voice Assignments")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter characters...")
        self.search_box.textChanged.connect(self._filter_characters)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        # Action buttons
        actions = QHBoxLayout()
        layout.addLayout(actions)

        save_btn = QPushButton("💾 Save Selections")
        save_btn.clicked.connect(self.save_voice_selections)
        actions.addWidget(save_btn)

        load_btn = QPushButton("📂 Load Selections")
        load_btn.clicked.connect(self.load_voice_selections)
        actions.addWidget(load_btn)

        queue_btn = QPushButton("→ Queue to Audio")
        queue_btn.setStyleSheet("background-color: #1976D2; color: white; font-weight: 600; padding: 6px;")
        queue_btn.clicked.connect(self.send_to_audio)
        actions.addWidget(queue_btn)

        # Character/Voice table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Character", "Voice"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        self.status = QLabel("No character lines loaded.")
        self.status.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.status, 0)

    def load_character_lines(self, characters, lines, character_colors=None):
        self.character_names = list(characters or [])
        self.character_lines = list(lines or [])
        self.character_colors = dict(character_colors or {})
        self._render_table()
        self.status.setText(f"Loaded {len(self.character_names)} characters and {len(self.character_lines)} lines")

    @staticmethod
    def _is_bright(color: QColor) -> bool:
        return (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) > 150

    def _render_table(self):
        labels = [entry.get("label", "") for entry in self.voice_catalog if entry.get("label")]
        labels = sorted(set(labels))
        if not labels:
            labels = ["(no voices available)"]

        self.table.setRowCount(len(self.character_names))
        for row, name in enumerate(self.character_names):
            name_item = QTableWidgetItem(name)
            color_value = self.character_colors.get(name)
            if color_value:
                color = QColor(color_value)
                name_item.setBackground(color)
                name_item.setForeground(QColor("#111111") if self._is_bright(color) else QColor("#FFFFFF"))
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
            self.table.setItem(row, 0, name_item)
            
            combo = PopupChoice()
            combo.addItems(labels)
            combo.setToolTip("Click to select a voice.")
            
            self.table.setCellWidget(row, 1, combo)

    def _collect_assignments(self):
        assignments = {}
        for row in range(self.table.rowCount()):
            char_item = self.table.item(row, 0)
            combo = self.table.cellWidget(row, 1)
            if char_item and combo:
                assignments[char_item.text()] = combo.currentText()
        return assignments

    def _filter_characters(self):
        query = self.search_box.text().lower()
        for row in range(self.table.rowCount()):
            char_item = self.table.item(row, 0)
            if char_item:
                match = query in char_item.text().lower()
                self.table.setRowHidden(row, not match)

    def save_voice_selections(self):
        assignments = self._collect_assignments()
        payload = {"assignments": assignments}
        SELECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SELECTIONS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.status.setText(f"Saved selections to {SELECTIONS_FILE}")
        self.debug_callback(f"[VoicesTab] Saved {len(assignments)} selections")

    def load_voice_selections(self):
        if not SELECTIONS_FILE.exists():
            QMessageBox.warning(self, "Not found", f"No selections file found at {SELECTIONS_FILE}")
            return

        data = json.loads(SELECTIONS_FILE.read_text(encoding="utf-8"))
        assignments = data.get("assignments", {})

        for row in range(self.table.rowCount()):
            char_item = self.table.item(row, 0)
            combo = self.table.cellWidget(row, 1)
            if not char_item or not combo:
                continue
            name = char_item.text()
            if name in assignments:
                idx = combo.findText(assignments[name], Qt.MatchFlag.MatchExactly)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

        self.status.setText(f"Loaded selections from {SELECTIONS_FILE}")
        self.debug_callback("[VoicesTab] Loaded voice selections")

    def send_to_audio(self):
        if not self.audio_tab:
            QMessageBox.warning(self, "Audio tab missing", "Audio tab is not linked yet.")
            return

        if not self.character_lines:
            QMessageBox.warning(self, "No lines", "No lines available. Send lines from Characters tab first.")
            return

        assignments = self._collect_assignments()

        voice_by_label = {entry.get("label"): entry for entry in self.voice_catalog}
        emotions = annotate_lines(self.character_lines)
        jobs = []
        for idx, line in enumerate(self.character_lines):
            speaker = line.get("speaker", "Unknown")
            chosen_label = assignments.get(speaker)
            voice_entry = voice_by_label.get(chosen_label)
            if not voice_entry:
                continue
            emotion, intensity = emotions[idx]
            jobs.append(
                {
                    "idx": idx,
                    "chapter": line.get("chapter", "Chapter_Unknown"),
                    "speaker": speaker,
                    "text": line.get("text", ""),
                    "voice_entry": voice_entry,
                    "emotion": emotion,
                    "emotion_intensity": intensity,
                }
            )

        if not jobs:
            QMessageBox.warning(self, "No jobs", "No synthesizable jobs found from current assignments.")
            return

        self.audio_tab.add_jobs(jobs)
        self.status.setText(f"Queued {len(jobs)} jobs for Audio Processing")
        self.debug_callback(f"[VoicesTab] Queued {len(jobs)} jobs")
