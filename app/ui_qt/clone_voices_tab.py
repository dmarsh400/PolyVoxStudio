import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTextEdit,
)
from app.ui_qt.choice_widgets import PopupChoice

VOICES_FILE = Path("voices_complete_xtts.json")
VOICES_DIR = Path("voices/references")


class CloneVoicesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_path = ""
        self._build_layout()

    def _build_layout(self):
        layout = QVBoxLayout(self)

        title = QLabel("Clone Voices")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        pick_row = QHBoxLayout()
        layout.addLayout(pick_row)

        self.pick_btn = QPushButton("Select Audio File")
        self.pick_btn.clicked.connect(self.upload_audio)
        pick_row.addWidget(self.pick_btn)

        self.audio_label = QLabel("No file selected")
        pick_row.addWidget(self.audio_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Voice Name")
        layout.addWidget(self.name_edit)

        self.type_combo = PopupChoice()
        self.type_combo.addItems(["voice", "narrator"])
        layout.addWidget(self.type_combo)

        self.gender_combo = PopupChoice()
        self.gender_combo.addItems(["Male", "Female", "Unknown"])
        layout.addWidget(self.gender_combo)

        self.age_combo = PopupChoice()
        self.age_combo.addItems(["Teen", "Young Adult", "Adult", "Middle-Aged", "Mature", "Senior", "Unknown"])
        layout.addWidget(self.age_combo)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Description")
        layout.addWidget(self.desc_edit)

        save_btn = QPushButton("Generate & Save Voice")
        save_btn.clicked.connect(self.generate_voice)
        layout.addWidget(save_btn)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def log(self, message):
        self.log_box.append(message)

    def upload_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select audio", "", "Audio Files (*.wav *.mp3 *.flac)")
        if path:
            self.audio_path = path
            self.audio_label.setText(path)
            self.log(f"Selected audio: {path}")

    def generate_voice(self):
        if not self.audio_path:
            QMessageBox.critical(self, "Error", "Please select an audio file first.")
            return

        voice_name = self.name_edit.text().strip()
        if not voice_name:
            QMessageBox.critical(self, "Error", "Please provide a voice name.")
            return

        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in voice_name).lower()
        if not safe_name:
            QMessageBox.critical(self, "Error", "Voice name produced an invalid filename.")
            return

        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        target = VOICES_DIR / f"{safe_name}.wav"

        # Keep this as a straight file copy; source preprocessing can be run later.
        Path(target).write_bytes(Path(self.audio_path).read_bytes())

        # F5-TTS needs a transcript of the reference clip alongside the audio;
        # transcribe once here so per-line synthesis never re-transcribes it.
        ref_text = ""
        try:
            from app.core.voices import transcribe_reference_audio
            self.log("Transcribing reference audio for F5-TTS (one-time)...")
            ref_text = transcribe_reference_audio(str(target))
            self.log(f"Reference transcript: {ref_text}")
        except Exception as exc:
            self.log(f"⚠ Could not transcribe reference audio now, will transcribe on first use: {exc}")

        if VOICES_FILE.exists():
            data = json.loads(VOICES_FILE.read_text(encoding="utf-8"))
        else:
            data = {"voices": [], "narrators": []}

        entry = {
            "id": safe_name,
            "label": voice_name,
            "description": self.desc_edit.text().strip(),
            "voice_file": str(target).replace("\\\\", "/"),
            "engine": "f5",
            "ref_text": ref_text,
            "gender": self.gender_combo.currentText(),
            "age": self.age_combo.currentText(),
        }

        bucket = "narrators" if self.type_combo.currentText() == "narrator" else "voices"
        data.setdefault(bucket, [])

        # Upsert by label.
        replaced = False
        for idx, old in enumerate(data[bucket]):
            if old.get("label") == voice_name:
                data[bucket][idx] = entry
                replaced = True
                break
        if not replaced:
            data[bucket].append(entry)

        VOICES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"Saved voice '{voice_name}' to {target}")
        QMessageBox.information(self, "Saved", f"Voice '{voice_name}' saved successfully.")
