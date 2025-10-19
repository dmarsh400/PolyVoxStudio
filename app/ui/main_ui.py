import customtkinter as ctk
import tkinter as tk

from app.ui.book_processing_tab import BookProcessingTab
from app.ui.characters_tab import CharactersTab
from app.ui.voices_tab import VoicesTab
from app.ui.audio_processing_tab import AudioProcessingTab
from app.ui.gpu_monitor_tab import GpuMonitorTab
from app.ui.debug_tab import DebugTab
from app.ui.settings_tab import SettingsTab
from app.ui.clone_voices_tab import CloneVoicesTab


class PolyVoxApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PolyVox Studio")
        self.geometry("1200x800")
        
        # Set up proper window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Tab container
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True)

        # Shared state
        self.book_processing_tab = None
        self.characters_tab = None
        self.voices_tab = None
        self.audio_processing_tab = None
        self.clone_voices_tab = None
        self.gpu_tab = None
        self.debug_tab = None
        self.settings_tab = None

        self.gpu_enabled = True
        self.chapters = []

        # Tab order ? Book ? Characters ? Voices ? Audio ? Clone Voices ? GPU ? Debug ? Settings
        self.build_book_processing_tab()
        self.build_characters_tab()
        self.build_voices_tab()
        self.build_audio_processing_tab()
        self.build_clone_voices_tab()
        self.build_gpu_tab()
        self.build_debug_tab()
        self.build_settings_tab()

    # --- Tabs ---
    def build_book_processing_tab(self):
        self.notebook.add("Book Processing")
        tab = self.notebook.tab("Book Processing")
        self.book_processing_tab = BookProcessingTab(
            tab,
            set_book_text_cb=self.set_book_text,
            go_to_characters_cb=lambda: self.notebook.set("Characters"),
            log_debug=self.log_debug,
        )
        self.book_processing_tab.pack(fill="both", expand=True)

    def build_characters_tab(self):
        self.notebook.add("Characters")
        tab = self.notebook.tab("Characters")
        self.characters_tab = CharactersTab(
            tab,
            get_book_text=lambda: self.chapters,
            log_debug=self.log_debug,
            gpu_enabled=lambda: self.gpu_enabled,
        )
        self.characters_tab.pack(fill="both", expand=True)

    def build_voices_tab(self):
        self.notebook.add("Voices")
        tab = self.notebook.tab("Voices")
        self.voices_tab = VoicesTab(
            tab,
            characters_tab=self.characters_tab,
            audio_tab=self.audio_processing_tab,  # may be None initially
            debug_callback=self.log_debug,
        )
        self.voices_tab.pack(fill="both", expand=True)

    def build_audio_processing_tab(self):
        self.notebook.add("Audio Processing")
        tab = self.notebook.tab("Audio Processing")
        self.audio_processing_tab = AudioProcessingTab(
            tab,
            log_debug=self.log_debug,
        )
        self.audio_processing_tab.pack(fill="both", expand=True)

        # Reconnect Voices ? Audio now that audio tab exists
        if self.voices_tab:
            self.voices_tab.audio_tab = self.audio_processing_tab
            self.log_debug("[MainUI] Linked VoicesTab ? AudioProcessingTab")

    def build_clone_voices_tab(self):
        self.notebook.add("Clone Voices")
        tab = self.notebook.tab("Clone Voices")
        self.clone_voices_tab = CloneVoicesTab(tab)
        self.clone_voices_tab.pack(fill="both", expand=True)

    def build_gpu_tab(self):
        self.notebook.add("GPU Monitor")
        tab = self.notebook.tab("GPU Monitor")
        self.gpu_tab = GpuMonitorTab(
            tab,
            log_debug=self.log_debug,
        )

        # Add GPU toggle button
        toggle_btn = ctk.CTkButton(
            tab,
            text="Toggle GPU Debug",
            command=self.toggle_gpu,
        )
        toggle_btn.pack(pady=10)

        self.gpu_tab.pack(fill="both", expand=True)

    def build_debug_tab(self):
        self.notebook.add("Debug")
        tab = self.notebook.tab("Debug")
        self.debug_tab = DebugTab(tab)
        self.debug_tab.pack(fill="both", expand=True)

    def build_settings_tab(self):
        self.notebook.add("Settings")
        tab = self.notebook.tab("Settings")
        self.settings_tab = SettingsTab(
            tab,
            gpu_tab=self.gpu_tab,
            voices_tab=self.voices_tab,
            log_debug=self.log_debug,
        )
        self.settings_tab.pack(fill="both", expand=True)

    # --- Shared callbacks ---
    def set_book_text(self, chapters):
        self.chapters = chapters
        if self.characters_tab:
            self.characters_tab.set_book_text(chapters)

    def log_debug(self, message: str):
        if self.debug_tab:
            self.debug_tab.log(message)
        print(message)

    def toggle_gpu(self):
        self.gpu_enabled = not self.gpu_enabled
        self.log_debug(f"[MainUI] GPU enabled: {self.gpu_enabled}")

    def change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode.lower())
        self.log_debug(f"[MainUI] Appearance mode set to {mode}")

    def on_closing(self):
        """Clean up and close the application properly."""
        try:
            self.log_debug("[MainUI] Shutting down application...")
            
            # Cancel any pending after() callbacks in tabs
            if self.gpu_tab:
                try:
                    self.gpu_tab.destroy()
                except:
                    pass
            
            # Quit the mainloop first
            self.quit()
            
            # Then destroy the window
            self.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            # Force exit if cleanup fails
            import sys
            sys.exit(0)


def run_app():
    app = PolyVoxApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
