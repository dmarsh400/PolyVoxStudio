import os
import json
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from tkinter import messagebox, ttk


class ScrollableDropdown(ctk.CTkFrame):
    """Dropdown widget with a scrollable popup that fits long option labels."""

    def __init__(self, master, values, command=None, width=240, button_height=30, max_width=520, max_height=320, **kwargs):
        super().__init__(master, **kwargs)
        self._values = list(values) if values else []
        self._command = command
        self._base_width = width
        self._max_width = max_width
        self._max_height = max_height
        self._button_height = button_height
        self._selection = ""

        self._debug_enabled = os.environ.get("POLYVOX_DEBUG_DROPDOWN") == "1"
        self._dropdown_window = None
        self._list_frame = None
        self._root_click_binding = None
        self._root_config_binding = None
        self._padding = 4
        self._popup_width = self._base_width

        self._display_btn = ctk.CTkButton(
            self,
            text="",
            anchor="w",
            width=self._base_width,
            height=self._button_height,
            fg_color=None,
            text_color=None,
            border_width=1,
            command=self._toggle_dropdown,
        )
        self._display_btn.pack(fill="x", expand=True)

        placeholder = self._values[0] if self._values else "(no options)"
        self.set(placeholder)
        self._ensure_width()

        self.bind("<Destroy>", self._handle_destroy)

    def set(self, value):
        self._selection = value or ""
        self._display_btn.configure(text=self._selection if self._selection else "(no options)")
        self._ensure_width()

    def get(self):
        return self._selection

    def configure(self, **kwargs):  # type: ignore[override]
        if "values" in kwargs:
            self._values = list(kwargs.pop("values"))
            if self._selection not in self._values and self._values:
                self.set(self._values[0])
            if self._dropdown_window is not None:
                self._rebuild_dropdown()
            self._ensure_width()
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "width" in kwargs:
            self._base_width = kwargs.pop("width")
            self._ensure_width()
        if "max_width" in kwargs:
            self._max_width = kwargs.pop("max_width")
            self._ensure_width()
        super().configure(**kwargs)

    def _toggle_dropdown(self):
        if self._dropdown_window is None:
            self._open_dropdown()
        else:
            self._close_dropdown()

    def _open_dropdown(self):
        if not self._values:
            return

        if self._dropdown_window is not None:
            self._close_dropdown()

        self.update_idletasks()

        root = self.winfo_toplevel()
        popup_width = self._popup_width
        height = self._get_dropdown_height()
        width = popup_width + 6
        padding = self._padding
        window_width = width + padding * 2
        window_height = height + padding * 2

        dropdown = ctk.CTkToplevel(root)
        dropdown.withdraw()
        dropdown.overrideredirect(True)
        dropdown.transient(root)
        dropdown.attributes("-topmost", True)

        self._debug(
            "open",
            {
                "popup_width": popup_width,
                "width": width,
                "height": height,
                "window_width": window_width,
                "window_height": window_height,
            },
        )

        popup_bg = ctk.ThemeManager.theme.get("CTk", {}).get("fg_color", "system")
        try:
            dropdown.configure(fg_color=popup_bg)
        except tk.TclError:
            pass

        outer_frame = ctk.CTkFrame(
            dropdown,
            corner_radius=8,
            fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"],
        )
        outer_frame.pack(fill="both", expand=True, padx=padding, pady=padding)

        self._list_frame = ctk.CTkScrollableFrame(
            outer_frame,
            width=width,
            height=height,
            corner_radius=0,
            fg_color="transparent",
        )
        self._list_frame.pack(fill="both", expand=True)

        self._populate_dropdown_buttons()

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._list_frame.bind(sequence, self._on_mousewheel, add="+")

        self._dropdown_window = dropdown
        self._bind_root_events(root)
        self._reposition_dropdown(window_width, window_height)

        try:
            dropdown.deiconify()
            dropdown.lift()
            dropdown.after_idle(lambda: self._reposition_dropdown(window_width, window_height))
            dropdown.after(20, self._focus_dropdown)
        except tk.TclError:
            self._close_dropdown()
            return

        dropdown.bind("<FocusOut>", lambda _event: self._close_dropdown())

        dropdown.after(40, self._log_actual_geometry)

    def _populate_dropdown_buttons(self):
        if self._list_frame is None:
            return

        container = getattr(self._list_frame, "scrollable_frame", self._list_frame)

        for child in container.winfo_children():
            child.destroy()

        active_value = self._selection
        popup_width = self._popup_width
        for value in self._values:
            is_active = value == active_value
            btn = ctk.CTkButton(
                container,
                text=value,
                anchor="w",
                width=popup_width,
                height=self._button_height,
                fg_color=("#3a3a3a" if is_active else "transparent"),
                hover_color=("#4c4c4c" if is_active else ctk.ThemeManager.theme["CTkButton"]["hover_color"]),
                text_color=None,
                command=lambda v=value: self._on_select(v),
            )
            btn.pack(fill="x", padx=4, pady=2)
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                btn.bind(sequence, self._on_mousewheel, add="+")

    def _rebuild_dropdown(self):
        if self._dropdown_window is None:
            return
        self._populate_dropdown_buttons()
        self._reposition_dropdown()

    def _on_select(self, value):
        self.set(value)
        if self._command is not None:
            self._command(value)
        self._close_dropdown()

    def _close_dropdown(self):
        if self._dropdown_window is not None:
            self._debug("close")
            try:
                self._dropdown_window.destroy()
            except tk.TclError:
                pass
            self._dropdown_window = None
            self._list_frame = None
            self._unbind_root_events()

    def _handle_destroy(self, event):
        if event.widget is self:
            self._close_dropdown()

    def _ensure_width(self):
        target = max(self._base_width, self._compute_required_width())
        target = min(target, self._max_width)
        changed = target != getattr(self, "_popup_width", None)
        self._popup_width = target
        self._display_btn.configure(width=target)
        if changed:
            self._reposition_dropdown()
        self._debug(
            "ensure_width",
            {
                "base_width": self._base_width,
                "computed_width": self._compute_required_width(),
                "popup_width": self._popup_width,
                "max_width": self._max_width,
            },
        )

    def _compute_required_width(self):
        if not self._values:
            return self._base_width
        try:
            font = tkfont.Font(font=self._display_btn.cget("font"))
            text_px = max(font.measure(v) for v in self._values)
        except tk.TclError:
            text_px = max(len(v) for v in self._values) * 8
        return text_px + 48

    def _get_dropdown_height(self):
        if not self._values:
            return min(120, self._max_height)
        content_height = len(self._values) * (self._button_height + 4)
        return min(self._max_height, max(120, content_height))

    def _on_mousewheel(self, event):
        if self._list_frame is None:
            return
        canvas = getattr(self._list_frame, "_parent_canvas", None)
        if canvas is None:
            return
        try:
            if event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                canvas.yview_scroll(1, "units")
        except tk.TclError:
            pass

    def _focus_dropdown(self):
        if self._dropdown_window is None:
            return
        try:
            self._dropdown_window.focus_force()
        except tk.TclError:
            pass

    def _reposition_dropdown(self, window_width=None, window_height=None):
        if self._dropdown_window is None:
            return
        popup_width = self._popup_width
        width = popup_width + 6
        height = self._get_dropdown_height()
        padding = self._padding
        win_width = window_width if window_width is not None else width + padding * 2
        win_height = window_height if window_height is not None else height + padding * 2
        pos_x, pos_y = self._calculate_anchor_position(win_width, win_height)
        self._debug(
            "reposition",
            {
                "popup_width": popup_width,
                "height": height,
                "window_width": win_width,
                "window_height": win_height,
                "pos_x": pos_x,
                "pos_y": pos_y,
            },
        )
        try:
            self._dropdown_window.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        except tk.TclError:
            return
        if self._list_frame is not None:
            try:
                self._list_frame.configure(width=width, height=height)
                container = getattr(self._list_frame, "scrollable_frame", self._list_frame)
                for child in container.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        child.configure(width=self._popup_width)
            except tk.TclError:
                pass

    def _calculate_anchor_position(self, window_width, window_height):
        try:
            root = self.winfo_toplevel()
        except tk.TclError:
            return 0, 0

        try:
            root.update_idletasks()
            self.update_idletasks()
            self._display_btn.update_idletasks()
        except tk.TclError:
            return 0, 0

        try:
            btn_root_x = self._display_btn.winfo_rootx()
            btn_root_y = self._display_btn.winfo_rooty()
            btn_height = self._display_btn.winfo_height()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root_x = root.winfo_rootx()
            root_y = root.winfo_rooty()
            root_width = root.winfo_width()
            root_height = root.winfo_height()

            abs_x = btn_root_x
            abs_y = btn_root_y + btn_height + 2

            if abs_x + window_width > screen_width - 4:
                abs_x = max(4, screen_width - window_width - 4)

            if abs_y + window_height > screen_height - 4:
                above_y = btn_root_y - window_height - 2
                if above_y >= 4:
                    abs_y = above_y
                else:
                    abs_y = max(4, screen_height - window_height - 4)

            self._debug(
                "anchor",
                {
                    "btn_root_x": btn_root_x,
                    "btn_root_y": btn_root_y,
                    "btn_height": btn_height,
                    "root_x": root_x,
                    "root_y": root_y,
                    "root_width": root_width,
                    "root_height": root_height,
                    "screen_width": screen_width,
                    "screen_height": screen_height,
                    "window_width": window_width,
                    "window_height": window_height,
                    "abs_x": abs_x,
                    "abs_y": abs_y,
                },
            )
            return int(abs_x), int(abs_y)
        except tk.TclError:
            return 0, 0

    def _bind_root_events(self, root):
        self._unbind_root_events()

        def _on_root_click(event):
            if self._dropdown_window is None:
                return
            try:
                x1 = self._dropdown_window.winfo_rootx()
                y1 = self._dropdown_window.winfo_rooty()
                x2 = x1 + self._dropdown_window.winfo_width()
                y2 = y1 + self._dropdown_window.winfo_height()
                if not (x1 <= event.x_root <= x2 and y1 <= event.y_root <= y2):
                    self._close_dropdown()
            except tk.TclError:
                self._close_dropdown()

        def _on_root_configure(_event):
            self._reposition_dropdown()

        self._root_click_binding = root.bind("<Button-1>", _on_root_click, add="+")
        self._root_config_binding = root.bind("<Configure>", _on_root_configure, add="+")

    def _unbind_root_events(self):
        try:
            root = self.winfo_toplevel()
        except tk.TclError:
            root = None

        if root is not None:
            if self._root_click_binding is not None:
                try:
                    root.unbind("<Button-1>", self._root_click_binding)
                except tk.TclError:
                    pass
                self._root_click_binding = None
            if self._root_config_binding is not None:
                try:
                    root.unbind("<Configure>", self._root_config_binding)
                except tk.TclError:
                    pass
                self._root_config_binding = None

    def _log_actual_geometry(self):
        if self._dropdown_window is None or not self._debug_enabled:
            return
        try:
            self._debug(
                "actual_geometry",
                {
                    "x": self._dropdown_window.winfo_rootx(),
                    "y": self._dropdown_window.winfo_rooty(),
                    "width": self._dropdown_window.winfo_width(),
                    "height": self._dropdown_window.winfo_height(),
                },
            )
        except tk.TclError:
            pass

    def _debug(self, label, payload=None):
        if not self._debug_enabled:
            return
        identifier = f"id={self.winfo_id()}" if self.winfo_exists() else "id=<destroyed>"
        if payload is not None:
            print(f"[ScrollableDropdown:{label}] {identifier} {payload}")
        else:
            print(f"[ScrollableDropdown:{label}] {identifier}")



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
        self.list_frame = ctk.CTkFrame(left_panel)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Treeview for voice list
        columns = ("name", "type", "gender", "age", "accent")
        self.voice_tree = ttk.Treeview(
            self.list_frame,
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
        
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.voice_tree.yview)
        self.voice_tree.configure(yscrollcommand=scrollbar.set)
        
        self.voice_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Voice management buttons
        btn_frame = ctk.CTkFrame(left_panel)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame, text="Refresh List", command=self._refresh_voice_list
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="Edit Selected", command=self._edit_selected_voice
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="Delete Selected", command=self._delete_selected_voice,
            fg_color="red", hover_color="darkred"
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="View Details", command=self._view_voice_details
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="Test Voice", command=self._test_selected_voice
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame, text="Set as Default", command=self._set_as_default_narrator
        ).pack(fill="x", pady=2)
        
        # Edit Voices Dialog (initially hidden)
        self.edit_dialog = None
        
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
            right_panel, text="Refresh Characters", command=self.refresh_characters
        ).pack(fill="x", padx=10, pady=5)

        self.assign_scroll = ctk.CTkScrollableFrame(right_panel)
        self.assign_scroll.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.send_button = ctk.CTkButton(
            right_panel,
            text="Send to Audio Processing",
            command=self.send_to_audio_processing,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.send_button.pack(fill="x", padx=10, pady=10, side="bottom")
        
        # Initial population
        self._refresh_voice_list()
        
        # Apply theme colors
        self._apply_theme_colors()

    def _apply_theme_colors(self):
        """Apply appropriate colors based on current theme."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        
        if is_dark:
            # Dark theme colors - use grey background with white text
            bg_color = "#606060"
            fg_color = "#ffffff"
            tree_bg = "#606060"
            tree_fg = "#ffffff"
            tree_select_bg = "#404040"
            tree_select_fg = "#ffffff"
        else:
            # Light theme colors
            bg_color = "#ffffff"
            fg_color = "#000000"
            tree_bg = "#ffffff"
            tree_fg = "#000000"
            tree_select_bg = "#0078d4"
            tree_select_fg = "#ffffff"
        
        # Configure Treeview style for theme
        style = ttk.Style()
        style.configure("Treeview",
            background=tree_bg,
            foreground=tree_fg,
            fieldbackground=tree_bg
        )
        style.configure("Treeview.Heading",
            background=tree_bg,
            foreground=tree_fg
        )
        style.map("Treeview",
            background=[("selected", tree_select_bg)],
            foreground=[("selected", tree_select_fg)]
        )
        
        # Update list frame background
        if hasattr(self, 'list_frame') and self.list_frame:
            self.list_frame.configure(fg_color=tree_bg)
        
        # Apply to stats label
        if self.stats_label:
            self.stats_label.configure(text_color=fg_color)

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

        if not hasattr(self, "assign_scroll") or self.assign_scroll is None:
            return

        container = getattr(self.assign_scroll, "scrollable_frame", self.assign_scroll)

        for widget in container.winfo_children():
            widget.destroy()

        if not characters:
            ctk.CTkLabel(container, text="No characters detected.").pack(pady=10)
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
            frame = ctk.CTkFrame(container)
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

            dropdown = ScrollableDropdown(
                frame,
                values=all_options,
                command=lambda choice, c=char, vlm=voice_label_map: self._set_voice_with_map(c, choice, vlm),
                width=260,
            )
            dropdown.set(display_selection)
            dropdown.pack(side="left", padx=5, fill="x", expand=True)
    
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
    
    def _edit_selected_voice(self):
        """Open edit dialog for the selected voice"""
        selection = self.voice_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a voice to edit.")
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
        
        self._open_edit_dialog(voice)
    
    def _open_edit_dialog(self, voice):
        """Open the voice editing dialog"""
        if self.edit_dialog:
            self.edit_dialog.destroy()
        
        # Create dialog window
        self.edit_dialog = ctk.CTkToplevel(self)
        self.edit_dialog.title(f"Edit Voice: {voice.get('label', 'Unknown')}")
        self.edit_dialog.geometry("500x600")
        self.edit_dialog.resizable(False, False)
        
        # Make it modal - moved after dialog construction
        self.edit_dialog.transient(self)
        
        # Center the dialog
        self.edit_dialog.update_idletasks()
        x = (self.edit_dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.edit_dialog.winfo_screenheight() // 2) - (600 // 2)
        self.edit_dialog.geometry(f"+{x}+{y}")
        
        # Title
        ctk.CTkLabel(
            self.edit_dialog, 
            text=f"Edit Voice: {voice.get('label', 'Unknown')}", 
            font=("Arial", 16, "bold")
        ).pack(pady=20)
        
        # Form frame
        form_frame = ctk.CTkFrame(self.edit_dialog)
        form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Voice Name
        ctk.CTkLabel(form_frame, text="Voice Name:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        name_entry = ctk.CTkEntry(form_frame, width=400)
        name_entry.insert(0, voice.get("label", ""))
        name_entry.pack(padx=10, pady=(0, 10))
        
        # Type dropdown
        ctk.CTkLabel(form_frame, text="Type:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        type_var = ctk.StringVar(value="Standard" if not voice.get("custom_cloned", False) else "Custom Cloned")
        type_menu = ctk.CTkOptionMenu(
            form_frame, 
            values=["Standard", "Custom Cloned"],
            variable=type_var,
            width=400
        )
        type_menu.pack(padx=10, pady=(0, 10))
        
        # Gender dropdown
        ctk.CTkLabel(form_frame, text="Gender:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        gender_var = ctk.StringVar(value=voice.get("gender", "Unknown"))
        gender_menu = ctk.CTkOptionMenu(
            form_frame, 
            values=["Male", "Female", "Unknown"],
            variable=gender_var,
            width=400
        )
        gender_menu.pack(padx=10, pady=(0, 10))
        
        # Age dropdown
        ctk.CTkLabel(form_frame, text="Age:", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        age_var = ctk.StringVar(value=voice.get("age", "Unknown"))
        age_menu = ctk.CTkOptionMenu(
            form_frame, 
            values=["Teen", "Young Adult", "Adult", "Middle-Aged", "Mature", "Senior", "Unknown"],
            variable=age_var,
            width=400
        )
        age_menu.pack(padx=10, pady=(0, 20))
        
        # Buttons frame
        btn_frame = ctk.CTkFrame(self.edit_dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Save button
        save_btn = ctk.CTkButton(
            btn_frame, 
            text="Save", 
            command=lambda: self._save_voice_changes(voice, name_entry.get(), type_var.get(), gender_var.get(), age_var.get(), save_as=False),
            fg_color="green",
            hover_color="darkgreen"
        )
        save_btn.pack(side="left", padx=(0, 10), expand=True)
        
        # Save As button
        save_as_btn = ctk.CTkButton(
            btn_frame, 
            text="Save As New", 
            command=lambda: self._save_voice_changes(voice, name_entry.get(), type_var.get(), gender_var.get(), age_var.get(), save_as=True),
            fg_color="blue",
            hover_color="darkblue"
        )
        save_as_btn.pack(side="left", expand=True)
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            command=self.edit_dialog.destroy,
            fg_color="gray",
            hover_color="darkgray"
        )
        cancel_btn.pack(side="right", padx=(10, 0), expand=True)
        
        # Now that dialog is fully constructed, make it modal
        self.edit_dialog.grab_set()
    
    def _save_voice_changes(self, original_voice, new_name, new_type, new_gender, new_age, save_as=False):
        """Save the voice changes"""
        if not new_name.strip():
            messagebox.showerror("Error", "Voice name cannot be empty.")
            return
        
        # Check for duplicate names (only if not saving as new)
        if not save_as:
            all_voices = self.narrators + self.voices
            for v in all_voices:
                if v != original_voice and v.get("label") == new_name:
                    messagebox.showerror("Error", f"A voice with the name '{new_name}' already exists.")
                    return
        
        # Create updated voice data
        updated_voice = original_voice.copy()
        updated_voice["label"] = new_name
        updated_voice["gender"] = new_gender if new_gender != "Unknown" else None
        updated_voice["age"] = new_age if new_age != "Unknown" else None
        updated_voice["custom_cloned"] = (new_type == "Custom Cloned")
        
        if save_as:
            # Add as new voice
            if original_voice in self.narrators:
                self.narrators.append(updated_voice)
            else:
                self.voices.append(updated_voice)
            messagebox.showinfo("Success", f"Voice '{new_name}' has been created as a new voice.")
        else:
            # Update existing voice
            if original_voice in self.narrators:
                idx = self.narrators.index(original_voice)
                self.narrators[idx] = updated_voice
            else:
                idx = self.voices.index(original_voice)
                self.voices[idx] = updated_voice
            
            # Update voice selections if the name changed
            if original_voice.get("label") != new_name:
                old_name = original_voice.get("label")
                for char, voice in self.voice_selections.items():
                    if voice == old_name:
                        self.voice_selections[char] = new_name
                self._save_selections()
            
            messagebox.showinfo("Success", f"Voice '{new_name}' has been updated.")
        
        # Save and refresh
        self._save_voices_json()
        self._refresh_voice_list()
        self.refresh_characters()
        
        # Close dialog
        if self.edit_dialog:
            self.edit_dialog.destroy()
            self.edit_dialog = None
        
        self._log(f"[VoicesTab] {'Created' if save_as else 'Updated'} voice: {new_name}")
    
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
