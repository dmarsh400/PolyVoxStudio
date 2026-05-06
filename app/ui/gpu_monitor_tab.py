import customtkinter as ctk
import tkinter as tk
import threading
import time
import subprocess
import re


class GpuMonitorTab(ctk.CTkFrame):
    def __init__(self, master, log_debug=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.log_debug = log_debug or (lambda msg: print(msg))
        self.refresh_interval = 2.0  # seconds
        self._stop_event = threading.Event()
        self.debug_enabled = True  # New flag to control debug logging

        self._build_layout()

        # Start background update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _build_layout(self):
        title = ctk.CTkLabel(
            self,
            text="GPU Monitor",
            font=("TkDefaultFont", 18, "bold"),
            text_color="lime",
            fg_color="black"
        )
        title.pack(fill="x", pady=5)

        self.gpu_text = tk.Text(
            self,
            height=30,
            width=120,
            wrap="none",
            bg="black",
            fg="lime",
            insertbackground="lime",
            font=("Courier New", 12)
        )
        self.gpu_text.pack(fill="both", expand=True, padx=10, pady=10)

        yscroll = tk.Scrollbar(self, orient="vertical", command=self.gpu_text.yview)
        xscroll = tk.Scrollbar(self, orient="horizontal", command=self.gpu_text.xview)
        self.gpu_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")

        self.gpu_text.insert("1.0", "Waiting for GPU stats...")
        self.gpu_text.config(state="disabled")

    def _color_for_value(self, value, low, high):
        ratio = (value - low) / (high - low)
        ratio = max(0.0, min(1.0, ratio))
        if ratio < 0.5:
            r = int(0 + (255 * (ratio * 2)))
            g = 255
        else:
            r = 255
            g = int(255 - (255 * ((ratio - 0.5) * 2)))
        b = 0
        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_loop(self):
        while not self._stop_event.is_set():
            try:
                result = subprocess.run(
                    ["nvidia-smi"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if result.returncode != 0:
                    output = f"Error running nvidia-smi:\n{result.stderr.strip()}"
                else:
                    output = result.stdout

                self.gpu_text.config(state="normal")
                self.gpu_text.delete("1.0", "end")
                self.gpu_text.insert("1.0", output)

                for match in re.finditer(r"(\d+)%", output):
                    val = int(match.group(1))
                    color = self._color_for_value(val, 0, 100)
                    start = f"1.0+{match.start()}c"
                    end = f"1.0+{match.end()}c"
                    tag = f"util{match.start()}"
                    self.gpu_text.tag_add(tag, start, end)
                    self.gpu_text.tag_config(tag, foreground=color)

                for match in re.finditer(r"(\d+)[ ]*C", output):
                    val = int(match.group(1))
                    color = self._color_for_value(val, 30, 90)
                    start = f"1.0+{match.start()}c"
                    end = f"1.0+{match.end()-1}c"
                    tag = f"temp{match.start()}"
                    self.gpu_text.tag_add(tag, start, end)
                    self.gpu_text.tag_config(tag, foreground=color)

                self.gpu_text.config(state="disabled")

                if self.debug_enabled:
                    self.log_debug("[GpuMonitorTab] Updated GPU stats")

            except Exception as e:
                if self.debug_enabled:
                    self.log_debug(f"[GpuMonitorTab] Error updating GPU stats: {e}")

            time.sleep(self.refresh_interval)

    def set_refresh_interval(self, interval):
        try:
            self.refresh_interval = float(interval)
            self.log_debug(f"[GpuMonitorTab] Refresh interval set to {self.refresh_interval:.1f}s")
        except Exception as e:
            self.log_debug(f"[GpuMonitorTab] Failed to set refresh interval: {e}")

    def set_debug_enabled(self, enabled: bool):
        self.debug_enabled = enabled
        state = "enabled" if enabled else "disabled"
        self.log_debug(f"[GpuMonitorTab] Debug logging {state}")

    def stop(self):
        self._stop_event.set()
