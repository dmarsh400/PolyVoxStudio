import os
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import shutil

VOICES_DIR = "voices/references"
VOICES_FILE = "voices_complete_xtts.json"


class CloneVoicesTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Main container with scrollable area
        main_container = ctk.CTkScrollableFrame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Header ---
        header = ctk.CTkLabel(main_container, text="Clone Voices", font=("Arial", 18, "bold"))
        header.pack(pady=10)

        # --- Audio Upload Section ---
        upload_frame = ctk.CTkFrame(main_container, border_width=2, border_color="gray")
        upload_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(upload_frame, text="1. Upload Voice Sample", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.upload_btn = ctk.CTkButton(upload_frame, text="Select Audio File", command=self.upload_audio)
        self.upload_btn.pack(pady=10)

        self.audio_path_var = tk.StringVar(value="No file selected")
        self.audio_label = ctk.CTkLabel(upload_frame, textvariable=self.audio_path_var, wraplength=500)
        self.audio_label.pack(pady=5, padx=10)

        # --- Voice Metadata Section ---
        metadata_frame = ctk.CTkFrame(main_container, border_width=2, border_color="gray")
        metadata_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(metadata_frame, text="2. Voice Information", font=("Arial", 14, "bold")).pack(pady=5)

        # Voice Name
        name_frame = ctk.CTkFrame(metadata_frame)
        name_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(name_frame, text="Voice Name:", width=120, anchor="w").pack(side="left", padx=5)
        self.voice_name_var = tk.StringVar()
        self.voice_name_entry = ctk.CTkEntry(name_frame, textvariable=self.voice_name_var, width=300,
                                             placeholder_text="e.g., 'Morgan Freeman Clone', 'Sarah_British'")
        self.voice_name_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Voice Type (Character voice vs Narrator)
        type_frame = ctk.CTkFrame(metadata_frame)
        type_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(type_frame, text="Voice Type:", width=120, anchor="w").pack(side="left", padx=5)
        self.voice_type_var = tk.StringVar(value="voice")
        voice_type_menu = ctk.CTkOptionMenu(type_frame, variable=self.voice_type_var, 
                                            values=["voice", "narrator"],
                                            width=200)
        voice_type_menu.pack(side="left", padx=5)
        ctk.CTkLabel(type_frame, text="(voice = character, narrator = narration)", 
                    font=("Arial", 10), text_color="gray").pack(side="left", padx=10)

        # Gender
        gender_frame = ctk.CTkFrame(metadata_frame)
        gender_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(gender_frame, text="Gender:", width=120, anchor="w").pack(side="left", padx=5)
        self.gender_var = tk.StringVar(value="Unknown")
        gender_menu = ctk.CTkOptionMenu(gender_frame, variable=self.gender_var, 
                                       values=["Male", "Female", "Non-Binary", "Unknown"],
                                       width=200)
        gender_menu.pack(side="left", padx=5)

        # Age Range
        age_frame = ctk.CTkFrame(metadata_frame)
        age_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(age_frame, text="Age Range:", width=120, anchor="w").pack(side="left", padx=5)
        self.age_var = tk.StringVar(value="Adult")
        age_menu = ctk.CTkOptionMenu(age_frame, variable=self.age_var, 
                                     values=["Child", "Teen", "Young Adult", "Adult", "Middle-Aged", "Senior"],
                                     width=200)
        age_menu.pack(side="left", padx=5)

        # Accent/Style
        accent_frame = ctk.CTkFrame(metadata_frame)
        accent_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(accent_frame, text="Accent/Style:", width=120, anchor="w").pack(side="left", padx=5)
        self.accent_var = tk.StringVar()
        accent_entry = ctk.CTkEntry(accent_frame, textvariable=self.accent_var, width=300,
                                   placeholder_text="e.g., 'British', 'Southern US', 'Neutral', 'Dramatic'")
        accent_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Description
        desc_label_frame = ctk.CTkFrame(metadata_frame)
        desc_label_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(desc_label_frame, text="Description:", width=120, anchor="w").pack(side="left", padx=5)
        
        self.description_var = tk.StringVar()
        desc_entry = ctk.CTkEntry(metadata_frame, textvariable=self.description_var, 
                                 placeholder_text="Brief description to help identify this voice...")
        desc_entry.pack(fill="x", pady=5, padx=135)

        # --- Generate Button ---
        self.generate_btn = ctk.CTkButton(main_container, text="Generate & Save Voice", 
                                         command=self.generate_voice, height=40,
                                         font=("Arial", 14, "bold"))
        self.generate_btn.pack(pady=20)

        # --- Test Voice Section ---
        test_frame = ctk.CTkFrame(main_container, border_width=2, border_color="gray")
        test_frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(test_frame, text="3. Test Existing Voice", font=("Arial", 14, "bold")).pack(pady=5)

        # Select existing voice to test
        select_frame = ctk.CTkFrame(test_frame)
        select_frame.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(select_frame, text="Select Voice:", width=120, anchor="w").pack(side="left", padx=5)
        self.placeholder_var = tk.StringVar()
        self.placeholder_menu = ctk.CTkOptionMenu(select_frame, variable=self.placeholder_var, values=["(no voices yet)"])
        self.placeholder_menu.pack(side="left", padx=5, fill="x", expand=True)
        
        refresh_btn = ctk.CTkButton(select_frame, text="🔄", width=40, command=self.refresh_placeholders)
        refresh_btn.pack(side="left", padx=5)

        # Sample text
        ctk.CTkLabel(test_frame, text="Sample Text:", anchor="w").pack(fill="x", padx=10, pady=(10, 2))
        self.sample_text = tk.StringVar(value="Hello, I'm your voice. Welcome to PolyVox Studio!")
        self.sample_entry = ctk.CTkEntry(test_frame, textvariable=self.sample_text)
        self.sample_entry.pack(fill="x", padx=10, pady=5)

        self.play_btn = ctk.CTkButton(test_frame, text="▶ Play Sample", command=self.play_sample)
        self.play_btn.pack(pady=10)

        # --- Log output ---
        ctk.CTkLabel(main_container, text="Activity Log", font=("Arial", 12, "bold")).pack(pady=(10, 5))
        self.log_box = tk.Text(main_container, height=8, state="disabled", wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.refresh_placeholders()

    # -------------------------
    def log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    # -------------------------
    def upload_audio(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.flac")])
        if file_path:
            self.audio_path_var.set(file_path)
            self.log(f"Selected audio: {file_path}")

    # -------------------------
    def refresh_placeholders(self):
        """Refresh the list of available voices with metadata display"""
        if not os.path.exists(VOICES_FILE):
            with open(VOICES_FILE, "w") as f:
                json.dump({"voices": [], "narrators": []}, f, indent=2)

        with open(VOICES_FILE, "r") as f:
            data = json.load(f)

        # Build voice list with metadata for display
        voice_labels = []
        
        # Add character voices
        for v in data.get("voices", []):
            label = v["label"]
            # Add metadata hints if available
            hints = []
            if v.get("gender") and v["gender"] != "Unknown":
                hints.append(v["gender"])
            if v.get("age"):
                hints.append(v["age"])
            if hints:
                label += f" [{', '.join(hints)}]"
            voice_labels.append(label)
        
        # Add narrator voices
        for n in data.get("narrators", []):
            label = n["label"]
            # Add metadata hints if available
            hints = ["Narrator"]
            if n.get("gender") and n["gender"] != "Unknown":
                hints.append(n["gender"])
            if n.get("age"):
                hints.append(n["age"])
            label += f" [{', '.join(hints)}]"
            voice_labels.append(label)

        if not voice_labels:
            voice_labels = ["(no voices yet)"]

        self.placeholder_menu.configure(values=voice_labels)
        self.placeholder_var.set(voice_labels[0])
        
        self.log(f"Refreshed voice list: {len(voice_labels)} voice(s) available")

    # -------------------------
    def generate_voice(self):
        """Generate and save a cloned voice with metadata"""
        audio_path = self.audio_path_var.get()
        
        # Validate audio file
        if not os.path.exists(audio_path) or audio_path == "No file selected":
            messagebox.showerror("Error", "Please select a valid audio file first.")
            return

        # Get metadata from form - also try direct widget access as fallback
        voice_name = self.voice_name_var.get().strip()
        if not voice_name:
            # Fallback: try getting value directly from entry widget
            voice_name = self.voice_name_entry.get().strip()
        
        voice_type = self.voice_type_var.get()
        gender = self.gender_var.get()
        age = self.age_var.get()
        accent = self.accent_var.get().strip()
        description = self.description_var.get().strip()

        # Validate required fields
        if not voice_name:
            messagebox.showerror("Error", "Please provide a voice name.")
            return

        # Create safe filename from voice name
        safe_name = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in voice_name)
        safe_name = safe_name.replace(' ', '_').lower()

        # Build full description with metadata
        metadata_parts = []
        if gender != "Unknown":
            metadata_parts.append(gender)
        if age:
            metadata_parts.append(age)
        if accent:
            metadata_parts.append(accent)
        
        full_description = description if description else f"Cloned voice: {voice_name}"
        if metadata_parts:
            full_description += f" ({', '.join(metadata_parts)})"

        os.makedirs(VOICES_DIR, exist_ok=True)
        
        # For XTTS, we need a WAV reference file, not a Bark history prompt
        # Copy the uploaded audio to the voices/references directory
        import shutil
        voice_ref_path = os.path.join(VOICES_DIR, f"{safe_name}.wav")

        try:
            self.log(f"Processing audio file: {os.path.basename(audio_path)}")
            self.log(f"Copying voice reference for '{voice_name}'...")
            self.update_idletasks()

            # Copy the audio file to references directory
            shutil.copy2(audio_path, voice_ref_path)
            self.log(f"Voice reference saved to: {voice_ref_path}")

            # Load existing voices
            if not os.path.exists(VOICES_FILE):
                data = {"narrators": [], "voices": []}
            else:
                with open(VOICES_FILE, "r") as f:
                    data = json.load(f)

            # Create voice entry with XTTS-compatible structure
            # Generate a unique ID from the safe_name
            voice_id = f"cloned_{safe_name}"
            
            entry = {
                "id": voice_id,
                "label": voice_name,
                "description": full_description,
                "voice_file": voice_ref_path,
                "engine": "xtts",
                "gender": gender,
                "age": age,
                "accent": accent if accent else "Custom",
                "personality": "Custom Cloned",
                "custom_cloned": True,
                "source_file": os.path.basename(audio_path)
            }

            # Insert into correct section (voices or narrators)
            target = "voices" if voice_type == "voice" else "narrators"
            
            # Check for duplicates
            existing = data.get(target, [])
            duplicate_idx = next((i for i, v in enumerate(existing) if v["label"] == voice_name), None)
            
            if duplicate_idx is not None:
                # Ask user if they want to overwrite
                response = messagebox.askyesno(
                    "Voice Exists",
                    f"A {voice_type} named '{voice_name}' already exists.\n\n"
                    f"Do you want to overwrite it?"
                )
                if response:
                    existing[duplicate_idx] = entry
                    self.log(f"Overwritten existing {voice_type}: '{voice_name}'")
                else:
                    self.log("Generation cancelled by user.")
                    return
            else:
                # Add new voice
                existing.append(entry)
                data[target] = existing

            # Save to file
            with open(VOICES_FILE, "w") as f:
                json.dump(data, f, indent=2)

            self.log(f"✅ Successfully saved {voice_type}: '{voice_name}'")
            self.log(f"   Gender: {gender}, Age: {age}, Accent: {accent or 'N/A'}")
            
            # Refresh the dropdown
            self.refresh_placeholders()
            
            # Show success message
            messagebox.showinfo(
                "Success",
                f"Voice '{voice_name}' created successfully!\n\n"
                f"Type: {voice_type.title()}\n"
                f"Gender: {gender}\n"
                f"Age: {age}\n"
                f"Accent: {accent or 'N/A'}\n\n"
                f"The voice is now available in the Voices tab for character assignment."
            )
            
            # Clear form
            self.voice_name_var.set("")
            self.description_var.set("")
            self.accent_var.set("")
            self.audio_path_var.set("No file selected")
            
        except Exception as e:
            self.log(f"❌ Error generating voice: {e}")
            messagebox.showerror("Error", f"Failed to generate voice:\n{e}")

    # -------------------------
    def play_sample(self):
        """Play a sample of the selected voice using XTTS"""
        selected = self.placeholder_var.get()
        if not selected or selected == "(no voices yet)":
            messagebox.showerror("Error", "Please select a valid voice first.")
            return

        # Extract the actual voice name (remove metadata hints in brackets)
        # Format: "Voice Name [Gender, Age]" -> "Voice Name"
        voice_name = selected.split('[')[0].strip()

        if not os.path.exists(VOICES_FILE):
            messagebox.showerror("Error", "Voice configuration file not found.")
            return

        with open(VOICES_FILE, "r") as f:
            data = json.load(f)

        all_entries = data.get("voices", []) + data.get("narrators", [])
        voice_entry = next((v for v in all_entries if v["label"] == voice_name), None)
        
        if not voice_entry:
            messagebox.showerror("Error", f"No voice found for '{voice_name}'.")
            return

        text = self.sample_text.get()
        if not text.strip():
            messagebox.showerror("Error", "Please enter sample text to play.")
            return

        try:
            self.log(f"Generating audio sample for '{voice_name}' using XTTS...")
            self.update_idletasks()
            
            # Use XTTS for synthesis
            from TTS.api import TTS
            import sounddevice as sd
            import soundfile as sf
            
            # Load XTTS model
            tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2').to('cuda')
            
            out_path = "temp_sample.wav"
            voice_file = voice_entry.get("voice_file", "")
            
            if not os.path.exists(voice_file):
                messagebox.showerror("Error", f"Voice reference file not found: {voice_file}")
                return
            
            # Generate audio
            tts.tts_to_file(
                text=text,
                speaker_wav=voice_file,
                language="en",
                file_path=out_path
            )

            self.log(f"Playing sample...")
            
            # Read and play audio
            data_audio, samplerate = sf.read(out_path)
            sd.play(data_audio, samplerate)
            sd.wait()

            self.log(f"✅ Played sample for '{voice_name}'")
        except Exception as e:
            self.log(f"❌ Error playing sample: {e}")
            messagebox.showerror("Error", f"Failed to play sample:\n{e}")
