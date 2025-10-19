import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, gpu_tab=None, voices_tab=None, log_debug=None):
        super().__init__(master)

        self.gpu_tab = gpu_tab
        self.voices_tab = voices_tab
        self.log_debug = log_debug or (lambda msg: print(msg))
        
        # Default settings
        self.settings = {
            "theme": "System",
            "gpu_refresh": 2.0,
            "gpu_debug": True,
            "audio_output_dir": "output_audio",
            "audio_format": "wav",
            "audio_sample_rate": 24000,
            "audio_quality": "high",
            "enable_audio_enhancement": True,
            "character_detection_model": "english",
            "auto_save_interval": 5,
            "max_chapter_lines": 1000,
            "show_tooltips": True,
            "auto_backup": True,
            "narrator_color": "#808080"
        }
        
        self.load_settings()
        self._build_layout()

    def _build_layout(self):
        # Title
        ctk.CTkLabel(self, text="Settings", font=("Arial", 20, "bold")).pack(pady=10)
        
        # Create scrollable frame for all settings
        scroll_frame = ctk.CTkScrollableFrame(self, width=700, height=600)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === APPEARANCE SECTION ===
        self._create_section_header(scroll_frame, "[APPEARANCE]")
        
        # Theme
        theme_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(theme_frame, text="Theme:", width=150, anchor="w").pack(side="left", padx=5)
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "System"))
        theme_dropdown = ctk.CTkComboBox(
            theme_frame,
            values=["Light", "Dark", "System"],
            variable=self.theme_var,
            command=lambda choice: self.change_theme(choice),
            width=200
        )
        theme_dropdown.pack(side="left", padx=5)
        
        # Narrator Color
        narrator_color_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        narrator_color_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(narrator_color_frame, text="Narrator Color:", width=150, anchor="w").pack(side="left", padx=5)
        self.narrator_color_var = tk.StringVar(value=self.settings.get("narrator_color", "#808080"))
        narrator_color_entry = ctk.CTkEntry(narrator_color_frame, textvariable=self.narrator_color_var, width=100)
        narrator_color_entry.pack(side="left", padx=5)
        ctk.CTkButton(narrator_color_frame, text="Apply", command=self.change_narrator_color, width=80).pack(side="left", padx=5)
        
        # Show Tooltips
        tooltip_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        tooltip_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(tooltip_frame, text="Show Tooltips:", width=150, anchor="w").pack(side="left", padx=5)
        self.tooltip_var = tk.BooleanVar(value=self.settings.get("show_tooltips", True))
        ctk.CTkSwitch(tooltip_frame, text="", variable=self.tooltip_var, command=self.toggle_tooltips).pack(side="left", padx=5)
        
        # === GPU SETTINGS ===
        if self.gpu_tab:
            self._create_section_header(scroll_frame, "[GPU SETTINGS]")
            
            # GPU Refresh Rate
            gpu_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            gpu_frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(gpu_frame, text="GPU Refresh Rate:", width=150, anchor="w").pack(side="left", padx=5)
            self.gpu_refresh_var = tk.DoubleVar(value=self.settings.get("gpu_refresh", 2.0))
            gpu_slider = ctk.CTkSlider(
                gpu_frame,
                from_=0.5,
                to=10.0,
                number_of_steps=95,
                variable=self.gpu_refresh_var,
                command=lambda v: self.change_gpu_refresh(v),
                width=200
            )
            gpu_slider.pack(side="left", padx=5)
            self.gpu_refresh_label = ctk.CTkLabel(gpu_frame, text=f"{self.gpu_refresh_var.get():.1f}s", width=50)
            self.gpu_refresh_label.pack(side="left", padx=5)
            
            # GPU Debug Mode
            debug_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            debug_frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(debug_frame, text="GPU Debug Mode:", width=150, anchor="w").pack(side="left", padx=5)
            self.gpu_debug_var = tk.BooleanVar(value=self.settings.get("gpu_debug", True))
            ctk.CTkSwitch(debug_frame, text="", variable=self.gpu_debug_var, command=self.toggle_gpu_debug).pack(side="left", padx=5)
        
        # === AUDIO SETTINGS ===
        self._create_section_header(scroll_frame, "[AUDIO OUTPUT]")
        
        # Output Directory
        output_dir_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        output_dir_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(output_dir_frame, text="Output Directory:", width=150, anchor="w").pack(side="left", padx=5)
        self.output_dir_var = tk.StringVar(value=self.settings.get("audio_output_dir", "output_audio"))
        ctk.CTkEntry(output_dir_frame, textvariable=self.output_dir_var, width=250).pack(side="left", padx=5)
        ctk.CTkButton(output_dir_frame, text="Browse", command=self.browse_output_dir, width=80).pack(side="left", padx=5)
        
        # Audio Format
        format_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        format_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(format_frame, text="Audio Format:", width=150, anchor="w").pack(side="left", padx=5)
        self.audio_format_var = tk.StringVar(value=self.settings.get("audio_format", "wav"))
        ctk.CTkComboBox(
            format_frame,
            values=["wav", "mp3", "flac", "ogg"],
            variable=self.audio_format_var,
            command=lambda v: self.change_audio_format(v),
            width=200
        ).pack(side="left", padx=5)
        
        # Sample Rate
        sample_rate_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        sample_rate_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(sample_rate_frame, text="Sample Rate:", width=150, anchor="w").pack(side="left", padx=5)
        self.sample_rate_var = tk.StringVar(value=str(self.settings.get("audio_sample_rate", 24000)))
        ctk.CTkComboBox(
            sample_rate_frame,
            values=["16000", "22050", "24000", "44100", "48000"],
            variable=self.sample_rate_var,
            command=lambda v: self.change_sample_rate(v),
            width=200
        ).pack(side="left", padx=5)
        ctk.CTkLabel(sample_rate_frame, text="Hz").pack(side="left", padx=5)
        
        # Audio Quality
        quality_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        quality_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(quality_frame, text="Audio Quality:", width=150, anchor="w").pack(side="left", padx=5)
        self.audio_quality_var = tk.StringVar(value=self.settings.get("audio_quality", "high"))
        ctk.CTkComboBox(
            quality_frame,
            values=["low", "medium", "high", "ultra"],
            variable=self.audio_quality_var,
            command=lambda v: self.change_audio_quality(v),
            width=200
        ).pack(side="left", padx=5)
        
        # Audio Enhancement
        enhancement_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        enhancement_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(enhancement_frame, text="Audio Enhancement:", width=150, anchor="w").pack(side="left", padx=5)
        self.enhancement_var = tk.BooleanVar(value=self.settings.get("enable_audio_enhancement", True))
        ctk.CTkSwitch(enhancement_frame, text="", variable=self.enhancement_var, command=self.toggle_enhancement).pack(side="left", padx=5)
        ctk.CTkLabel(enhancement_frame, text="(requires FFmpeg)", font=("Arial", 11), text_color="gray").pack(side="left", padx=5)
        
        # === CHARACTER DETECTION ===
        self._create_section_header(scroll_frame, "[CHARACTER DETECTION]")
        
        # Detection Model
        model_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        model_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(model_frame, text="Model:", width=150, anchor="w").pack(side="left", padx=5)
        self.model_var = tk.StringVar(value=self.settings.get("character_detection_model", "english"))
        ctk.CTkComboBox(
            model_frame,
            values=["english", "multilingual"],
            variable=self.model_var,
            command=lambda v: self.change_detection_model(v),
            width=200
        ).pack(side="left", padx=5)
        
        # Max Chapter Lines
        max_lines_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        max_lines_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(max_lines_frame, text="Max Lines per Chapter:", width=150, anchor="w").pack(side="left", padx=5)
        self.max_lines_var = tk.IntVar(value=self.settings.get("max_chapter_lines", 1000))
        ctk.CTkEntry(max_lines_frame, textvariable=self.max_lines_var, width=100).pack(side="left", padx=5)
        ctk.CTkButton(max_lines_frame, text="Apply", command=self.change_max_lines, width=80).pack(side="left", padx=5)
        
        # === GENERAL SETTINGS ===
        self._create_section_header(scroll_frame, "[GENERAL]")
        
        # Auto-save Interval
        autosave_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        autosave_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(autosave_frame, text="Auto-save Interval:", width=150, anchor="w").pack(side="left", padx=5)
        self.autosave_var = tk.IntVar(value=self.settings.get("auto_save_interval", 5))
        ctk.CTkEntry(autosave_frame, textvariable=self.autosave_var, width=100).pack(side="left", padx=5)
        ctk.CTkLabel(autosave_frame, text="minutes").pack(side="left", padx=5)
        ctk.CTkButton(autosave_frame, text="Apply", command=self.change_autosave, width=80).pack(side="left", padx=5)
        
        # Auto Backup
        backup_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        backup_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(backup_frame, text="Auto Backup:", width=150, anchor="w").pack(side="left", padx=5)
        self.backup_var = tk.BooleanVar(value=self.settings.get("auto_backup", True))
        ctk.CTkSwitch(backup_frame, text="", variable=self.backup_var, command=self.toggle_backup).pack(side="left", padx=5)
        
        # === ACTION BUTTONS ===
        button_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=20)
        
        ctk.CTkButton(button_frame, text="Save All Settings", command=self.save_all_settings, 
                     fg_color="green", hover_color="darkgreen", width=150).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Reset to Defaults", command=self.reset_to_defaults,
                     fg_color="orange", hover_color="darkorange", width=150).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Export Settings", command=self.export_settings, width=150).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Import Settings", command=self.import_settings, width=150).pack(side="left", padx=5)
    
    def _create_section_header(self, parent, text):
        """Create a section header with styling."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=(15, 5))
        # Add a colored line for visual separation
        separator = ctk.CTkFrame(frame, height=2, fg_color=("gray70", "gray30"))
        separator.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(frame, text=text, font=("Arial", 14, "bold"), anchor="w", 
                    text_color=("#2B5BA6", "#4A9EFF")).pack(side="left", padx=5)

    # === APPEARANCE METHODS ===
    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.settings["theme"] = choice
        self.log_debug(f"[SettingsTab] Theme changed to {choice}")
    
    def change_narrator_color(self):
        color = self.narrator_color_var.get()
        self.settings["narrator_color"] = color
        self.log_debug(f"[SettingsTab] Narrator color changed to {color}")
        messagebox.showinfo("Success", f"Narrator color updated to {color}\nReload characters to see changes.")
    
    def toggle_tooltips(self):
        enabled = self.tooltip_var.get()
        self.settings["show_tooltips"] = enabled
        self.log_debug(f"[SettingsTab] Tooltips {'enabled' if enabled else 'disabled'}")
    
    # === GPU METHODS ===
    def change_gpu_refresh(self, value):
        self.settings["gpu_refresh"] = float(value)
        if self.gpu_tab and hasattr(self.gpu_tab, "set_refresh_interval"):
            self.gpu_tab.set_refresh_interval(float(value))
        self.gpu_refresh_label.configure(text=f"{float(value):.1f}s")
        self.log_debug(f"[SettingsTab] GPU refresh set to {value:.1f}s")

    def toggle_gpu_debug(self):
        enabled = self.gpu_debug_var.get()
        self.settings["gpu_debug"] = enabled
        if self.gpu_tab:
            self.gpu_tab.set_debug_enabled(enabled)
        self.log_debug(f"[SettingsTab] GPU debug set to {enabled}")
    
    # === AUDIO METHODS ===
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
            self.settings["audio_output_dir"] = directory
            self.log_debug(f"[SettingsTab] Output directory set to {directory}")
    
    def change_audio_format(self, value):
        self.settings["audio_format"] = value
        self.log_debug(f"[SettingsTab] Audio format changed to {value}")
    
    def change_sample_rate(self, value):
        self.settings["audio_sample_rate"] = int(value)
        self.log_debug(f"[SettingsTab] Sample rate changed to {value}Hz")
    
    def change_audio_quality(self, value):
        self.settings["audio_quality"] = value
        self.log_debug(f"[SettingsTab] Audio quality changed to {value}")
    
    def toggle_enhancement(self):
        enabled = self.enhancement_var.get()
        self.settings["enable_audio_enhancement"] = enabled
        self.log_debug(f"[SettingsTab] Audio enhancement {'enabled' if enabled else 'disabled'}")
    
    # === CHARACTER DETECTION METHODS ===
    def change_detection_model(self, value):
        self.settings["character_detection_model"] = value
        self.log_debug(f"[SettingsTab] Detection model changed to {value}")
    
    def change_max_lines(self):
        try:
            max_lines = self.max_lines_var.get()
            if max_lines < 100:
                messagebox.showwarning("Warning", "Minimum value is 100 lines")
                self.max_lines_var.set(100)
                return
            self.settings["max_chapter_lines"] = max_lines
            self.log_debug(f"[SettingsTab] Max chapter lines set to {max_lines}")
            messagebox.showinfo("Success", f"Max chapter lines set to {max_lines}")
        except:
            messagebox.showerror("Error", "Invalid number")
    
    # === GENERAL METHODS ===
    def change_autosave(self):
        try:
            interval = self.autosave_var.get()
            if interval < 1:
                messagebox.showwarning("Warning", "Minimum interval is 1 minute")
                self.autosave_var.set(1)
                return
            self.settings["auto_save_interval"] = interval
            self.log_debug(f"[SettingsTab] Auto-save interval set to {interval} minutes")
            messagebox.showinfo("Success", f"Auto-save interval set to {interval} minutes")
        except:
            messagebox.showerror("Error", "Invalid number")
    
    def toggle_backup(self):
        enabled = self.backup_var.get()
        self.settings["auto_backup"] = enabled
        self.log_debug(f"[SettingsTab] Auto backup {'enabled' if enabled else 'disabled'}")
    
    # === SETTINGS MANAGEMENT ===
    def save_all_settings(self):
        """Save all current settings to file."""
        self.save_settings()
        messagebox.showinfo("Success", "All settings saved successfully!")
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        response = messagebox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\nThis cannot be undone."
        )
        if response:
            # Reset to defaults
            self.settings = {
                "theme": "System",
                "gpu_refresh": 2.0,
                "gpu_debug": True,
                "audio_output_dir": "output_audio",
                "audio_format": "wav",
                "audio_sample_rate": 24000,
                "audio_quality": "high",
                "enable_audio_enhancement": True,
                "character_detection_model": "english",
                "auto_save_interval": 5,
                "max_chapter_lines": 1000,
                "show_tooltips": True,
                "auto_backup": True,
                "narrator_color": "#808080"
            }
            self.save_settings()
            self.log_debug("[SettingsTab] Settings reset to defaults")
            messagebox.showinfo("Success", "Settings reset to defaults!\nPlease restart the application for all changes to take effect.")
    
    def export_settings(self):
        """Export settings to JSON file."""
        filename = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.settings, f, indent=4)
                self.log_debug(f"[SettingsTab] Settings exported to {filename}")
                messagebox.showinfo("Success", f"Settings exported to:\n{filename}")
            except Exception as e:
                self.log_debug(f"[SettingsTab] Error exporting settings: {e}")
                messagebox.showerror("Error", f"Failed to export settings:\n{e}")
    
    def import_settings(self):
        """Import settings from JSON file."""
        filename = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported = json.load(f)
                
                # Validate and merge settings
                for key, value in imported.items():
                    if key in self.settings:
                        self.settings[key] = value
                
                self.save_settings()
                self.log_debug(f"[SettingsTab] Settings imported from {filename}")
                messagebox.showinfo("Success", f"Settings imported from:\n{filename}\nPlease restart the application for all changes to take effect.")
            except Exception as e:
                self.log_debug(f"[SettingsTab] Error importing settings: {e}")
                messagebox.showerror("Error", f"Failed to import settings:\n{e}")
    
    def load_settings(self):
        """Load settings from file."""
        settings_file = "polyvox_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    for key, value in loaded.items():
                        if key in self.settings:
                            self.settings[key] = value
                self.log_debug(f"[SettingsTab] Settings loaded from {settings_file}")
            except Exception as e:
                self.log_debug(f"[SettingsTab] Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to file."""
        settings_file = "polyvox_settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            self.log_debug(f"[SettingsTab] Settings saved to {settings_file}")
        except Exception as e:
            self.log_debug(f"[SettingsTab] Error saving settings: {e}")
    
    def get_setting(self, key, default=None):
        """Get a specific setting value."""
        return self.settings.get(key, default)
