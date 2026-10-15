import subprocess

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QSpinBox,
)


class GpuMonitorTab(QWidget):
    def __init__(self, log_debug=None, parent=None):
        super().__init__(parent)
        self.log_debug = log_debug or (lambda msg: print(msg))
        self.refresh_interval = 2.0
        self.debug_enabled = False

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("GPU Monitor")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        # Controls
        controls = QHBoxLayout()
        layout.addLayout(controls)

        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self._update_once)
        controls.addWidget(refresh_btn)

        controls.addWidget(QLabel("Interval (s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setValue(int(self.refresh_interval))
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setMaximumWidth(70)
        self.interval_spin.valueChanged.connect(lambda v: self.set_refresh_interval(float(v)))
        controls.addWidget(self.interval_spin)

        controls.addStretch()

        # GPU output display
        self.gpu_text = QTextEdit()
        self.gpu_text.setReadOnly(True)
        self.gpu_text.setPlainText("Waiting for GPU stats...")
        self.gpu_text.setFont(self.gpu_text.font())  # Keep monospace
        layout.addWidget(self.gpu_text, 1)

        # Auto-update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_once)
        self.timer.start(int(self.refresh_interval * 1000))

    def _update_once(self):
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                output = f"Error running nvidia-smi:\n{result.stderr.strip()}"
            else:
                output = result.stdout
            self.gpu_text.setPlainText(output)
            if self.debug_enabled:
                self.log_debug("[GpuMonitorTab] Updated GPU stats")
        except Exception as exc:
            if self.debug_enabled:
                self.log_debug(f"[GpuMonitorTab] Error updating GPU stats: {exc}")

    def set_refresh_interval(self, interval):
        self.refresh_interval = float(interval)
        self.timer.start(int(self.refresh_interval * 1000))
        self.log_debug(f"[GpuMonitorTab] Refresh interval set to {self.refresh_interval:.1f}s")

    def set_debug_enabled(self, enabled: bool):
        self.debug_enabled = enabled
        state = "enabled" if enabled else "disabled"
        self.log_debug(f"[GpuMonitorTab] Debug logging {state}")

    def stop(self):
        self.timer.stop()
