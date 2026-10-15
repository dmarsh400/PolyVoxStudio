import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QCheckBox,
    QDoubleSpinBox,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from app.ui_qt.choice_widgets import PopupChoice

SETTINGS_PATH = Path("app/settings.json")


class SettingsTab(QWidget):
    def __init__(self, gpu_tab=None, voices_tab=None, log_debug=None, change_appearance_mode=None, parent=None):
        super().__init__(parent)
        self.gpu_tab = gpu_tab
        self.voices_tab = voices_tab
        self.log_debug = log_debug or (lambda msg: print(msg))
        self.change_appearance_mode = change_appearance_mode

        self.settings = {
            "theme": "Dark",
            "gpu_refresh": 2.0,
            "gpu_debug": False,
            "audio_output_dir": "output/audio",
            "audio_format": "wav",
            "audio_sample_rate": 24000,
            "audio_quality": "high",
            "enable_audio_enhancement": True,
            "max_chapter_lines": 1000,
            "show_tooltips": True,
        }
        self.load_settings()
        self._build_layout()
        self._apply_initial_settings()

    def _apply_initial_settings(self):
        if self.gpu_tab and hasattr(self.gpu_tab, "set_refresh_interval"):
            self.gpu_tab.set_refresh_interval(float(self.settings.get("gpu_refresh", 2.0)))
        if self.gpu_tab and hasattr(self.gpu_tab, "set_debug_enabled"):
            self.gpu_tab.set_debug_enabled(bool(self.settings.get("gpu_debug", False)))

    def _build_layout(self):
        root = QVBoxLayout(self)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        form = QFormLayout()
        root.addLayout(form)

        # --- Appearance ---
        appearance_label = QLabel("Appearance")
        appearance_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #1976D2; margin-top: 10px;")
        form.addRow(appearance_label, None)

        self.theme_combo = PopupChoice()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        self.theme_combo.setCurrentText(self.settings.get("theme", "Dark"))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        form.addRow("Theme:", self.theme_combo)

        show_tooltips = QCheckBox("Show tooltips on hover")
        show_tooltips.setChecked(bool(self.settings.get("show_tooltips", True)))
        form.addRow("UI Options:", show_tooltips)

        # --- GPU Settings ---
        gpu_label = QLabel("GPU Monitor")
        gpu_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #2E7D32; margin-top: 10px;")
        form.addRow(gpu_label, None)

        self.gpu_refresh_spin = QDoubleSpinBox()
        self.gpu_refresh_spin.setRange(0.5, 10.0)
        self.gpu_refresh_spin.setSingleStep(0.1)
        self.gpu_refresh_spin.setValue(float(self.settings.get("gpu_refresh", 2.0)))
        self.gpu_refresh_spin.valueChanged.connect(self.change_gpu_refresh)
        form.addRow("Refresh Interval (s):", self.gpu_refresh_spin)

        self.gpu_debug_check = QCheckBox("Enable debug logging")
        self.gpu_debug_check.setChecked(bool(self.settings.get("gpu_debug", True)))
        self.gpu_debug_check.stateChanged.connect(self.toggle_gpu_debug)
        form.addRow("Debug Mode:", self.gpu_debug_check)

        # --- Audio Settings ---
        audio_label = QLabel("Audio Processing")
        audio_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #C62828; margin-top: 10px;")
        form.addRow(audio_label, None)

        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(8000, 96000)
        self.sample_rate.setValue(int(self.settings.get("audio_sample_rate", 24000)))
        self.sample_rate.valueChanged.connect(self.change_sample_rate)
        form.addRow("Sample Rate (Hz):", self.sample_rate)

        self.output_dir_edit = QLineEdit(self.settings.get("audio_output_dir", "output/audio"))
        browse = QPushButton("Browse...")
        browse.setMaximumWidth(80)
        browse.clicked.connect(self.browse_output_dir)

        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_dir_edit, 1)
        output_layout.addWidget(browse, 0)
        form.addRow("Output Directory:", output_row)

        # --- Processing Settings ---
        proc_label = QLabel("Processing")
        proc_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #F57C00; margin-top: 10px;")
        form.addRow(proc_label, None)

        self.max_lines = QSpinBox()
        self.max_lines.setRange(100, 100000)
        self.max_lines.setValue(int(self.settings.get("max_chapter_lines", 1000)))
        self.max_lines.valueChanged.connect(self.change_max_lines)
        form.addRow("Max Lines per Chapter:", self.max_lines)

        # --- Cache Management ---
        cache_label = QLabel("Cache Management")
        cache_label.setStyleSheet("font-weight: 700; font-size: 11px; color: #6A1B9A; margin-top: 10px;")
        form.addRow(cache_label, None)

        clear_cache_btn = QPushButton("🧹 Clear Cached Chapters")
        clear_cache_btn.setStyleSheet("background-color: #6A1B9A; color: white; font-weight: 600; padding: 6px;")
        clear_cache_btn.clicked.connect(self.clear_cached_chapters)
        form.addRow("BookNLP Cache:", clear_cache_btn)

        # --- Buttons ---
        save_btn = QPushButton("💾 Save All Settings")
        save_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: 600; padding: 6px;")
        root.addWidget(save_btn)
        save_btn.clicked.connect(self.save_all_settings)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("font-size: 9px; color: #666; margin-top: 10px;")
        root.addWidget(self.status)

        root.addStretch()

    def change_theme(self, choice):
        self.settings["theme"] = choice
        if self.change_appearance_mode:
            self.change_appearance_mode(choice)
        self.log_debug(f"[SettingsTab] Theme changed to {choice}")

    def change_gpu_refresh(self, value):
        self.settings["gpu_refresh"] = float(value)
        if self.gpu_tab and hasattr(self.gpu_tab, "set_refresh_interval"):
            self.gpu_tab.set_refresh_interval(float(value))

    def toggle_gpu_debug(self, _state):
        enabled = self.gpu_debug_check.isChecked()
        self.settings["gpu_debug"] = enabled
        if self.gpu_tab and hasattr(self.gpu_tab, "set_debug_enabled"):
            self.gpu_tab.set_debug_enabled(enabled)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select output directory")
        if directory:
            self.output_dir_edit.setText(directory)
            self.settings["audio_output_dir"] = directory

    def change_sample_rate(self, value):
        self.settings["audio_sample_rate"] = int(value)

    def change_max_lines(self, value):
        self.settings["max_chapter_lines"] = int(value)

    def clear_cached_chapters(self):
        reply = QMessageBox.question(
            self,
            "Clear Cached Chapters",
            "This will delete all cached BookNLP chapter artifacts and force reprocessing next time. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from app.core.character_detection import clear_booknlp_cache

            removed = clear_booknlp_cache()
            self.status.setText(f"Cleared cached chapters ({removed} item(s) removed).")
            self.log_debug(f"[SettingsTab] Cleared cached chapters: removed {removed} item(s)")
            QMessageBox.information(
                self,
                "Cache Cleared",
                f"Cleared cached chapters successfully. Removed {removed} cached item(s).",
            )
        except Exception as exc:
            self.log_debug(f"[SettingsTab] Failed to clear cached chapters: {exc}")
            QMessageBox.critical(self, "Error", f"Failed to clear cached chapters:\n{exc}")

    def save_all_settings(self):
        self.settings["audio_output_dir"] = self.output_dir_edit.text().strip() or "output/audio"
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(self.settings, indent=2, ensure_ascii=False), encoding="utf-8")
        self.status.setText(f"Saved settings to {SETTINGS_PATH}")
        QMessageBox.information(self, "Saved", "Settings saved.")

    def load_settings(self):
        if SETTINGS_PATH.exists():
            try:
                loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                self.settings.update(loaded)
            except Exception as exc:
                self.log_debug(f"[SettingsTab] Failed to load settings: {exc}")
