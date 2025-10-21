import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import customtkinter as ctk
import random
import os

from app.core import character_detection


# -----------------------------
# Tooltip helper
# -----------------------------
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            wraplength=600
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class CharactersTab(ctk.CTkFrame):
    def __init__(self, master, get_book_text, log_debug=None, gpu_enabled=True):
        super().__init__(master)
        self.get_book_text = get_book_text
        self.log_debug = log_debug or (lambda msg: print(msg))
        self.gpu_enabled = gpu_enabled

        self.chapters = []  # list of {"title": str, "text": str, "results": []}
        self.locked_lines = set()
        self.character_colors = {}
        self.line_vars = []
        self._text_labels = []  # Store references to text labels for dynamic resizing

        self.narrator_color = "#555555"
        
        # Search and filter state
        self.search_var = tk.StringVar()
        self.filter_character_var = tk.StringVar(value="All Characters")
        
        self.build_layout()

    # ---------- Book text setter ----------
    def set_book_text(self, chapters):
        self.chapters = chapters
        self.log_debug(
            f"[CharactersTab] Received {len(self.chapters)} chapter(s): "
            f"{[c['title'] for c in self.chapters]}"
        )

    # ---------- UI Layout ----------
    def build_layout(self):
        # Store references to left and right panels for resize handling
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.pack(side="left", fill="both", padx=10, pady=10)

        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Track window size to detect fullscreen/maximize
        self.bind("<Configure>", self._on_window_resize)
        self._last_width = 0
        
        left = self.left_panel
        right = self.right_panel

        # Make character list scrollable
        char_list_frame = tk.Frame(left)
        char_list_frame.pack(side="top", fill="both", expand=True)
        
        char_scrollbar = tk.Scrollbar(char_list_frame, orient="vertical")
        self.char_list = tk.Listbox(
            char_list_frame, 
            selectmode="extended", 
            width=30, 
            exportselection=False,
            yscrollcommand=char_scrollbar.set,
            font=("Arial", 11)  # Slightly larger font
        )
        char_scrollbar.config(command=self.char_list.yview)
        char_scrollbar.pack(side="right", fill="y")
        self.char_list.pack(side="left", fill="both", expand=True)

        # Character-centric operations
        char_frame = ctk.CTkFrame(left, border_width=2, border_color="gray")
        char_frame.pack(pady=10, padx=5, fill="x")
        ctk.CTkLabel(char_frame, text="Character Operations", font=("Arial", 12, "bold")).pack(pady=5)
        
        ctk.CTkButton(char_frame, text="Add Character", command=self.add_character).pack(pady=5)
        self.detect_button = ctk.CTkButton(
            char_frame, text="Detect Characters", command=self.detect_characters,
            fg_color="green", hover_color="darkgreen"
        )
        self.detect_button.pack(pady=5)
        self.progress_bar = ctk.CTkProgressBar(char_frame, width=200)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(char_frame, text="Ready")
        self.progress_label.pack(pady=5)

        ctk.CTkButton(char_frame, text="Delete Selected", command=self.delete_selected,
                      fg_color="red", hover_color="darkred").pack(pady=5)
        ctk.CTkButton(char_frame, text="Merge Selected", command=self.merge_selected).pack(pady=5)
        ctk.CTkButton(char_frame, text="Rename Character", command=self.rename_character).pack(pady=5)

        # Line-centric operations
        line_frame = ctk.CTkFrame(left, border_width=2, border_color="gray")
        line_frame.pack(pady=10, padx=5, fill="x")
        ctk.CTkLabel(line_frame, text="Line Operations", font=("Arial", 12, "bold")).pack(pady=5)
        
        ctk.CTkButton(line_frame, text="Reassign Selected Lines", command=self.reassign_selected_lines).pack(pady=5)
        ctk.CTkButton(line_frame, text="Split Selected Line", command=self.split_selected_line).pack(pady=5)
        ctk.CTkButton(line_frame, text="Merge Selected Lines", command=self.merge_selected_lines).pack(pady=5)
        ctk.CTkButton(line_frame, text="Delete Selected Lines", command=self.delete_selected_lines,
                      fg_color="red", hover_color="darkred").pack(pady=5)
        
        ctk.CTkButton(left, text="Send to Voices", command=self.send_to_voices).pack(pady=15)

        # Search and Filter Bar (at top of right panel)
        search_filter_frame = ctk.CTkFrame(right, border_width=2, border_color="gray")
        search_filter_frame.pack(side="top", fill="x", padx=5, pady=5)
        
        # Search box
        search_label = ctk.CTkLabel(search_filter_frame, text="Search Text:", font=("Arial", 13))
        search_label.pack(side="left", padx=5, pady=5)
        
        self.search_entry = ctk.CTkEntry(search_filter_frame, textvariable=self.search_var, width=250, placeholder_text="Type to search in dialogue lines...")
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.search_entry.bind("<Return>", lambda e: self.do_search())
        self.search_entry.bind("<KP_Enter>", lambda e: self.do_search())
        
        search_btn = ctk.CTkButton(search_filter_frame, text="Search", command=self.do_search, width=70)
        search_btn.pack(side="left", padx=2, pady=5)
        
        clear_search_btn = ctk.CTkButton(search_filter_frame, text="Clear", command=self.clear_search, width=60)
        clear_search_btn.pack(side="left", padx=2, pady=5)
        
        # Character filter dropdown
        filter_label = ctk.CTkLabel(search_filter_frame, text="Filter by Character:", font=("Arial", 13))
        filter_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.filter_dropdown = ctk.CTkComboBox(
            search_filter_frame,
            variable=self.filter_character_var,
            values=["All Characters"],
            width=200,
            command=self.on_filter_changed
        )
        self.filter_dropdown.pack(side="left", padx=5, pady=5)

        # Canvas and scrollbar
        self.canvas = tk.Canvas(right)
        self.scrollbar = tk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Create window and store the window ID for later updates
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind canvas resize to update scroll frame width
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

        self.placeholder_label = tk.Label(
            self.scroll_frame,
            text="No characters detected yet.\nClick 'Detect Characters' to begin.",
            fg="gray",
            wraplength=700,
            justify="center",
        )
        self.placeholder_label.pack(pady=20)

    # ---------- Window Resize Handler ----------
    def _on_window_resize(self, event):
        """Adjust panel proportions when window is resized (e.g., fullscreen)"""
        # Only respond to width changes on the main frame
        if event.widget != self:
            return
            
        new_width = event.width
        
        # Detect significant width increase (like going fullscreen)
        # Threshold: if width increased by more than 300px, likely maximized/fullscreened
        if self._last_width > 0 and new_width > self._last_width + 300:
            # Expand left panel when going fullscreen
            self.left_panel.pack_configure(expand=True)
        elif self._last_width > 0 and new_width < self._last_width - 300:
            # Restore left panel when returning from fullscreen
            self.left_panel.pack_configure(expand=False)
        
        self._last_width = new_width
    
    def _on_canvas_resize(self, event):
        """Update scroll frame width to match canvas width when canvas is resized"""
        # Set the scroll frame width to match canvas width (minus scrollbar)
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        # Update wraplength for all text labels
        if hasattr(self, '_text_labels') and self._text_labels:
            dynamic_wraplength = max(400, canvas_width - 250)
            for label in self._text_labels:
                if label.winfo_exists():
                    label.config(wraplength=dynamic_wraplength)

    # ---------- Mousewheel ----------
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    # ---------- Character Management ----------
    def add_character(self):
        name = simpledialog.askstring("Add Character", "Enter character name:")
        if not name:
            return
        if name in self.get_current_characters():
            messagebox.showinfo("Info", f"{name} already exists.")
            return
        color = self._get_color(name)
        self.character_colors[name] = color
        self.char_list.insert(tk.END, name)
        self.char_list.itemconfig(tk.END, fg=color)
        self.log_debug(f"[CharactersTab] Added character '{name}' with color {color}")

    def delete_selected(self):
        selection = self.char_list.curselection()
        if not selection:
            messagebox.showinfo("Info", "No character selected.")
            return
        for idx in reversed(selection):
            name = self.char_list.get(idx)
            self.char_list.delete(idx)
            self.character_colors.pop(name, None)
            for chapter in self.chapters:
                if isinstance(chapter.get("results"), list):
                    for r in chapter["results"]:
                        if isinstance(r, dict) and r.get("speaker") == name:
                            r["speaker"] = "Unknown"
        self.show_lines()

    def merge_selected(self):
        selection = self.char_list.curselection()
        if len(selection) < 2:
            messagebox.showinfo("Info", "Select 2 or more characters to merge.")
            return
        names = [self.char_list.get(idx) for idx in selection]

        # Dropdown to pick survivor
        survivor = self._prompt_survivor_dropdown(names)
        if not survivor:
            return

        # Update chapters
        updated_count = 0
        for chapter in self.chapters:
            if isinstance(chapter.get("results"), list):
                for r in chapter["results"]:
                    if isinstance(r, dict) and r.get("speaker") in names:
                        old_speaker = r["speaker"]
                        r["speaker"] = survivor
                        updated_count += 1
                        self.log_debug(f"  Updated line: '{old_speaker}' -> '{survivor}': {r.get('text', '')[:50]}")
        
        self.log_debug(f"[CharactersTab] Updated {updated_count} lines from {names} to '{survivor}'")

        # Remove merged characters (except survivor) from listbox
        for name in names:
            if name != survivor:
                idxs = [i for i in range(self.char_list.size()) if self.char_list.get(i) == name]
                for idx in reversed(idxs):
                    self.char_list.delete(idx)
                self.character_colors.pop(name, None)

        # Ensure survivor keeps/gets a color
        if survivor not in self.character_colors:
            self.character_colors[survivor] = self._get_color(survivor)

        self._refresh_char_list()
        self.show_lines()

        # Debug/log message
        merged = [n for n in names if n != survivor]
        self.log_debug(f"[CharactersTab] Merged {merged} into '{survivor}'")

    def rename_character(self):
        """Rename a single character across all lines."""
        selection = self.char_list.curselection()
        if len(selection) != 1:
            messagebox.showinfo("Info", "Select exactly one character to rename.")
            return
        
        old_name = self.char_list.get(selection[0])
        
        # Prompt for new name
        new_name = simpledialog.askstring("Rename Character", f"Rename '{old_name}' to:", initialvalue=old_name)
        if not new_name or new_name.strip() == "":
            return
        
        new_name = new_name.strip()
        
        # Don't rename if the name didn't change
        if new_name == old_name:
            return
        
        # Update all occurrences in chapters
        updated_count = 0
        for chapter in self.chapters:
            if isinstance(chapter.get("results"), list):
                for r in chapter["results"]:
                    if isinstance(r, dict) and r.get("speaker") == old_name:
                        r["speaker"] = new_name
                        updated_count += 1
        
        # Update character colors dictionary
        if old_name in self.character_colors:
            self.character_colors[new_name] = self.character_colors.pop(old_name)
        
        # Refresh display
        self._refresh_char_list()
        self.show_lines()
        
        self.log_debug(f"[CharactersTab] Renamed '{old_name}' to '{new_name}' ({updated_count} lines updated)")
        messagebox.showinfo("Success", f"Renamed '{old_name}' to '{new_name}'\n{updated_count} lines updated.")

    def _prompt_survivor_dropdown(self, names):
        win = tk.Toplevel(self)
        win.title("Merge Characters")
        tk.Label(win, text="Select the surviving character:").pack(pady=5)

        survivor_var = tk.StringVar(value=names[0])
        dropdown = ttk.Combobox(win, textvariable=survivor_var, values=names, state="readonly")
        dropdown.pack(pady=5)

        survivor = {"value": None}

        def confirm():
            survivor["value"] = survivor_var.get()
            win.destroy()

        tk.Button(win, text="OK", command=confirm).pack(pady=5)

        win.transient(self)
        win.wait_visibility()   # ? ensures window is mapped before grab
        win.grab_set()
        self.wait_window(win)
        return survivor["value"]

    def reassign_selected_lines(self):
        selection = self.char_list.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a character to reassign lines to.")
            return
        new_speaker = self.char_list.get(selection[0])
        
        # Debug: check line_vars state
        self.log_debug(f"[CharactersTab] Total line_vars: {len(self.line_vars)}")
        selected_count = sum(1 for var, result in self.line_vars if var.get() == 1)
        self.log_debug(f"[CharactersTab] Selected checkboxes: {selected_count}")
        
        reassigned = 0
        for var, result in self.line_vars:
            if var.get() == 1 and isinstance(result, dict):
                result["speaker"] = new_speaker
                reassigned += 1
        self.log_debug(f"[CharactersTab] Reassigned {reassigned} lines to {new_speaker}")
        self.show_lines()

    def split_selected_line(self):
        """Split a selected line into multiple lines at user-specified positions."""
        # Debug: check line_vars state
        self.log_debug(f"[CharactersTab] Total line_vars: {len(self.line_vars)}")
        selected_count = sum(1 for var, result in self.line_vars if var.get() == 1)
        self.log_debug(f"[CharactersTab] Selected checkboxes: {selected_count}")
        
        # Find selected lines
        selected = [(var, result) for var, result in self.line_vars if var.get() == 1]
        
        if len(selected) == 0:
            messagebox.showinfo("Info", "Please select a line to split.")
            return
        
        if len(selected) > 1:
            messagebox.showinfo("Info", "Please select only ONE line to split.")
            return
        
        var, result = selected[0]
        original_text = result.get("text", "").strip()
        original_speaker = result.get("speaker", "Unknown")
        
        if not original_text:
            messagebox.showinfo("Info", "Selected line has no text.")
            return
        
        # Create split dialog
        self._show_split_dialog(result, original_text, original_speaker)

    def _show_split_dialog(self, result, original_text, original_speaker):
        """Show dialog for splitting a line."""
        win = tk.Toplevel(self)
        win.title("Split Line")
        win.geometry("700x500")
        
        # Instructions
        tk.Label(
            win, 
            text=f"Original Speaker: {original_speaker}\n\n"
                 "Position cursor where you want to split and press ENTER.\n"
                 "You can split multiple times. Click 'Done' when finished.",
            justify="left",
            wraplength=650
        ).pack(pady=10, padx=10)
        
        # Text widget for editing
        text_frame = tk.Frame(win)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_scrollbar = tk.Scrollbar(text_frame)
        text_scrollbar.pack(side="right", fill="y")
        
        text_widget = tk.Text(
            text_frame, 
            wrap="word", 
            height=15,
            yscrollcommand=text_scrollbar.set
        )
        text_widget.pack(side="left", fill="both", expand=True)
        text_scrollbar.config(command=text_widget.yview)
        
        text_widget.insert("1.0", original_text)
        text_widget.focus_set()
        
        # Track split positions
        split_marker = "\n⮕ SPLIT HERE ⮕\n"
        
        def insert_split_marker(event):
            """Insert split marker at cursor position."""
            text_widget.insert("insert", split_marker)
            return "break"  # Prevent default Enter behavior
        
        text_widget.bind("<Return>", insert_split_marker)
        text_widget.bind("<KP_Enter>", insert_split_marker)  # Numpad Enter
        
        # Buttons
        button_frame = tk.Frame(win)
        button_frame.pack(pady=10)
        
        def do_split():
            """Process the split and create new lines."""
            content = text_widget.get("1.0", "end-1c")
            
            # Split by marker
            segments = [s.strip() for s in content.split(split_marker) if s.strip()]
            
            if len(segments) <= 1:
                messagebox.showinfo("Info", "No split markers found. Use ENTER to add splits.")
                return
            
            # Find the original result in chapters and replace it
            found = False
            for chapter in self.chapters:
                if isinstance(chapter.get("results"), list):
                    for idx, r in enumerate(chapter["results"]):
                        if r is result:  # Same object reference
                            # Create new results for each segment
                            new_results = []
                            for segment in segments:
                                new_result = {
                                    "speaker": original_speaker,
                                    "text": segment,
                                    "is_quote": result.get("is_quote", False),
                                    "quote_type": result.get("quote_type", ""),
                                    "_split_from_line": True
                                }
                                new_results.append(new_result)
                            
                            # Replace original with split results
                            chapter["results"][idx:idx+1] = new_results
                            found = True
                            self.log_debug(
                                f"[CharactersTab] Split line from '{original_speaker}' "
                                f"into {len(segments)} segments"
                            )
                            break
                
                if found:
                    break
            
            if not found:
                messagebox.showerror("Error", "Could not find original line to split.")
                return
            
            # Refresh display
            self.show_lines()
            win.destroy()
            messagebox.showinfo(
                "Success", 
                f"Line split into {len(segments)} segments.\n"
                f"All segments assigned to '{original_speaker}'.\n"
                f"You can now reassign individual segments to other characters."
            )
        
        def cancel():
            win.destroy()
        
        tk.Button(button_frame, text="Done - Apply Split", command=do_split, width=20).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel, width=15).pack(side="left", padx=5)
        
        win.transient(self)
        win.wait_visibility()
        win.grab_set()

    def merge_selected_lines(self):
        """Merge multiple selected lines into one line with editable text."""
        # Debug: check line_vars state
        self.log_debug(f"[CharactersTab] Total line_vars: {len(self.line_vars)}")
        selected_count = sum(1 for var, result in self.line_vars if var.get() == 1)
        self.log_debug(f"[CharactersTab] Selected checkboxes: {selected_count}")
        
        # Find selected lines
        selected = [(var, result) for var, result in self.line_vars if var.get() == 1]
        
        if len(selected) < 2:
            messagebox.showinfo("Info", "Please select at least TWO lines to merge.")
            return
        
        # Collect text and speakers from selected lines
        texts = []
        speakers = []
        results_to_merge = []
        
        for var, result in selected:
            text = result.get("text", "").strip()
            speaker = result.get("speaker", "Unknown")
            texts.append(text)
            speakers.append(speaker)
            results_to_merge.append(result)
        
        # Check if all speakers are the same
        unique_speakers = set(speakers)
        if len(unique_speakers) == 1:
            default_speaker = speakers[0]
        else:
            default_speaker = speakers[0]  # Use first speaker as default
        
        # Merge texts with line breaks
        merged_text = "\n".join(texts)
        
        # Show merge dialog
        self._show_merge_dialog(results_to_merge, merged_text, default_speaker, unique_speakers)

    def _show_merge_dialog(self, results_to_merge, merged_text, default_speaker, unique_speakers):
        """Show dialog for editing merged text."""
        win = tk.Toplevel(self)
        win.title("Merge Lines")
        win.geometry("700x500")
        
        # Instructions
        info_text = f"Merging {len(results_to_merge)} lines"
        if len(unique_speakers) > 1:
            info_text += f"\n⚠️ Warning: Lines have different speakers: {', '.join(sorted(unique_speakers))}"
        info_text += f"\n\nDefault Speaker: {default_speaker}\n\nEdit the merged text as needed, then click 'Save'."
        
        tk.Label(
            win, 
            text=info_text,
            justify="left",
            wraplength=650,
            fg="red" if len(unique_speakers) > 1 else "black"
        ).pack(pady=10, padx=10)
        
        # Speaker selection
        speaker_frame = tk.Frame(win)
        speaker_frame.pack(pady=5, padx=10, fill="x")
        
        tk.Label(speaker_frame, text="Assign to Speaker:").pack(side="left", padx=5)
        
        speaker_var = tk.StringVar(value=default_speaker)
        speaker_dropdown = ctk.CTkComboBox(
            speaker_frame,
            variable=speaker_var,
            values=self.get_characters(),
            width=200
        )
        speaker_dropdown.pack(side="left", padx=5)
        
        # Text widget for editing
        text_frame = tk.Frame(win)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_scrollbar = tk.Scrollbar(text_frame)
        text_scrollbar.pack(side="right", fill="y")
        
        text_widget = tk.Text(
            text_frame, 
            wrap="word", 
            height=15,
            yscrollcommand=text_scrollbar.set
        )
        text_widget.pack(side="left", fill="both", expand=True)
        text_scrollbar.config(command=text_widget.yview)
        
        text_widget.insert("1.0", merged_text)
        text_widget.focus_set()
        
        # Buttons
        button_frame = tk.Frame(win)
        button_frame.pack(pady=10)
        
        def save_merge():
            """Save the merged line and remove originals."""
            final_text = text_widget.get("1.0", "end-1c").strip()
            final_speaker = speaker_var.get()
            
            if not final_text:
                messagebox.showwarning("Warning", "Merged text cannot be empty.")
                return
            
            # Find and replace in chapters
            found = False
            first_result = results_to_merge[0]
            
            for chapter in self.chapters:
                if isinstance(chapter.get("results"), list):
                    # Find index of first result to merge
                    try:
                        first_idx = chapter["results"].index(first_result)
                        
                        # Create merged result
                        merged_result = {
                            "speaker": final_speaker,
                            "text": final_text,
                            "is_quote": first_result.get("is_quote", False),
                            "quote_type": first_result.get("quote_type", ""),
                            "_merged_from": len(results_to_merge)
                        }
                        
                        # Remove all results to merge and insert merged result
                        # We need to find indices of all results
                        indices_to_remove = []
                        for result in results_to_merge:
                            try:
                                idx = chapter["results"].index(result)
                                indices_to_remove.append(idx)
                            except ValueError:
                                continue
                        
                        if indices_to_remove:
                            # Sort in reverse to remove from end first (preserves indices)
                            indices_to_remove.sort(reverse=True)
                            min_idx = min(indices_to_remove)
                            
                            # Remove all
                            for idx in indices_to_remove:
                                del chapter["results"][idx]
                            
                            # Insert merged at position of first removed
                            chapter["results"].insert(min_idx, merged_result)
                            
                            found = True
                            self.log_debug(
                                f"[CharactersTab] Merged {len(results_to_merge)} lines "
                                f"into one line for '{final_speaker}'"
                            )
                            break
                    except ValueError:
                        continue
            
            if not found:
                messagebox.showerror("Error", "Could not find lines to merge.")
                return
            
            # Refresh display
            self.show_lines()
            win.destroy()
            messagebox.showinfo(
                "Success", 
                f"Merged {len(results_to_merge)} lines into one.\n"
                f"Assigned to '{final_speaker}'."
            )
        
        def cancel():
            win.destroy()
        
        tk.Button(button_frame, text="Save Merged Line", command=save_merge, width=20, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel, width=15).pack(side="left", padx=5)
        
        win.transient(self)
        win.wait_visibility()
        win.grab_set()

    def delete_selected_lines(self):
        """Delete selected lines after confirmation."""
        # Find selected lines
        selected = [(var, result) for var, result in self.line_vars if var.get() == 1]
        
        if len(selected) == 0:
            messagebox.showinfo("Info", "Please select line(s) to delete.")
            return
        
        # Show confirmation dialog
        line_count = len(selected)
        if line_count == 1:
            confirmation_msg = "Are you sure you want to delete the selected line?\n\nThis action cannot be undone."
        else:
            confirmation_msg = f"Are you sure you want to delete {line_count} selected lines?\n\nThis action cannot be undone."
        
        response = messagebox.askyesno("Confirm Deletion", confirmation_msg, icon='warning')
        
        if not response:
            return
        
        # Delete the selected lines from chapters
        deleted_count = 0
        results_to_delete = [result for var, result in selected]
        
        for chapter in self.chapters:
            if isinstance(chapter.get("results"), list):
                original_count = len(chapter["results"])
                # Filter out the selected results
                chapter["results"] = [
                    r for r in chapter["results"] 
                    if r not in results_to_delete
                ]
                deleted_count += original_count - len(chapter["results"])
        
        self.log_debug(f"[CharactersTab] Deleted {deleted_count} line(s)")
        
        # Refresh display
        self.show_lines()
        
        # Show success message
        if deleted_count > 0:
            messagebox.showinfo("Success", f"Successfully deleted {deleted_count} line(s).")

    def send_to_voices(self):
        chars = self.get_characters()
        if not chars:
            messagebox.showinfo("Info", "No characters to send.")
            return

        app = self.master.master
        if hasattr(app, "voices_tab") and app.voices_tab:
            app.voices_tab.set_characters(chars)
            messagebox.showinfo("Info", "Characters sent to Voices tab.")
            self.log_debug("[CharactersTab] Sent characters to Voices tab.")
    
    # ---------- Search and Filter ----------
    def do_search(self):
        """Execute the search with the current search box text."""
        search_text = self.search_entry.get().strip()
        self.search_var.set(search_text)
        self.log_debug(f"[CharactersTab] Search initiated: '{search_text}'")
        self.apply_filters()
    
    def clear_search(self):
        """Clear the search box."""
        self.search_var.set("")
        self.search_entry.delete(0, tk.END)
        self.apply_filters()  # Refresh display after clearing
    
    def on_filter_changed(self, choice):
        """Handle filter dropdown selection change."""
        self.filter_character_var.set(choice)
        self.log_debug(f"[CharactersTab] Filter changed to: '{choice}'")
        self.apply_filters()
    
    def apply_filters(self):
        """Apply both search and character filter to the displayed lines."""
        search_text = self.search_var.get()
        filter_char = self.filter_character_var.get()
        self.log_debug(f"[CharactersTab] Applying filters - Search: '{search_text}', Character: '{filter_char}'")
        self.show_lines()
    
    def update_filter_dropdown(self):
        """Update the character filter dropdown with current characters."""
        chars = self.get_characters()
        filter_values = ["All Characters"] + chars
        self.filter_dropdown.configure(values=filter_values)
        self.log_debug(f"[CharactersTab] Updated filter dropdown with {len(chars)} characters")

    # ---------- Detection ----------
    def detect_characters(self):
        if not self.chapters:
            messagebox.showerror("Error", "No chapters selected. Please select chapters in Book Processing tab.")
            return

        self.detect_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Processing...")
        self.update_idletasks()

        total_chapters = len(self.chapters)
        for i, chapter in enumerate(self.chapters):
            text = chapter.get("text", "")
            results = character_detection.run_attribution(text)

            chapter["results"] = results or []
            self.log_debug(f"[CharactersTab] Loaded {len(chapter['results'])} lines for chapter {chapter['title']}")

            progress = (i + 1) / total_chapters
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f"Processing chapter {i+1}/{total_chapters}")
            self.update_idletasks()

        self.detect_button.configure(state="normal")
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="Completed")
        self._refresh_char_list()
        self.show_lines()

    # ---------- Show Lines ----------
    def show_lines(self):
        # Clear stored text label references
        self._text_labels = []
        
        for widget in self.scroll_frame.winfo_children():
            if widget is not self.placeholder_label:
                widget.destroy()

        self.placeholder_label.pack_forget()

        all_results = []
        for chapter in self.chapters:
            if isinstance(chapter.get("results"), list):
                for r in chapter["results"]:
                    if isinstance(r, dict):
                        all_results.append(r)

        if not all_results:
            self.placeholder_label.pack(pady=20)
            return

        # Apply filters
        search_text = self.search_var.get().lower().strip()
        filter_character = self.filter_character_var.get()
        
        self.log_debug(f"[CharactersTab] show_lines: Total lines={len(all_results)}, Search='{search_text}', Filter='{filter_character}'")
        
        filtered_results = []
        for result in all_results:
            speaker = result.get("speaker", "Unknown")
            text = result.get("text", "").strip()
            
            # Apply character filter
            if filter_character != "All Characters" and speaker != filter_character:
                continue
            
            # Apply search filter
            if search_text and search_text not in text.lower():
                continue
            
            filtered_results.append(result)
        
        self.log_debug(f"[CharactersTab] show_lines: Filtered down to {len(filtered_results)} lines")
        
        # Show message if no results after filtering
        if not filtered_results:
            no_results_msg = "No lines found"
            if search_text and filter_character != "All Characters":
                no_results_msg = f"No lines found for '{filter_character}' matching '{search_text}'"
            elif search_text:
                no_results_msg = f"No lines found matching '{search_text}'"
            elif filter_character != "All Characters":
                no_results_msg = f"No lines found for '{filter_character}'"
            
            no_results_label = tk.Label(
                self.scroll_frame,
                text=no_results_msg,
                fg="gray",
                font=("Arial", 12),
                wraplength=700,
                justify="center",
            )
            no_results_label.pack(pady=20)
            return

        self.line_vars = []
        for idx, result in enumerate(filtered_results):
            # Add visual distinction for quote vs non-quote rows
            is_quote = result.get("is_quote", False)
            bg_color = "#ffffff" if is_quote else "#f0f0f0"  # white for quotes, light gray for narrator
            
            frame = tk.Frame(self.scroll_frame, bg=bg_color, relief="solid", borderwidth=1)
            frame.pack(fill="x", pady=1)

            var = tk.IntVar(master=frame, value=0)
            chk = tk.Checkbutton(frame, variable=var, bg=bg_color)
            chk.pack(side="left", padx=5)
            self.line_vars.append((var, result))

            speaker = result.get("speaker", "Unknown")
            color = self._get_color(speaker)
            spk_label = tk.Label(frame, text=speaker, fg=color, width=15, anchor="w", bg=bg_color, font=("Arial", 11))
            spk_label.pack(side="left", padx=5)

            text = result.get("text", "").strip()
            
            # Show full text if searching (don't truncate), otherwise show preview
            if search_text:
                display_text = text  # Show full text when searching
            else:
                display_text = text[:100] + "..." if len(text) > 100 else text
            
            # Calculate dynamic wraplength based on canvas width (subtract space for checkbox + speaker label + padding)
            canvas_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 800
            dynamic_wraplength = max(400, canvas_width - 250)  # Reserve 250px for checkbox and speaker label
            
            # Use Text widget if highlighting is needed, otherwise use Label
            if search_text:
                # Create a read-only Text widget for highlighting
                txt_widget = tk.Text(
                    frame, 
                    wrap="word",
                    width=1,  # Will be controlled by pack
                    bg=bg_color, 
                    font=("Arial", 11), 
                    fg="#000000",
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=0,
                    cursor="arrow",
                    padx=2,
                    pady=2
                )
                txt_widget.insert("1.0", display_text)
                
                # Configure tag for highlighting
                txt_widget.tag_configure("highlight", background="#FFFF00", foreground="#000000")
                
                # Find and highlight all occurrences of search text (case-insensitive)
                txt_widget.configure(state="normal")
                start_idx = "1.0"
                while True:
                    start_idx = txt_widget.search(search_text, start_idx, nocase=True, stopindex="end")
                    if not start_idx:
                        break
                    end_idx = f"{start_idx}+{len(search_text)}c"
                    txt_widget.tag_add("highlight", start_idx, end_idx)
                    start_idx = end_idx
                
                txt_widget.configure(state="disabled")  # Make read-only
                
                # Calculate height based on content
                num_lines = int(txt_widget.index('end-1c').split('.')[0])
                txt_widget.configure(height=min(num_lines, 10))  # Max 10 lines visible
                
                txt_widget.pack(side="left", fill="both", expand=True, padx=2, pady=2)
                self._text_labels.append(txt_widget)
                
                # Tooltip
                ToolTip(txt_widget, text)
            else:
                # Use regular Label when not searching
                txt_label = tk.Label(frame, text=display_text, wraplength=dynamic_wraplength, anchor="w", justify="left", bg=bg_color, font=("Arial", 11), fg="#000000")
                txt_label.pack(side="left", fill="x", expand=True)
                self._text_labels.append(txt_label)
                
                # Tooltip - always show full text in tooltip
                ToolTip(txt_label, text)

        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ---------- Character List ----------
    def _refresh_char_list(self):
        self.char_list.delete(0, tk.END)
        all_results = []
        for chapter in self.chapters:
            for r in chapter.get("results", []):
                if isinstance(r, dict):
                    all_results.append(r)

        speakers = sorted(
            set(r.get("speaker", "Unknown") for r in all_results),
            key=lambda s: (s != "Narrator", s),
        )
        for spk in speakers:
            color = self._get_color(spk)
            self.char_list.insert(tk.END, spk)
            self.char_list.itemconfig(tk.END, fg=color)
        
        # Update filter dropdown
        self.update_filter_dropdown()

    def _get_color(self, name):
        if name == "Narrator":
            return self.narrator_color
        if name not in self.character_colors:
            # Generate darker colors only (each RGB component 0-180, avoiding light colors)
            r = random.randint(0, 180)
            g = random.randint(0, 180)
            b = random.randint(0, 180)
            self.character_colors[name] = "#%02x%02x%02x" % (r, g, b)
        return self.character_colors[name]

    # ---------- Public API for VoicesTab ----------
    def get_characters(self):
        if not self.char_list:
            return []
        chars = [self.char_list.get(i) for i in range(self.char_list.size())]
        # Make sure Narrator is always available for voice assignment
        if "Narrator" not in chars:
            chars.insert(0, "Narrator")
        return chars
    
    def get_chapter_dialogue(self):
        dialogue = {}
        for chapter in self.chapters:
            lines = []
            for r in chapter.get("results", []):
                if isinstance(r, dict):
                    speaker = r.get("speaker", "Unknown")
                    text = r.get("text", "")
                    if speaker and text:
                        lines.append((speaker, text))
            if lines:
                dialogue[chapter["title"]] = lines
        return dialogue

    def get_current_characters(self):
        return [self.char_list.get(i) for i in range(self.char_list.size())]
