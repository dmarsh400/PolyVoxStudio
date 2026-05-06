import customtkinter as ctk
import tkinter as tk


class DebugTab(ctk.CTkFrame):
    def __init__(self, master, log_debug=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.log_debug = log_debug or (lambda msg: print(msg))

        self._build_layout()

    def _build_layout(self):
        ctk.CTkLabel(self, text="Debug Console", font=("TkDefaultFont", 16, "bold")).pack(pady=10)

        self.text_area = tk.Text(self, height=20, width=100, wrap="word")
        self.text_area.pack(fill="both", expand=True, padx=10, pady=10)

        clear_btn = ctk.CTkButton(self, text="Clear", command=self.clear_log)
        clear_btn.pack(pady=5)
        
        # Apply theme colors
        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """Apply appropriate colors based on current theme."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        
        if is_dark:
            # Dark theme colors
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
        else:
            # Light theme colors
            bg_color = "#ffffff"
            fg_color = "#000000"
        
        # Apply to text area
        if self.text_area:
            self.text_area.config(
                bg=bg_color,
                fg=fg_color,
                insertbackground=fg_color,  # cursor color
                selectbackground="#404040" if is_dark else "#0078d4",
                selectforeground="#ffffff"
            )

    def log(self, message: str):
        """Primary logging method."""
        self.text_area.insert("end", message + "\n")
        self.text_area.see("end")
        self.log_debug(f"[DebugTab] {message}")

    def log_message(self, message: str):
        """Alias so other modules calling log_message still work."""
        self.log(message)

    def clear_log(self):
        self.text_area.delete("1.0", "end")
        self.log_debug("[DebugTab] Cleared log")
