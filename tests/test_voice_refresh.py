import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QTabWidget

from app.ui_qt import clone_voices_tab, main_ui, voices_tab


class VoiceRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.catalog = root / "voices.json"
        self.references = root / "references"
        self.catalog.write_text(json.dumps({
            "voices": [{"label": "Original", "voice_file": "original.wav"}],
            "narrators": [],
        }), encoding="utf-8")
        for module, name, value in (
            (voices_tab, "VOICES_FILE", self.catalog),
            (clone_voices_tab, "VOICES_FILE", self.catalog),
            (clone_voices_tab, "VOICES_DIR", self.references),
        ):
            patcher = patch.object(module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.tab = voices_tab.VoicesTab()
        self.tab.character_names = ["Alice", "Bob"]
        self.tab.character_lines = [{"speaker": "Alice", "text": "Hello"}]
        self.tab._render_table()

    def test_clone_updates_catalog_and_preserves_choices_and_jobs(self):
        window = types.SimpleNamespace(voices_tab=self.tab, notebook=QTabWidget())
        main_ui.PolyVoxApp.build_clone_voices_tab(window)
        clone = window.clone_voices_tab
        source = self.catalog.parent / "source.wav"
        source.write_bytes(b"reference")
        clone.audio_path = str(source)
        clone.name_edit.setText("New Voice")
        fake_voices = types.ModuleType("app.core.voices")
        fake_voices.transcribe_reference_audio = lambda path: "reference text"
        with patch.dict("sys.modules", {"app.core.voices": fake_voices}), \
                patch.object(QMessageBox, "information"):
            clone.generate_voice()

        alice = self.tab._combo_for_row(0)
        bob = self.tab._combo_for_row(1)
        self.assertEqual(alice.currentText(), "Original")
        self.assertEqual(bob.currentText(), "Original")
        self.assertGreaterEqual(alice.findText("New Voice"), 0)
        alice.setCurrentText("New Voice")
        jobs = []
        self.tab.audio_tab = types.SimpleNamespace(add_jobs=jobs.extend)
        self.tab.send_to_audio()
        self.assertEqual(jobs[0]["voice_entry"]["ref_text"], "reference text")
        self.assertEqual(jobs[0]["voice_entry"]["label"], "New Voice")

    def test_manual_refresh_preserves_selections_and_reports_read_errors(self):
        self.catalog.write_text(json.dumps({
            "voices": [{"label": "Original"}, {"label": "External"}],
            "narrators": [],
        }), encoding="utf-8")
        button = next(button for button in self.tab.findChildren(QPushButton)
                      if button.text() == "Refresh Voices")
        button.click()
        self.assertEqual(self.tab._combo_for_row(0).currentText(), "Original")
        self.assertGreaterEqual(self.tab._combo_for_row(0).findText("External"), 0)

        self.catalog.write_text("{", encoding="utf-8")
        with patch.object(QMessageBox, "warning") as warning:
            self.tab.refresh_voices()
        warning.assert_called_once()
        self.assertGreaterEqual(self.tab._combo_for_row(0).findText("External"), 0)

    def test_clone_with_deferred_transcription_still_refreshes(self):
        clone = clone_voices_tab.CloneVoicesTab()
        clone.voice_saved.connect(self.tab.refresh_voices)
        source = self.catalog.parent / "source.wav"
        source.write_bytes(b"reference")
        clone.audio_path = str(source)
        clone.name_edit.setText("Deferred")
        fake_voices = types.ModuleType("app.core.voices")

        def fail_transcription(path):
            raise RuntimeError("transcription unavailable")

        fake_voices.transcribe_reference_audio = fail_transcription
        with patch.dict("sys.modules", {"app.core.voices": fake_voices}), \
                patch.object(QMessageBox, "information"):
            clone.generate_voice()
        self.assertGreaterEqual(self.tab._combo_for_row(0).findText("Deferred"), 0)
        saved = json.loads(self.catalog.read_text(encoding="utf-8"))["voices"][-1]
        self.assertEqual(saved["ref_text"], "")
        self.assertIn("transcription unavailable", clone.log_box.toPlainText())

    def test_missing_selection_is_preserved_and_reported(self):
        self.catalog.write_text(json.dumps({
            "voices": [{"label": "Replacement"}], "narrators": [],
        }), encoding="utf-8")
        with patch.object(QMessageBox, "warning") as warning:
            self.tab.refresh_voices()
        warning.assert_called_once()
        self.assertEqual(self.tab._combo_for_row(0).currentText(), "Original")


if __name__ == "__main__":
    unittest.main()
