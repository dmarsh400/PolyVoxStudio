import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import re
import subprocess
import sys
import numpy as np
from typing import List, Dict, Any
from pydub import AudioSegment
import soundfile as sf

from app.core.voices import synthesize_text


class AudioQualityChecker:
    """
    Automatic audio quality validation to detect common TTS artifacts and issues.
    """
    
    @staticmethod
    def validate_audio(file_path: str, text: str = "") -> Dict[str, Any]:
        """
        Validate audio file for quality issues and artifacts.
        
        Returns:
            Dict with 'passed', 'issues', 'score', 'warnings'
        """
        issues = []
        warnings = []
        score = 100.0
        
        try:
            # Load audio
            audio, sample_rate = sf.read(file_path)
            
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            duration = len(audio) / sample_rate
            
            # Check 1: Duration validation
            if duration < 0.1:
                issues.append("Audio too short (< 0.1s)")
                score -= 30
            elif duration > 120:
                warnings.append(f"Long audio detected ({duration:.1f}s)")
            
            # Check 2: Silence detection
            silence_threshold = 0.01
            silence_ratio = np.sum(np.abs(audio) < silence_threshold) / len(audio)
            if silence_ratio > 0.9:
                issues.append(f"Excessive silence detected ({silence_ratio*100:.1f}%)")
                score -= 25
            elif silence_ratio > 0.7:
                warnings.append(f"High silence ratio ({silence_ratio*100:.1f}%)")
                score -= 10
            
            # Check 3: Clipping detection
            clipping_threshold = 0.99
            clipping_samples = np.sum(np.abs(audio) > clipping_threshold)
            clipping_ratio = clipping_samples / len(audio)
            if clipping_ratio > 0.01:
                issues.append(f"Clipping detected ({clipping_ratio*100:.2f}%)")
                score -= 20
            elif clipping_ratio > 0.001:
                warnings.append(f"Minor clipping ({clipping_ratio*100:.3f}%)")
                score -= 5
            
            # Check 4: Volume level check
            rms = np.sqrt(np.mean(audio**2))
            if rms < 0.01:
                issues.append(f"Audio too quiet (RMS: {rms:.4f})")
                score -= 15
            elif rms > 0.7:
                warnings.append(f"Audio very loud (RMS: {rms:.4f})")
                score -= 5
            
            # Check 5: Dynamic range
            dynamic_range = np.max(np.abs(audio)) - np.min(np.abs(audio))
            if dynamic_range < 0.1:
                issues.append(f"Low dynamic range ({dynamic_range:.3f})")
                score -= 15
            
            # Check 6: Unexpected noise/artifacts (simplified detection)
            # Check for sudden spikes that might indicate artifacts
            audio_diff = np.diff(audio)
            sudden_changes = np.sum(np.abs(audio_diff) > 0.5) / len(audio_diff)
            if sudden_changes > 0.05:
                warnings.append(f"Possible artifacts detected ({sudden_changes*100:.2f}% spikes)")
                score -= 10
            
            # Check 7: Sample rate validation
            if sample_rate < 16000:
                warnings.append(f"Low sample rate ({sample_rate} Hz)")
                score -= 5
            
            # Check 8: Text/audio length correlation (if text provided)
            if text:
                # Rough estimate: ~150 words per minute, ~5 chars per word
                expected_duration = (len(text) / 5) / 150 * 60  # seconds
                if duration < expected_duration * 0.3:
                    issues.append(f"Audio too short for text length ({duration:.1f}s vs expected ~{expected_duration:.1f}s)")
                    score -= 20
                elif duration > expected_duration * 3:
                    warnings.append(f"Audio longer than expected ({duration:.1f}s vs ~{expected_duration:.1f}s)")
            
            # Ensure score doesn't go below 0
            score = max(0, score)
            
            # Determine pass/fail
            passed = score >= 60 and len(issues) == 0
            
            return {
                "passed": passed,
                "score": score,
                "issues": issues,
                "warnings": warnings,
                "duration": duration,
                "sample_rate": sample_rate,
                "rms": rms,
                "silence_ratio": silence_ratio
            }
            
        except Exception as e:
            return {
                "passed": False,
                "score": 0,
                "issues": [f"Validation error: {str(e)}"],
                "warnings": [],
                "duration": 0,
                "sample_rate": 0,
                "rms": 0,
                "silence_ratio": 0
            }
    
    @staticmethod
    def should_retry(validation_result: Dict[str, Any]) -> bool:
        """Determine if audio should be regenerated based on quality issues."""
        return not validation_result["passed"]


class AudioProcessingTab(ctk.CTkFrame):
    def __init__(self, master, log_debug=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.log_debug = log_debug or (lambda msg: print(msg))
        self.jobs: List[Dict[str, Any]] = []
        self.processing = False
        self.worker_thread = None
        self.output_root = os.path.join("output", "audio")  # default output dir
        self.row_vars: Dict[int, tk.BooleanVar] = {}  # store checkbox states by row index
        self.checkbox_states: Dict[int, bool] = {}  # cache of checkbox states for thread-safe access
        
        # Quality control settings
        self.enable_quality_check = tk.BooleanVar(value=True)
        self.max_retries = 2
        self.quality_threshold = 60  # Minimum score to pass
        
        # Progress tracking
        self.current_job_progress = tk.StringVar(value="")
        self.overall_progress = tk.StringVar(value="Ready")
        self.processed_lines = 0
        self.total_lines = 0
        self.failed_lines = 0
        self.retried_lines = 0

        self._build_layout()

    # ---------------- UI ----------------
    def _build_layout(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            header_frame, text="Audio Processing", font=("Arial", 24, "bold")
        ).pack(side="left")
        
        self.overall_status_label = ctk.CTkLabel(
            header_frame, textvariable=self.overall_progress, 
            font=("Arial", 12), text_color="gray"
        ).pack(side="right", padx=10)
        
        # Control Panel
        control_frame = ctk.CTkFrame(self, border_width=2, border_color="gray")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(control_frame, text="Controls", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=3, pady=5, sticky="w", padx=10
        )
        
        # Row 1: Processing controls
        ctk.CTkButton(
            control_frame, text="▶ Start Processing", command=self.start_processing,
            fg_color="green", hover_color="darkgreen", width=150
        ).grid(row=1, column=0, padx=5, pady=5)
        
        ctk.CTkButton(
            control_frame, text="■ Stop", command=self.stop_processing,
            fg_color="red", hover_color="darkred", width=100
        ).grid(row=1, column=1, padx=5, pady=5)
        
        ctk.CTkButton(
            control_frame, text="🗑 Clear Queue", command=self.clear_queue,
            width=120
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Row 2: Output controls
        ctk.CTkButton(
            control_frame, text="📁 Select Output Folder", command=self.select_output_folder,
            width=170
        ).grid(row=2, column=0, padx=5, pady=5)
        
        ctk.CTkButton(
            control_frame, text="📂 Open Output", command=self.open_output_folder,
            width=130
        ).grid(row=2, column=1, padx=5, pady=5)
        
        ctk.CTkButton(
            control_frame, text="📚 Export M4B", command=self.merge_all_to_m4b,
            width=120
        ).grid(row=2, column=2, padx=5, pady=5)
        
        # Row 3: Quality control
        quality_check_cb = ctk.CTkCheckBox(
            control_frame, text="Enable Quality Check (Auto-retry failed audio)",
            variable=self.enable_quality_check
        )
        quality_check_cb.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        self.output_label = ctk.CTkLabel(
            control_frame, text=f"Output: {self.output_root}",
            font=("Arial", 10), text_color="gray"
        )
        self.output_label.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        
        # Progress Section
        progress_frame = ctk.CTkFrame(self, border_width=2, border_color="gray")
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(progress_frame, text="Progress", font=("Arial", 14, "bold")).pack(
            anchor="w", padx=10, pady=(5, 2)
        )
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=400, height=20)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)
        
        self.current_job_label = ctk.CTkLabel(
            progress_frame, textvariable=self.current_job_progress,
            font=("Arial", 11), text_color="blue"
        )
        self.current_job_label.pack(anchor="w", padx=10, pady=2)
        
        # Statistics display
        stats_inner = ctk.CTkFrame(progress_frame, fg_color="transparent")
        stats_inner.pack(fill="x", padx=10, pady=5)
        
        self.stat_total = ctk.CTkLabel(stats_inner, text="Total: 0", font=("Arial", 10))
        self.stat_total.pack(side="left", padx=10)
        
        self.stat_processed = ctk.CTkLabel(stats_inner, text="Processed: 0", 
                                           font=("Arial", 10), text_color="green")
        self.stat_processed.pack(side="left", padx=10)
        
        self.stat_failed = ctk.CTkLabel(stats_inner, text="Failed: 0", 
                                        font=("Arial", 10), text_color="red")
        self.stat_failed.pack(side="left", padx=10)
        
        self.stat_retried = ctk.CTkLabel(stats_inner, text="Retried: 0", 
                                         font=("Arial", 10), text_color="orange")
        self.stat_retried.pack(side="left", padx=10)
        
        # Queue Section
        queue_frame = ctk.CTkFrame(self, border_width=2, border_color="gray")
        queue_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(queue_frame, text="Processing Queue", font=("Arial", 14, "bold")).pack(
            anchor="w", padx=10, pady=(5, 2)
        )
        
        # Treeview with enhanced columns and visual styling
        tree_frame = ctk.CTkFrame(queue_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Configure Treeview style for better visual separation
        style = ttk.Style()
        style.configure("Queue.Treeview", 
                       rowheight=30,  # Taller rows
                       borderwidth=1)
        style.configure("Queue.Treeview.Heading", 
                       font=("Arial", 11, "bold"))
        style.map("Queue.Treeview",
                 background=[("selected", "#0078D7")])
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("select", "chapter", "speaker", "voice", "lines", "status", "quality"),
            show="headings",
            height=15,
            style="Queue.Treeview"
        )
        self.tree.heading("select", text="☑")
        self.tree.heading("chapter", text="Chapter")
        self.tree.heading("speaker", text="Speaker")
        self.tree.heading("voice", text="Voice")
        self.tree.heading("lines", text="Lines")
        self.tree.heading("status", text="Status")
        self.tree.heading("quality", text="Quality")

        self.tree.column("select", width=50, anchor="center")
        self.tree.column("chapter", width=150)
        self.tree.column("speaker", width=120)
        self.tree.column("voice", width=180)
        self.tree.column("lines", width=70, anchor="center")
        self.tree.column("status", width=150)
        self.tree.column("quality", width=100, anchor="center")
        
        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add alternating row colors for visual separation
        self.tree.tag_configure('oddrow', background='#f0f0f0')
        self.tree.tag_configure('evenrow', background='#ffffff')

    def stop_processing(self):
        """Stop processing (gracefully)"""
        if self.processing:
            self.processing = False
            self.log_debug("[AudioProcessingTab] Stop requested...")
        else:
            messagebox.showinfo("Info", "No processing in progress.")

    # ---------------- Queue ops ----------------
    def add_jobs(self, jobs: List[Dict[str, Any]]):
        for job in jobs:
            job.setdefault("status", "Pending")
            job.setdefault("quality_score", "-")
            self.jobs.append(job)
            speakers = job.get("speakers", ["Unknown"])
            voice_labels = job.get("voice_labels", [job.get("voice_label", "")])
            speaker_display = ", ".join(set(speakers))
            voice_display = ", ".join(set(voice_labels))
            chapter = job.get("chapter", "Chapter_Unknown")

            idx = len(self.jobs) - 1
            # Apply alternating row colors
            row_tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            
            row_id = self.tree.insert(
                "",
                "end",
                values=(
                    "[X]",  # checkbox placeholder
                    chapter,
                    speaker_display,
                    voice_display,
                    len(job.get("lines", [])),
                    job["status"],
                    job["quality_score"]
                ),
                tags=(row_tag,)
            )
            self.row_vars[idx] = tk.BooleanVar(value=True)  # default checked
            self._update_checkbox_display(idx)
            
            # Add to total lines count
            self.total_lines += len(job.get("lines", []))

            self.log_debug(
                f"[AudioProcessingTab] Added job for chapter {chapter} with {len(job.get('lines', []))} lines"
            )
        
        self._update_statistics()
        self.log_debug(f"[AudioProcessingTab] Added {len(jobs)} jobs to queue (total lines: {self.total_lines})")
        self.tree.bind("<Button-1>", self._on_tree_click)

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        column = self.tree.identify_column(event.x)
        if column != "#1":  # only checkbox column
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        idx = self.tree.index(row_id)
        if idx in self.row_vars:
            current = self.row_vars[idx].get()
            self.row_vars[idx].set(not current)
            self._update_checkbox_display(idx)

    def _update_checkbox_display(self, idx: int):
        row_id = self.tree.get_children()[idx]
        state = self.row_vars[idx].get()
        self.tree.set(row_id, "select", "[X]" if state else "[ ]")
    
    def _update_statistics(self):
        """Update the statistics display"""
        # Use after() to update from main thread
        self.after(0, self._update_statistics_ui)
    
    def _update_statistics_ui(self):
        """Update statistics UI - must be called from main thread."""
        self.stat_total.configure(text=f"Total: {self.total_lines}")
        self.stat_processed.configure(text=f"Processed: {self.processed_lines}")
        self.stat_failed.configure(text=f"Failed: {self.failed_lines}")
        self.stat_retried.configure(text=f"Retried: {self.retried_lines}")
        
        if self.total_lines > 0:
            progress = self.processed_lines / self.total_lines
            self.progress_bar.set(progress)
            percentage = int(progress * 100)
            self.overall_progress.set(f"{percentage}% Complete ({self.processed_lines}/{self.total_lines})")
    
    def _set_current_progress(self, text):
        """Thread-safe way to set current job progress."""
        self.after(0, lambda: self.current_job_progress.set(text))
    
    def _set_overall_progress(self, text):
        """Thread-safe way to set overall progress."""
        self.after(0, lambda: self.overall_progress.set(text))

    def _show_info(self, title, message):
        """Thread-safe way to show info messagebox."""
        self.after(0, lambda: messagebox.showinfo(title, message))
    
    def _show_error(self, title, message):
        """Thread-safe way to show error messagebox."""
        self.after(0, lambda: messagebox.showerror(title, message))

    def clear_queue(self):
        self.jobs.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.row_vars.clear()
        
        # Reset statistics
        self.processed_lines = 0
        self.total_lines = 0
        self.failed_lines = 0
        self.retried_lines = 0
        self._update_statistics()
        self.progress_bar.set(0)
        self.current_job_progress.set("")
        self.overall_progress.set("Ready")
        
        self.log_debug("[AudioProcessingTab] Queue cleared.")

    def start_processing(self):
        if self.processing:
            messagebox.showinfo("Info", "Already processing.")
            return
        if not self.jobs:
            messagebox.showwarning("Warning", "No jobs in queue.")
            return

        # Cache checkbox states for thread-safe access
        self.checkbox_states.clear()
        for idx in range(len(self.jobs)):
            if idx in self.row_vars:
                self.checkbox_states[idx] = self.row_vars[idx].get()
            else:
                self.checkbox_states[idx] = False
        
        # Cache settings for thread-safe access
        self.quality_check_enabled = self.enable_quality_check.get()
        self.cached_max_retries = self.max_retries
        
        selected_jobs = [
            (idx, job) for idx, job in enumerate(self.jobs) 
            if self.checkbox_states.get(idx, False)
        ]
        if not selected_jobs:
            messagebox.showwarning("Warning", "No chapters selected.")
            return

        self.jobs_to_process = selected_jobs
        os.makedirs(self.output_root, exist_ok=True)
        self.processing = True
        self.worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.worker_thread.start()
        self.log_debug("[AudioProcessingTab] Started processing selected jobs.")

    # ---------------- Synthesis loop ----------------
    def _process_loop(self):
        chapters_map = {}
        quality_checker = AudioQualityChecker()

        for idx, job in self.jobs_to_process:
            if not self.processing:  # Check if stopped
                self.log_debug("[AudioProcessingTab] Processing stopped by user")
                break
                
            try:
                job["status"] = "Processing"
                self._update_tree(idx, job)

                chapter = job.get("chapter", "Chapter_Unknown")
                chapter_dir = self._safe_name(chapter)
                lines = job.get("lines", [])
                speakers = job.get("speakers", ["Unknown"] * len(lines))
                voice_entries = job.get("voice_entries", [{}] * len(lines))
                voice_labels = job.get("voice_labels", [""] * len(lines))

                # Preprocessing: Split long texts into chunks at sentence boundaries
                processed_lines = []
                processed_speakers = []
                processed_voice_entries = []
                processed_voice_labels = []
                
                for text, speaker, voice_entry, voice_label in zip(lines, speakers, voice_entries, voice_labels):
                    if len(text) > 250:
                        # Split long text into chunks (XTTS has 250 char limit for English)
                        chunks = self._split_long_text(text, max_chars=250)
                        self.log_debug(f"[AudioProcessingTab] Split long text ({len(text)} chars) into {len(chunks)} chunks")
                        # Add each chunk with the same speaker/voice
                        for chunk in chunks:
                            processed_lines.append(chunk)
                            processed_speakers.append(speaker)
                            processed_voice_entries.append(voice_entry)
                            processed_voice_labels.append(voice_label)
                    else:
                        # Keep as-is
                        processed_lines.append(text)
                        processed_speakers.append(speaker)
                        processed_voice_entries.append(voice_entry)
                        processed_voice_labels.append(voice_label)
                
                # Use processed data
                lines = processed_lines
                speakers = processed_speakers
                voice_entries = processed_voice_entries
                voice_labels = processed_voice_labels

                produced_files = []
                job_quality_scores = []
                job_failed = 0
                job_retried = 0
                
                for i, (text, speaker, voice_entry, voice_label) in enumerate(
                    zip(lines, speakers, voice_entries, voice_labels), start=1
                ):
                    if not self.processing:  # Check if stopped
                        break
                    
                    # Update progress (thread-safe)
                    self._set_current_progress(
                        f"Processing {chapter} - Line {i}/{len(lines)}: '{speaker}' - '{text[:50]}...'"
                    )
                    
                    speaker_dir = self._safe_name(speaker)
                    out_dir = os.path.join(self.output_root, chapter_dir, speaker_dir)
                    os.makedirs(out_dir, exist_ok=True)
                    base = f"line_{i:04d}.wav"
                    out_path = os.path.join(out_dir, base)
                    
                    # Try to synthesize with retries for quality
                    success = False
                    attempts = 0
                    max_attempts = self.cached_max_retries + 1 if self.quality_check_enabled else 1
                    
                    while not success and attempts < max_attempts:
                        attempts += 1
                        
                        try:
                            # Synthesize audio
                            synthesize_text(voice_entry, text, out_path)
                            
                            # Validate quality if enabled
                            if self.quality_check_enabled:
                                validation = quality_checker.validate_audio(out_path, text)
                                quality_score = validation['score']
                                job_quality_scores.append(quality_score)
                                
                                if validation['passed']:
                                    success = True
                                    self.log_debug(
                                        f"[AudioProcessingTab] ✓ Line {i} quality: {quality_score:.1f}/100"
                                    )
                                else:
                                    if attempts < max_attempts:
                                        job_retried += 1
                                        self.retried_lines += 1
                                        self.log_debug(
                                            f"[AudioProcessingTab] ⚠ Line {i} failed quality check "
                                            f"(score: {quality_score:.1f}, issues: {validation['issues']}). "
                                            f"Retrying... (attempt {attempts}/{max_attempts})"
                                        )
                                    else:
                                        # Accept after max retries
                                        success = True
                                        job_failed += 1
                                        self.failed_lines += 1
                                        self.log_debug(
                                            f"[AudioProcessingTab] ✗ Line {i} failed after {attempts} attempts "
                                            f"(score: {quality_score:.1f}). Accepting anyway."
                                        )
                            else:
                                # No quality check - accept
                                success = True
                                job_quality_scores.append(100)
                            
                        except Exception as e:
                            if attempts < max_attempts:
                                self.log_debug(
                                    f"[AudioProcessingTab] Error on line {i}, retrying: {e}"
                                )
                            else:
                                job_failed += 1
                                self.failed_lines += 1
                                success = False  # Failed completely
                                self.log_debug(
                                    f"[AudioProcessingTab] Failed line {i} after {attempts} attempts: {e}"
                                )
                    
                    if success and os.path.exists(out_path):
                        produced_files.append((out_path, i))
                        self.processed_lines += 1
                    
                    self._update_statistics()

                chapters_map.setdefault(chapter_dir, []).extend(produced_files)

                # Calculate average quality for this job
                avg_quality = sum(job_quality_scores) / len(job_quality_scores) if job_quality_scores else 0
                quality_display = f"{avg_quality:.0f}/100"
                
                status_parts = [f"Done ({len(produced_files)}/{len(lines)} files)"]
                if job_failed > 0:
                    status_parts.append(f"{job_failed} failed")
                if job_retried > 0:
                    status_parts.append(f"{job_retried} retried")
                
                job["status"] = ", ".join(status_parts)
                job["quality_score"] = quality_display
                job["files"] = [path for path, _ in produced_files]
                self._update_tree(idx, job)

            except Exception as e:
                job["status"] = f"Error: {e}"
                job["quality_score"] = "N/A"
                self._update_tree(idx, job)
                self.log_debug(f"[AudioProcessingTab] Error processing job: {e}")

        if not self.processing:
            self._set_overall_progress("Stopped by user")
            self.processing = False
            return

        # Merge each chapter into MP3
        self._set_current_progress("Merging chapters into MP3 files...")
        for chapter_dir, wav_files in chapters_map.items():
            wav_files_sorted = [path for path, _ in sorted(wav_files, key=lambda x: x[1])]
            merged_path = os.path.join(self.output_root, f"{chapter_dir}.mp3")
            if self._merge_wavs(wav_files_sorted, merged_path, fmt="mp3"):
                try:
                    AudioSegment.from_file(merged_path, format="mp3")  # validation
                    self.log_debug(f"[AudioProcessingTab] Validated {merged_path}")
                except Exception as e:
                    self.log_debug(f"[AudioProcessingTab] Validation failed: {e}")

        self.merge_all_to_m4b(chapters_map)
        self.processing = False
        self._set_overall_progress("✓ Complete!")
        self._set_current_progress("")
        self.log_debug("[AudioProcessingTab] All selected jobs complete.")
        
        # Show completion message (thread-safe)
        self._show_info(
            "Processing Complete",
            f"Audio processing finished!\n\n"
            f"Total lines: {self.processed_lines}\n"
            f"Failed: {self.failed_lines}\n"
            f"Retried: {self.retried_lines}\n\n"
            f"Output folder: {self.output_root}"
        )

    # ---------------- Helpers ----------------
    def _split_long_text(self, text: str, max_chars: int = 250) -> list:
        """
        Split long text into chunks at sentence boundaries with expression awareness.
        Tries to keep chunks under max_chars while respecting sentence boundaries and
        preserving emotional/expressive punctuation context.
        
        Args:
            text: The text to split
            max_chars: Maximum characters per chunk (default 250 for XTTS limit)
            
        Returns:
            List of text chunks with continuation markers where needed
        """
        if len(text) <= max_chars:
            return [text]
        
        # Split into sentences (handles . ! ? followed by space or end)
        import re
        sentences = re.split(r'([.!?]+[\s"])', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # Get the punctuation if it exists
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
            full_sentence = sentence + punctuation
            
            # If adding this sentence would exceed max_chars
            if len(current_chunk) + len(full_sentence) > max_chars:
                if current_chunk:
                    # Save current chunk and start new one
                    chunks.append(current_chunk.strip())
                    current_chunk = full_sentence
                else:
                    # Single sentence is too long - split with expression awareness
                    chunks.extend(self._split_long_sentence_smart(full_sentence, max_chars))
                    current_chunk = ""
            else:
                current_chunk += full_sentence
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def _split_long_sentence_smart(self, sentence: str, max_chars: int) -> list:
        """
        Split a long sentence at natural pause points (commas, semicolons, em-dashes)
        while preserving expression. Falls back to word boundaries if needed.
        """
        import re
        
        # Try splitting at natural pause points first: commas, semicolons, em-dashes, colons
        pause_pattern = r'([,;:—])\s+'
        parts = re.split(pause_pattern, sentence)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(parts)):
            part = parts[i]
            
            # Check if adding this part would exceed limit
            if len(current_chunk) + len(part) > max_chars:
                if current_chunk:
                    # Determine if we should add continuation marker
                    ends_with_punctuation = current_chunk.rstrip().endswith((',', ';', ':'))
                    
                    # For commas/semicolons/colons, keep them as they are natural pauses
                    # No need for ellipsis since the pause is already there
                    chunks.append(current_chunk.strip())
                    
                    # Start next chunk
                    current_chunk = part
                else:
                    # Part itself is too long - split at word boundaries as last resort
                    words = part.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > max_chars - 3:  # Reserve space for ...
                            if temp_chunk:
                                # Add ellipsis only if not ending with natural pause
                                if not temp_chunk.rstrip().endswith((',', ';', ':', '—', '...')):
                                    chunks.append(temp_chunk.strip() + '...')
                                else:
                                    chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                # Single word too long - just take it
                                chunks.append(word)
                        else:
                            temp_chunk += (" " if temp_chunk else "") + word
                    if temp_chunk:
                        current_chunk = temp_chunk
            else:
                current_chunk += part
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [sentence]
    
    def _update_tree(self, idx: int, job: Dict[str, Any]):
        """Thread-safe tree update - schedules UI update on main thread"""
        self.after(0, lambda: self._update_tree_ui(idx, job))
    
    def _update_tree_ui(self, idx: int, job: Dict[str, Any]):
        """Actual tree update - must run on main thread"""
        try:
            row_id = self.tree.get_children()[idx]
        except IndexError:
            return
        speakers = job.get("speakers", ["Unknown"])
        voice_labels = job.get("voice_labels", [job.get("voice_label", "")])
        speaker_display = ", ".join(set(speakers))
        voice_display = ", ".join(set(voice_labels))
        chapter = job.get("chapter", "Chapter_Unknown")
        # Use cached checkbox state (thread-safe) instead of accessing tkinter variable
        is_checked = self.checkbox_states.get(idx, False)
        self.tree.item(
            row_id,
            values=(
                "[X]" if is_checked else "[ ]",
                chapter,
                speaker_display,
                voice_display,
                len(job.get("lines", [])),
                job.get("status", ""),
                job.get("quality_score", "-"),
            ),
        )

    def _safe_name(self, name: str) -> str:
        name = name.strip() or "untitled"
        name = re.sub(r"[^\w\-\. ]+", "_", name)
        name = re.sub(r"\s+", "_", name)
        return name[:80]

    def _merge_wavs(self, wav_files, out_path, fmt="mp3"):
        if not wav_files:
            self.log_debug(f"[AudioProcessingTab] No WAV files to merge for {out_path}")
            return False
        try:
            combined = AudioSegment.empty()
            for wf in wav_files:
                audio = AudioSegment.from_wav(wf)
                combined += audio
            combined.export(out_path, format=fmt, codec="libmp3lame", bitrate="192k")
            self.log_debug(f"[AudioProcessingTab] Exported MP3 → {out_path}")
            return True
        except Exception as e:
            self.log_debug(f"[AudioProcessingTab] Failed to merge: {e}")
            return False

    # ---------------- Output folder mgmt ----------------
    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_root = folder
            self.output_label.configure(text=f"Output: {self.output_root}")
            self.log_debug(f"[AudioProcessingTab] Output folder set → {self.output_root}")

    def open_output_folder(self):
        if not os.path.exists(self.output_root):
            messagebox.showwarning("Warning", "Output folder does not exist yet.")
            return
        try:
            if sys.platform.startswith("darwin"):
                subprocess.call(["open", self.output_root])
            elif os.name == "nt":
                os.startfile(self.output_root)
            elif os.name == "posix":
                subprocess.call(["xdg-open", self.output_root])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    # ---------------- Final merge to m4b ----------------
    def merge_all_to_m4b(self, chapters_map=None):
        try:
            if chapters_map is None:
                # Rebuild from finished jobs if called from button
                chapters_map = {}
                for job in self.jobs:
                    if "files" in job and job["status"].startswith("Done"):
                        chapter = self._safe_name(job.get("chapter", "Chapter_Unknown"))
                        wav_files = [(f, i + 1) for i, f in enumerate(job["files"])]
                        chapters_map.setdefault(chapter, []).extend(wav_files)

            combined = AudioSegment.empty()
            chapter_files = []
            for chapter_dir in sorted(chapters_map.keys()):
                mp3_path = os.path.join(self.output_root, f"{chapter_dir}.mp3")
                if os.path.exists(mp3_path):
                    audio = AudioSegment.from_file(mp3_path, format="mp3")
                    combined += audio
                    chapter_files.append(mp3_path)
                    self.log_debug(f"[AudioProcessingTab] Added {mp3_path}")

            out_file_name = list(chapters_map.keys())[0] if chapters_map else "Audiobook_Unknown"
            out_file = os.path.join(self.output_root, f"{out_file_name}.m4b")
            combined.export(out_file, format="ipod", codec="aac", bitrate="192k")
            self.log_debug(f"[AudioProcessingTab] Exported M4B → {out_file}")
            self._show_info("Merge Complete", f"Exported audiobook: {out_file}")
        except Exception as e:
            self.log_debug(f"[AudioProcessingTab] Merge failed: {e}")
            self._show_error("Error", f"Merge failed: {e}")
