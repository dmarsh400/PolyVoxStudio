import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import customtkinter as ctk
import random
import os
import json

from app.core import character_detection


# -----------------------------
# Tooltip helper
# -----------------------------
class ToolTip:
    def __init__(self, widget, text, characters_tab=None):
        self.widget = widget
        self.text = text
        self.characters_tab = characters_tab  # Reference to parent tab for character coloring
        self.tip_window = None
        self.mouse_over_tooltip = False  # Track if mouse is over tooltip
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self._on_widget_leave)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Get theme colors
        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
            border_color = "#555555"
        else:
            bg_color = "#ffffe0"
            fg_color = "#000000"
            border_color = "#000000"
        
        # Get tooltip font size from characters tab
        tooltip_font_size = 12  # default
        if self.characters_tab:
            tooltip_font_size = int(self.characters_tab.tooltip_text_size_var.get())
        
        # Create frame to hold text widget and scrollbar
        main_frame = tk.Frame(tw, bg=bg_color, relief="solid", borderwidth=2)
        main_frame.pack(fill="both", expand=True)
        
        # Create scrollbar
        scrollbar = tk.Scrollbar(main_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        # Create text widget for rich formatting (supports colored text)
        text_widget = tk.Text(
            main_frame,
            wrap="word",
            font=("Arial", tooltip_font_size),  # Use dynamic font size
            bg=bg_color,
            fg=fg_color,
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=6,
            width=60,
            height=8,
            yscrollcommand=scrollbar.set
        )
        
        # Configure scrollbar
        scrollbar.config(command=text_widget.yview)
        
        text_widget.pack(side="left", fill="both", expand=True)
        
        # Apply character name coloring to the tooltip text
        if self.characters_tab:
            self.characters_tab._color_character_names_in_text(text_widget, self.text, tooltip_font_size)
        else:
            text_widget.insert("1.0", self.text)
        
        text_widget.config(state="disabled")  # Make read-only
        
        # Adjust window size to fit content
        text_widget.update_idletasks()
        width = min(text_widget.winfo_reqwidth() + 30, 600)  # Max width 600px, extra space for scrollbar
        height = min(text_widget.winfo_reqheight() + 20, 400)  # Max height 400px
        tw.wm_geometry(f"{width}x{height}")
        
        # Bind mouse events to tooltip window to capture mouse when hovering over tooltip
        tw.bind("<Enter>", self._on_tooltip_enter)
        tw.bind("<Leave>", self._on_tooltip_leave)
        
        # Bind scroll events to prevent them from bubbling up to underlying widgets
        tw.bind("<MouseWheel>", self._on_tooltip_scroll)
        tw.bind("<Button-4>", self._on_tooltip_scroll)  # Linux scroll up
        tw.bind("<Button-5>", self._on_tooltip_scroll)  # Linux scroll down

    def _format_text_with_character_colors(self, text):
        """Format text with character names colored according to their assigned colors."""
        if not self.characters_tab or not text:
            return text
        
        # Get all character names and their colors
        characters = self.characters_tab.get_current_characters()
        character_colors = {}
        
        for char in characters:
            if char in self.characters_tab.character_colors:
                character_colors[char] = self.characters_tab.character_colors[char]
            elif char == "Narrator":
                character_colors[char] = self.characters_tab.narrator_color
        
        # Sort by length (longest first) to avoid partial matches
        sorted_chars = sorted(character_colors.keys(), key=len, reverse=True)
        
        # For tooltips, we'll return the text as-is since the Text widget will handle coloring
        # The coloring will be applied when the tooltip Text widget is created
        return text

    def _on_tooltip_enter(self, event=None):
        """Handle mouse entering tooltip window."""
        self.mouse_over_tooltip = True
    
    def _on_tooltip_leave(self, event=None):
        """Handle mouse leaving tooltip window."""
        self.mouse_over_tooltip = False
        # Check if we should hide the tooltip after a short delay
        self.widget.after(100, self._check_hide_tooltip)
    
    def _on_tooltip_scroll(self, event):
        """Handle scroll events on tooltip to prevent them from bubbling up."""
        # Find the text widget and scrollbar in the tooltip
        if self.tip_window:
            # Find text widgets in the tooltip
            for child in self.tip_window.winfo_children():
                if isinstance(child, tk.Frame):  # main_frame
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Text):
                            # Handle scroll event on the text widget
                            if event.delta > 0 or event.num == 4:  # Scroll up
                                subchild.yview_scroll(-1, "units")
                            elif event.delta < 0 or event.num == 5:  # Scroll down
                                subchild.yview_scroll(1, "units")
                            return "break"  # Prevent event from bubbling up
        return "break"  # Prevent event from bubbling up anyway

    def _on_widget_leave(self, event=None):
        """Handle mouse leaving the widget - delay hiding tooltip to allow mouse to move to tooltip."""
        self.widget.after(100, self._check_hide_tooltip)
    
    def _check_hide_tooltip(self):
        """Check if tooltip should be hidden after mouse leaves."""
        if not self.mouse_over_tooltip and self.tip_window:
            self.hide_tip()

    def hide_tip(self, event=None):
        """Hide the tooltip, but only if mouse is not over the tooltip itself."""
        if self.mouse_over_tooltip:
            return  # Don't hide if mouse is over tooltip
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
        
        # Text size control
        self.line_text_size_var = tk.StringVar(value="11")
        self.tooltip_text_size_var = tk.StringVar(value="12")
        
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
            font=("Arial", int(self.line_text_size_var.get()))  # Use dynamic font size
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

        # Save/Load assignments
        ctk.CTkButton(char_frame, text="Save Assignments", command=self.save_assignments).pack(pady=5)
        ctk.CTkButton(char_frame, text="Load Assignments", command=self.load_assignments).pack(pady=5)

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

        # Text size controls
        line_size_label = ctk.CTkLabel(search_filter_frame, text="Line Size:", font=("Arial", 11))
        line_size_label.pack(side="left", padx=(20, 5), pady=5)
        
        self.line_size_dropdown = ctk.CTkComboBox(
            search_filter_frame,
            variable=self.line_text_size_var,
            values=["8", "9", "10", "11", "12", "14", "16", "18", "20"],
            width=60,
            command=self.on_line_size_changed
        )
        self.line_size_dropdown.pack(side="left", padx=2, pady=5)
        
        tooltip_size_label = ctk.CTkLabel(search_filter_frame, text="Tooltip Size:", font=("Arial", 11))
        tooltip_size_label.pack(side="left", padx=(10, 5), pady=5)
        
        self.tooltip_size_dropdown = ctk.CTkComboBox(
            search_filter_frame,
            variable=self.tooltip_text_size_var,
            values=["8", "9", "10", "11", "12", "14", "16", "18", "20"],
            width=60,
            command=self.on_tooltip_size_changed
        )
        self.tooltip_size_dropdown.pack(side="left", padx=2, pady=5)

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

        # Apply theme colors
        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """Apply appropriate colors based on current theme."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        
        if is_dark:
            # Dark theme colors
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
            select_bg = "#404040"
            select_fg = "#ffffff"
        else:
            # Light theme colors
            bg_color = "#ffffff"
            fg_color = "#000000"
            select_bg = "#0078d4"
            select_fg = "#ffffff"
        
        # Apply to character listbox
        if self.char_list:
            self.char_list.config(
                bg=bg_color,
                fg=fg_color,
                selectbackground=select_bg,
                selectforeground=select_fg
            )
        
        # Apply to placeholder label
        if self.placeholder_label:
            self.placeholder_label.config(bg=bg_color, fg=fg_color)
        
        # Apply to scroll frame background
        if self.scroll_frame:
            self.scroll_frame.config(bg=bg_color)
        
        # Regenerate character colors for new theme
        old_colors = self.character_colors.copy()
        self.character_colors.clear()
        # Reassign colors to existing characters
        for name in old_colors:
            if name != "Narrator":  # Skip narrator, it has fixed color
                self._get_color(name)
        
        # Refresh the character list display
        self._refresh_char_list()

    def _color_character_names_in_text(self, text_widget, text, font_size=11):
        """Apply character name coloring to a Text widget, including partial name matches."""
        # Get all character names and their colors
        characters = list(self.character_colors.keys())
        if "Narrator" not in characters:
            characters.append("Narrator")
        character_colors = {}
        
        for char in characters:
            if char in self.character_colors:
                character_colors[char] = self.character_colors[char]
            elif char == "Narrator":
                character_colors[char] = self.narrator_color
        
        # Insert the text
        text_widget.insert("1.0", text)
        
        # Create a list of all name parts to match, with their associated character and color
        name_parts = []
        for char_name, color in character_colors.items():
            if char_name == "Narrator":
                # Special handling for Narrator - only match exact
                name_parts.append((char_name, color, len(char_name)))
            else:
                # Split character name into parts (first, last, etc.)
                parts = char_name.split()
                for part in parts:
                    if len(part) > 1:  # Only match parts longer than 1 character
                        name_parts.append((part, color, len(part)))
        
        # Sort by length (longest first) to avoid partial matches overriding longer matches
        name_parts.sort(key=lambda x: x[2], reverse=True)
        
        # Apply coloring to character name parts
        applied_ranges = []  # Track ranges that have been colored to avoid overlaps
        
        for name_part, color, length in name_parts:
            start_idx = "1.0"
            while True:
                # Find the name part
                start_idx = text_widget.search(name_part, start_idx, nocase=False, stopindex="end")
                if not start_idx:
                    break
                
                end_idx = f"{start_idx}+{len(name_part)}c"
                
                # Apply color tag (simplified - no overlap prevention for now)
                tag_name = f"char_{name_part.replace(' ', '_')}_{color}"
                text_widget.tag_configure(tag_name, foreground=color, font=("Arial", font_size, "bold"))
                text_widget.tag_add(tag_name, start_idx, end_idx)
                
                start_idx = end_idx

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
        
        self.log_debug(f"[CharactersTab] Merge selected - names: {names}, selection indices: {selection}")

        # Dropdown to pick survivor
        survivor = self._prompt_survivor_dropdown(names)
        if not survivor:
            return
        
        self.log_debug(f"[CharactersTab] User selected survivor: '{survivor}'")

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

    def save_assignments(self):
        """Save character assignments to a JSON file."""
        if not self.chapters:
            messagebox.showwarning("Warning", "No chapters with assignments to save.")
            return
        
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Character Assignments"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.chapters, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Assignments saved to {file_path}")
            self.log_debug(f"[CharactersTab] Saved assignments to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save assignments: {e}")
            self.log_debug(f"[CharactersTab] Failed to save assignments: {e}")

    def load_assignments(self):
        """Load character assignments from a JSON file."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load Character Assignments"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_chapters = json.load(f)
            
            # Validate structure
            if not isinstance(loaded_chapters, list):
                raise ValueError("Invalid file format")
            
            for chapter in loaded_chapters:
                if not isinstance(chapter, dict) or "title" not in chapter or "text" not in chapter:
                    raise ValueError("Invalid chapter structure")
            
            self.chapters = loaded_chapters
            self._refresh_char_list()
            self.show_lines()
            messagebox.showinfo("Success", f"Assignments loaded from {file_path}")
            self.log_debug(f"[CharactersTab] Loaded assignments from {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load assignments: {e}")
            self.log_debug(f"[CharactersTab] Failed to load assignments: {e}")

    def _prompt_survivor_dropdown(self, names):
        win = tk.Toplevel(self)
        win.title("Merge Characters")
        
        info_text = f"Merging {len(names)} characters:\n{', '.join(names)}\n\nSelect the surviving character:"
        tk.Label(win, text=info_text, justify="left").pack(pady=10, padx=10)

        # Create dropdown without StringVar to avoid binding issues
        dropdown = ttk.Combobox(win, values=names, state="readonly", width=30)
        dropdown.set(names[0])  # Set default
        dropdown.pack(pady=5, padx=10)
        dropdown.focus_set()

        result = {"value": None}

        def confirm():
            # Get value directly from dropdown widget
            selected = dropdown.get()
            self.log_debug(f"[_prompt_survivor_dropdown] User selected from dropdown: '{selected}'")
            if selected and selected in names:
                result["value"] = selected
            else:
                self.log_debug(f"[_prompt_survivor_dropdown] WARNING: Invalid selection '{selected}', defaulting to first")
                result["value"] = names[0]
            win.destroy()
        
        def cancel():
            self.log_debug(f"[_prompt_survivor_dropdown] User cancelled")
            result["value"] = None
            win.destroy()

        button_frame = tk.Frame(win)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="OK", command=confirm, width=10, bg="green", fg="white").pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel, width=10).pack(side="left", padx=5)
        
        # Bind Enter key to confirm
        dropdown.bind("<Return>", lambda e: confirm())

        win.transient(self)
        win.wait_visibility()
        win.grab_set()
        self.wait_window(win)
        
        self.log_debug(f"[_prompt_survivor_dropdown] Final result: '{result['value']}'")
        return result["value"]

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
    
    def on_line_size_changed(self, choice):
        """Handle line text size dropdown selection change."""
        self.line_text_size_var.set(choice)
        self.log_debug(f"[CharactersTab] Line text size changed to: '{choice}'")
        # Update character list font
        if self.char_list:
            self.char_list.config(font=("Arial", int(choice)))
        self.show_lines()  # Refresh display with new text size
    
    def on_tooltip_size_changed(self, choice):
        """Handle tooltip text size dropdown selection change."""
        self.tooltip_text_size_var.set(choice)
        self.log_debug(f"[CharactersTab] Tooltip text size changed to: '{choice}'")
        # Tooltips will use the new size on next hover
    
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

        # Get theme colors
        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
            select_bg = "#404040"
            select_fg = "#ffffff"
        else:
            bg_color = "#ffffff"
            fg_color = "#000000"
            select_bg = "#0078d4"
            select_fg = "#ffffff"

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
                bg=bg_color
            )
            no_results_label.pack(pady=20)
            return

        self.line_vars = []
        for idx, result in enumerate(filtered_results):
            # Add visual distinction for quote vs non-quote rows
            is_quote = result.get("is_quote", False)
            row_bg_color = "#ffffff" if is_quote else "#f0f0f0"  # white for quotes, light gray for narrator
            if is_dark:
                row_bg_color = "#3a3a3a" if is_quote else "#2b2b2b"  # darker for dark theme
            
            frame = tk.Frame(self.scroll_frame, bg=row_bg_color, relief="solid", borderwidth=1)
            frame.pack(fill="x", pady=1)

            var = tk.IntVar(master=frame, value=0)
            chk = tk.Checkbutton(frame, variable=var, bg=row_bg_color)
            chk.pack(side="left", padx=5)
            self.line_vars.append((var, result))

            speaker = result.get("speaker", "Unknown")
            color = self._get_color(speaker)
            line_font_size = int(self.line_text_size_var.get())
            spk_label = tk.Label(frame, text=speaker, fg=color, width=15, anchor="w", bg=row_bg_color, font=("Arial", line_font_size))
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
            
            line_font_size = int(self.line_text_size_var.get())
            
            # Always use Text widget for character name coloring
            txt_widget = tk.Text(
                frame, 
                wrap="word",
                width=1,  # Will be controlled by pack
                bg=row_bg_color, 
                font=("Arial", line_font_size), 
                fg=fg_color,
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                cursor="arrow",
                padx=2,
                pady=2
            )
            
            # Apply character name coloring
            self._color_character_names_in_text(txt_widget, display_text, line_font_size)
            
            # Apply search highlighting if searching
            if search_text:
                # Configure tag for search highlighting (different from character coloring)
                txt_widget.tag_configure("search_highlight", background="#FFFF00", foreground="#000000")
                
                # Find and highlight all occurrences of search text (case-insensitive)
                txt_widget.configure(state="normal")
                start_idx = "1.0"
                while True:
                    start_idx = txt_widget.search(search_text, start_idx, nocase=True, stopindex="end")
                    if not start_idx:
                        break
                    end_idx = f"{start_idx}+{len(search_text)}c"
                    txt_widget.tag_add("search_highlight", start_idx, end_idx)
                    start_idx = end_idx
                
                txt_widget.configure(state="disabled")  # Make read-only
            
            # Calculate height based on content
            num_lines = int(txt_widget.index('end-1c').split('.')[0])
            txt_widget.configure(height=min(num_lines, 10))  # Max 10 lines visible
            
            txt_widget.pack(side="left", fill="both", expand=True, padx=2, pady=2)
            self._text_labels.append(txt_widget)
            
            # Tooltip - always show full text in tooltip
            ToolTip(txt_widget, text, characters_tab=self)

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
            is_dark = ctk.get_appearance_mode() == "Dark"
            
            # Predefined set of highly saturated, distinct colors for maximum vibrancy
            # These are carefully chosen to be bright, saturated, and easily distinguishable
            vibrant_colors = [
                # Primary bright colors - maximum brightness for dark mode
                "#FF4444",  # Bright Red
                "#44FF44",  # Bright Green  
                "#4444FF",  # Bright Blue
                "#FFFF44",  # Bright Yellow
                "#FF44FF",  # Bright Magenta
                "#44FFFF",  # Bright Cyan
                "#FF8844",  # Bright Orange
                "#8844FF",  # Bright Purple
                "#44FF88",  # Bright Spring Green
                "#FF4488",  # Bright Pink
                "#88FF44",  # Bright Lime
                "#4488FF",  # Bright Sky Blue
                "#FF6666",  # Bright Coral
                "#66FF66",  # Bright Electric Green
                "#6666FF",  # Bright Royal Blue
                "#FFFF66",  # Bright Lemon
                "#FF66FF",  # Bright Hot Pink
                "#66FFFF",  # Bright Aqua
                "#FFA066",  # Bright Tangerine
                "#A066FF",  # Bright Violet
                "#66FFA0",  # Bright Mint
                "#FF6688",  # Bright Rose
                "#88FFA0",  # Bright Sea Green
                "#A088FF",  # Bright Lavender
                "#FFA088",  # Bright Peach
                "#88A0FF",  # Bright Periwinkle
                "#A0FFA0",  # Bright Light Green
                "#FFA0A0",  # Bright Light Coral
                "#A0A0FF",  # Bright Light Blue
                "#FFFFA0",  # Bright Light Yellow
                "#FFA0FF",  # Bright Light Magenta
            ]
            
            # Get current character count to determine color assignment
            current_chars = len([n for n in self.character_colors.keys() if n != "Narrator"])
            
            if current_chars < len(vibrant_colors):
                # Use predefined vibrant color
                color = vibrant_colors[current_chars]
            else:
                # Fallback to generating new vibrant colors if we have more characters than predefined colors
                if is_dark:
                    # Generate very bright, saturated colors for dark mode
                    # Use HSV-like approach: high saturation, high value
                    hue = (current_chars * 137.5) % 360  # Golden angle for good distribution
                    
                    # Convert HSV to RGB with high saturation and brightness
                    h = hue / 360.0
                    s = 0.9  # High saturation
                    v = 0.95  # High brightness
                    
                    # HSV to RGB conversion
                    c = v * s
                    x = c * (1 - abs((h * 6) % 2 - 1))
                    m = v - c
                    
                    if 0 <= h < 1/6:
                        r, g, b = c, x, 0
                    elif 1/6 <= h < 2/6:
                        r, g, b = x, c, 0
                    elif 2/6 <= h < 3/6:
                        r, g, b = 0, c, x
                    elif 3/6 <= h < 4/6:
                        r, g, b = 0, x, c
                    elif 4/6 <= h < 5/6:
                        r, g, b = x, 0, c
                    else:
                        r, g, b = c, 0, x
                    
                    r = int((r + m) * 255)
                    g = int((g + m) * 255)
                    b = int((b + m) * 255)
                    
                    # Boost brightness even more for maximum pop in dark mode
                    r = min(255, r + 20)
                    g = min(255, g + 20)  
                    b = min(255, b + 20)
                else:
                    # For light mode, use darker but still saturated colors
                    hue = (current_chars * 137.5) % 360
                    
                    h = hue / 360.0
                    s = 0.8  # High saturation
                    v = 0.6  # Medium brightness for light mode
                    
                    c = v * s
                    x = c * (1 - abs((h * 6) % 2 - 1))
                    m = v - c
                    
                    if 0 <= h < 1/6:
                        r, g, b = c, x, 0
                    elif 1/6 <= h < 2/6:
                        r, g, b = x, c, 0
                    elif 2/6 <= h < 3/6:
                        r, g, b = 0, c, x
                    elif 3/6 <= h < 4/6:
                        r, g, b = 0, x, c
                    elif 4/6 <= h < 5/6:
                        r, g, b = x, 0, c
                    else:
                        r, g, b = c, 0, x
                    
                    r = int((r + m) * 255)
                    g = int((g + m) * 255)
                    b = int((b + m) * 255)
                
                color = "#%02x%02x%02x" % (r, g, b)
            
            self.character_colors[name] = color
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
