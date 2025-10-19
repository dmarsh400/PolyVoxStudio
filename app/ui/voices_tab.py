import os
import json
import customtkinter as ctk
from tkinter import messagebox, ttk


class VoicesTab(ctk.CTkFrame):
    def __init__(self, master, characters_tab=None, audio_tab=None, debug_callback=None, **kwargs):
        # References to other tabs (wired in from main_ui)
        self.characters_tab = characters_tab
        self.audio_tab = audio_tab
        self.debug_callback = debug_callback

        # Clean out unused kwargs
        kwargs.pop("character_provider", None)
        kwargs.pop("voices_file", None)
        kwargs.pop("log_debug", None)

        super().__init__(master, **kwargs)

        # File paths - now using complete XTTS voice library
        self.voices_file = "voices_complete_xtts.json"
        self.selections_file = os.path.join("app", "voices_selections.json")

        self.narrators = []
        self.voices = []
        self.voice_selections = {}

        self._load_voices_json()
        self._load_selections()
        self._build_ui()

    # ---------------- JSON ----------------
    def _load_voices_json(self):
        if not os.path.exists(self.voices_file):
            self._log(f"[VoicesTab] voices.json not found at {self.voices_file}")
            return

        try:
            with open(self.voices_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.narrators = data.get("narrators", [])
            self.voices = data.get("voices", [])
            self._log(f"[VoicesTab] Loaded {len(self.narrators)} narrators and {len(self.voices)} voices")
        except Exception as e:
            self._log(f"[VoicesTab] Failed to load voices.json: {e}")

    def _load_selections(self):
        if os.path.exists(self.selections_file):
            try:
                with open(self.selections_file, "r", encoding="utf-8") as f:
                    self.voice_selections = json.load(f)
                self._log(f"[VoicesTab] Loaded selections: {self.voice_selections}")
            except Exception as e:
                self._log(f"[VoicesTab] Failed to load voice selections: {e}")

    def _save_selections(self):
        try:
            with open(self.selections_file, "w", encoding="utf-8") as f:
                json.dump(self.voice_selections, f, indent=2)
            self._log(f"[VoicesTab] Saved selections: {self.voice_selections}")
        except Exception as e:
            self._log(f"[VoicesTab] Failed to save selections: {e}")

    # ---------------- UI ----------------
    def _build_ui(self):
        """Build split layout: left panel for voice management, right panel for assignments"""
        
        # Main container with 2 columns
        self.columnconfigure(0, weight=1)  # Left panel
        self.columnconfigure(1, weight=0)  # Separator
        self.columnconfigure(2, weight=2)  # Right panel (bigger)
        self.rowconfigure(0, weight=1)
        
        # ===== LEFT PANEL: Voice Management =====
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        
        # Title
        ctk.CTkLabel(left_panel, text="Voice Library", font=("Arial", 16, "bold")).pack(
            pady=(10, 5), padx=10, anchor="w"
        )
        
        # Voice list with scrollbar
        list_frame = ctk.CTkFrame(left_panel)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Treeview for voice list
        columns = ("name", "type", "gender", "age", "accent")
        self.voice_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=15,
        )
        self.voice_tree.heading("name", text="Voice Name")
        self.voice_tree.heading("type", text="Type")
        self.voice_tree.heading("gender", text="Gender")
        self.voice_tree.heading("age", text="Age")
        self.voice_tree.heading("accent", text="Accent")
        
        self.voice_tree.column("name", width=150)
        self.voice_tree.column("type", width=80)
        self.voice_tree.column("gender", width=80)
        self.voice_tree.column("age", width=80)
        self.voice_tree.column("accent", width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.voice_tree.yview)
        self.voice_tree.configure(yscrollcommand=scrollbar.set)
        
        self.voice_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Voice management buttons
        btn_frame = ctk.CTkFrame(left_panel)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame, text="🔄 Refresh List", command=self._refresh_voice_list
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="🗑 Delete Selected", command=self._delete_selected_voice,
            fg_color="red", hover_color="darkred"
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="ℹ View Details", command=self._view_voice_details
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="🎵 Test Voice", command=self._test_selected_voice
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="📝 Set as Default", command=self._set_as_default_narrator
        ).pack(fill="x", pady=2)
        
        # Voice statistics
        self.stats_label = ctk.CTkLabel(
            left_panel, text="Total Voices: 0 | Standard: 0 | Cloned: 0",
            font=("Arial", 10), text_color="gray"
        )
        self.stats_label.pack(pady=5)
        
        # ===== SEPARATOR =====
        separator = ctk.CTkFrame(self, width=2, fg_color="gray")
        separator.grid(row=0, column=1, sticky="ns", pady=10)
        
        # ===== RIGHT PANEL: Character-Voice Assignments =====
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="nsew")
        
        # Title
        ctk.CTkLabel(right_panel, text="Character Voice Assignments", font=("Arial", 16, "bold")).pack(
            pady=(10, 5), padx=10, anchor="w"
        )
        
        ctk.CTkButton(
            right_panel, text="🔄 Refresh Characters", command=self.refresh_characters
        ).pack(fill="x", padx=10, pady=5)

        self.assign_frame = ctk.CTkFrame(right_panel)
        self.assign_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(
            right_panel, text="▶ Send to Audio Processing", command=self.send_to_audio_processing,
            fg_color="green", hover_color="darkgreen"
        ).pack(fill="x", padx=10, pady=10)
        
        # Initial population
        self._refresh_voice_list()

    def refresh_characters(self):
        # Reload voices.json to ensure we have latest data
        self._load_voices_json()
        
        if not self.characters_tab:
            self._log("[VoicesTab] characters_tab not set.")
            return

        characters = self.characters_tab.get_characters()
        self._log(f"[VoicesTab] Refreshing characters → {characters}")

        # --- Ensure Narrator always has a default voice selection ---
        # If Narrator is present but has no selection yet, default it to the first available voice
        if "Narrator" in characters and "Narrator" not in self.voice_selections and self.voices:
            self.voice_selections["Narrator"] = self.voices[0]["label"]

        for widget in self.assign_frame.winfo_children():
            widget.destroy()

        if not characters:
            ctk.CTkLabel(self.assign_frame, text="No characters detected.").pack(pady=10)
            return

        # Build voice options with metadata for better identification
        all_options = []
        voice_label_map = {}  # Maps display label to actual label
        
        for v in self.voices:
            actual_label = v["label"]
            display_label = actual_label
            
            # Add metadata hints if available
            hints = []
            if v.get("gender") and v["gender"] != "Unknown":
                hints.append(v["gender"])
            if v.get("age"):
                hints.append(v["age"])
            if v.get("accent"):
                hints.append(v["accent"])
            
            if hints:
                display_label = f"{actual_label} [{', '.join(hints)}]"
            
            all_options.append(display_label)
            voice_label_map[display_label] = actual_label
        
        if not all_options:
            all_options = ["(No voices available)"]
        default_voice = all_options[0]

        for char in characters:
            frame = ctk.CTkFrame(self.assign_frame)
            frame.pack(fill="x", pady=2)
            ctk.CTkLabel(frame, text=char, width=120, anchor="w").pack(side="left", padx=5)

            # Get the actual label for this character
            actual_selection = self.voice_selections.get(char, voice_label_map.get(default_voice, default_voice))
            
            # Find the display label that matches this actual label
            display_selection = default_voice
            for display, actual in voice_label_map.items():
                if actual == actual_selection:
                    display_selection = display
                    break
            
            # Assign default if not already
            if char not in self.voice_selections:
                self.voice_selections[char] = voice_label_map.get(default_voice, default_voice)
                self._save_selections()
                self._log(f"[VoicesTab] Assigned default voice {actual_selection} to {char}")

            menu = ctk.CTkOptionMenu(
                frame,
                values=all_options,
                command=lambda choice, c=char, vlm=voice_label_map: self._set_voice_with_map(c, choice, vlm),
            )
            menu.set(display_selection)
            menu.pack(side="left", padx=5)
    
    def _set_voice_with_map(self, character, display_choice, voice_label_map):
        """Set voice selection, converting from display label to actual label"""
        actual_label = voice_label_map.get(display_choice, display_choice)
        self.voice_selections[character] = actual_label
        self._save_selections()
        self._log(f"[VoicesTab] {character} → {actual_label}")

    def _set_voice(self, character, choice):
        self.voice_selections[character] = choice
        self._save_selections()
        self._log(f"[VoicesTab] {character} → {choice}")

    def _find_voice_by_label(self, label):
        for v in (self.narrators + self.voices):
            if v.get("label") == label:
                return v
        return None

    # ---------------- Jobs ----------------
    def send_to_audio_processing(self):
        if not self.audio_tab or not self.characters_tab:
            self._log("[VoicesTab] Missing audio_tab or characters_tab")
            return

        dialogue_data = self.characters_tab.get_chapter_dialogue()
        if not dialogue_data:
            self._log("[VoicesTab] No dialogue data found")
            return

        jobs = []
        skipped = 0
        for chapter, lines in dialogue_data.items():
            job = {
                "chapter": chapter,
                "lines": [],
                "speakers": [],
                "voice_labels": [],
                "voice_entries": [],
            }
            for speaker, text in lines:
                voice_label = self.voice_selections.get(speaker)

                # If it's Narrator and no voice is set yet, default to the first available voice
                if (not voice_label) and speaker == "Narrator" and self.voices:
                    voice_label = self.voices[0]["label"]
                    self.voice_selections["Narrator"] = voice_label  # persist it so the UI reflects this choice

                if not voice_label:
                    skipped += 1
                    continue

                voice_entry = self._find_voice_by_label(voice_label)
                if not voice_entry:
                    skipped += 1
                    continue
                job["lines"].append(text)
                job["speakers"].append(speaker)
                job["voice_labels"].append(voice_label)
                job["voice_entries"].append(voice_entry)
            if job["lines"]:
                jobs.append(job)

        if jobs:
            self.audio_tab.add_jobs(jobs)
            self._log(f"[VoicesTab] Sent {len(jobs)} jobs to Audio Processing. Skipped {skipped} lines.")
        else:
            self._log(f"[VoicesTab] No jobs created. Skipped {skipped} lines.")

    # ---------------- Voice Management Methods ----------------
    def _refresh_voice_list(self):
        """Refresh the voice library list"""
        # Reload voices from JSON
        self._load_voices_json()
        
        # Clear existing items
        for item in self.voice_tree.get_children():
            self.voice_tree.delete(item)
        
        # Count voices
        standard_count = 0
        cloned_count = 0
        
        # Add all voices to tree
        all_voices = self.narrators + self.voices
        for voice in all_voices:
            name = voice.get("label", "Unknown")
            voice_type = "Cloned" if voice.get("custom_cloned", False) else "Standard"
            gender = voice.get("gender", "-")
            age = voice.get("age", "-")
            accent = voice.get("accent", "-")
            
            if voice.get("custom_cloned", False):
                cloned_count += 1
            else:
                standard_count += 1
            
            self.voice_tree.insert("", "end", values=(name, voice_type, gender, age, accent))
        
        # Update statistics
        total = len(all_voices)
        self.stats_label.configure(
            text=f"Total Voices: {total} | Standard: {standard_count} | Cloned: {cloned_count}"
        )
        
        self._log(f"[VoicesTab] Voice list refreshed: {total} voices")
    
    def _delete_selected_voice(self):
        """Delete the selected voice from the library"""
        selection = self.voice_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a voice to delete.")
            return
        
        item = selection[0]
        values = self.voice_tree.item(item, "values")
        voice_name = values[0]
        voice_type = values[1]
        
        # Confirm deletion
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{voice_name}' ({voice_type})?\n\n"
            "This action cannot be undone."
        )
        
        if not response:
            return
        
        # Find and remove the voice
        all_voices = self.narrators + self.voices
        voice_to_remove = None
        
        for voice in all_voices:
            if voice.get("label") == voice_name:
                voice_to_remove = voice
                break
        
        if not voice_to_remove:
            messagebox.showerror("Error", f"Voice '{voice_name}' not found.")
            return
        
        # Remove from appropriate list
        if voice_to_remove in self.narrators:
            self.narrators.remove(voice_to_remove)
        elif voice_to_remove in self.voices:
            self.voices.remove(voice_to_remove)
        
        # Save updated voices.json
        self._save_voices_json()
        
        # Remove from selections if it was assigned
        chars_to_update = [char for char, voice in self.voice_selections.items() if voice == voice_name]
        for char in chars_to_update:
            del self.voice_selections[char]
        if chars_to_update:
            self._save_selections()
        
        # Refresh display
        self._refresh_voice_list()
        self.refresh_characters()  # Update character assignments
        
        messagebox.showinfo("Success", f"Voice '{voice_name}' has been deleted.")
        self._log(f"[VoicesTab] Deleted voice: {voice_name}")
    
    def _view_voice_details(self):
        """Display detailed information about the selected voice"""
        selection = self.voice_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a voice to view details.")
            return
        
        item = selection[0]
        values = self.voice_tree.item(item, "values")
        voice_name = values[0]
        
        # Find the voice
        all_voices = self.narrators + self.voices
        voice = None
        for v in all_voices:
            if v.get("label") == voice_name:
                voice = v
                break
        
        if not voice:
            messagebox.showerror("Error", f"Voice '{voice_name}' not found.")
            return
        
        # Build details string
        details = f"Voice Details: {voice_name}\n\n"
        details += f"Type: {'Custom Cloned' if voice.get('custom_cloned', False) else 'Standard'}\n"
        details += f"Gender: {voice.get('gender', 'Unknown')}\n"
        details += f"Age: {voice.get('age', 'Unknown')}\n"
        details += f"Accent: {voice.get('accent', 'Unknown')}\n"
        details += f"Description: {voice.get('description', 'No description')}\n\n"
        
        if voice.get("voice_file"):
            details += f"Voice File: {voice.get('voice_file')}\n"
        
        # Show in dialog
        messagebox.showinfo("Voice Details", details)
    
    def _test_selected_voice(self):
        """Test the selected voice with sample text"""
        selection = self.voice_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a voice to test.")
            return
        
        item = selection[0]
        values = self.voice_tree.item(item, "values")
        voice_name = values[0]
        
        messagebox.showinfo(
            "Test Voice",
            f"Voice testing for '{voice_name}' will be implemented.\n\n"
            "This will generate a sample audio using the voice.\n"
            "(Connect to Clone Voices tab test functionality)"
        )
        self._log(f"[VoicesTab] Test requested for voice: {voice_name}")
    
    def _set_as_default_narrator(self):
        """Set the selected voice as the default for Narrator"""
        selection = self.voice_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a voice to set as default narrator.")
            return
        
        item = selection[0]
        values = self.voice_tree.item(item, "values")
        voice_name = values[0]
        
        # Set Narrator to use this voice
        self.voice_selections["Narrator"] = voice_name
        self._save_selections()
        
        # Refresh character assignments to show the change
        self.refresh_characters()
        
        messagebox.showinfo("Success", f"'{voice_name}' is now the default narrator voice.")
        self._log(f"[VoicesTab] Set default narrator: {voice_name}")
    
    def _save_voices_json(self):
        """Save the current voices back to voices.json"""
        try:
            data = {
                "narrators": self.narrators,
                "voices": self.voices
            }
            with open(self.voices_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._log(f"[VoicesTab] Saved voices.json")
        except Exception as e:
            self._log(f"[VoicesTab] Failed to save voices.json: {e}")
            messagebox.showerror("Error", f"Failed to save voices: {e}")

    def _log(self, msg):
        print(msg)
        if self.debug_callback:
            self.debug_callback("[VoicesTab] " + msg)
