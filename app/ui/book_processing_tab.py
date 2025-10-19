import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import os


class BookProcessingTab(ctk.CTkFrame):
    def __init__(self, master, set_book_text_cb, go_to_characters_cb, log_debug=None):
        super().__init__(master)

        self.set_book_text_cb = set_book_text_cb
        self.go_to_characters_cb = go_to_characters_cb
        self.log_debug = log_debug or (lambda msg: print(msg))

        self.current_book_path = None
        self.raw_text = ""
        self.chapters = []

        self.chapter_listbox = None
        self.chapter_preview = None
        self.status_label = None

        self._build_layout()

    def _build_layout(self):
        # Top button row
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        import_button = ctk.CTkButton(button_frame, text="Import Book", command=self._import_book)
        import_button.pack(side="left", padx=5)

        detect_button = ctk.CTkButton(button_frame, text="Detect Chapters", command=self._detect_chapters)
        detect_button.pack(side="left", padx=5)

        send_button = ctk.CTkButton(button_frame, text="Send to Characters", command=self._send_to_characters)
        send_button.pack(side="left", padx=5)

        # Middle split: chapters list + preview
        middle_frame = ctk.CTkFrame(self)
        middle_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left: chapter list
        left_frame = ctk.CTkFrame(middle_frame)
        left_frame.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(left_frame, text="Chapters").pack(anchor="w", padx=5, pady=(5, 2))

        self.chapter_listbox = tk.Listbox(
            left_frame,
            height=25,
            width=40,
            exportselection=False,
            selectmode="extended"
        )
        self.chapter_listbox.pack(fill="y", padx=5, pady=5)
        self.chapter_listbox.bind("<<ListboxSelect>>", self._on_chapter_select)

        # Right: chapter preview
        right_frame = ctk.CTkFrame(middle_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        tk.Label(right_frame, text="Preview").pack(anchor="w", padx=5, pady=(5, 2))

        self.chapter_preview = tk.Text(right_frame, wrap="word")
        self.chapter_preview.config(state="disabled")
        self.chapter_preview.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom status
        self.status_label = ctk.CTkLabel(self, text="No book loaded")
        self.status_label.pack(fill="x", padx=10, pady=(0, 10))

    # ---------- Actions ----------
    def _import_book(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Supported formats", "*.txt *.epub *.pdf"),
                ("Text files", "*.txt"),
                ("EPUB files", "*.epub"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            try:
                from app.core.chapter_chunker import load_book
                
                self.update_status(f"Loading: {os.path.basename(file_path)}...")
                self.master.update_idletasks()  # Update UI to show loading message
                
                self.raw_text = load_book(file_path)
                self.current_book_path = file_path
                
                file_name = os.path.basename(file_path)
                file_size = len(self.raw_text)
                size_kb = file_size / 1024
                
                self.update_status(f"Loaded: {file_name} ({size_kb:.1f} KB, {file_size:,} chars)")
                self.chapters = []
                self.update_chapter_list([])
                self.update_preview(self.raw_text[:2000])
                self.log_debug(f"[BookProcessingTab] Imported book: {file_path} ({size_kb:.1f} KB)")
                
                messagebox.showinfo(
                    "Book Loaded", 
                    f"Successfully loaded:\n{file_name}\n\n"
                    f"Size: {size_kb:.1f} KB\n"
                    f"Characters: {file_size:,}\n\n"
                    f"Click 'Detect Chapters' to analyze structure."
                )
            except ImportError as e:
                self.log_debug(f"[BookProcessingTab] Missing dependency: {e}")
                messagebox.showerror(
                    "Missing Dependency", 
                    f"Cannot load this file format:\n{e}\n\n"
                    f"Install required packages:\n"
                    f"  • For EPUB: pip install ebooklib beautifulsoup4\n"
                    f"  • For PDF: pip install PyPDF2"
                )
            except Exception as e:
                self.log_debug(f"[BookProcessingTab] Failed to load file: {e}")
                messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def _detect_chapters(self):
        if not self.raw_text:
            messagebox.showwarning("No text", "Load a book first.")
            return

        try:
            from app.core.chapter_chunker import smart_chapter_detection
            
            self.update_status("Analyzing chapter structure...")
            self.master.update_idletasks()
            
            # Use smart chapter detection
            detected = smart_chapter_detection(
                self.raw_text,
                min_chapter_length=1000,
                max_chunk_size=50000  # 50K chars per chunk max
            )
            
            self.chapters = detected
            self.update_chapter_list([c["title"] for c in self.chapters])
            
            # Calculate statistics
            avg_length = sum(len(c["text"]) for c in self.chapters) / len(self.chapters)
            
            self.update_status(
                f"Detected {len(self.chapters)} chapter(s)/section(s) "
                f"(avg: {avg_length/1000:.1f}K chars)"
            )
            
            self.log_debug(
                f"[BookProcessingTab] Detected {len(self.chapters)} chapters: "
                f"{[c['title'] for c in self.chapters]}"
            )
            
            messagebox.showinfo(
                "Chapters Detected",
                f"Found {len(self.chapters)} chapter(s)/section(s)\n\n"
                f"Average size: {avg_length/1000:.1f}K characters\n\n"
                f"Select chapters and click 'Send to Characters' to continue."
            )
            
        except Exception as e:
            self.log_debug(f"[BookProcessingTab] Chapter detection failed: {e}")
            messagebox.showerror("Error", f"Chapter detection failed:\n{e}")

    def _on_chapter_select(self, event=None):
        if not self.chapter_listbox.curselection():
            return
        idx = self.chapter_listbox.curselection()[0]
        text = self.chapters[idx]["text"]
        self.update_preview(text[:20000])

    def _send_to_characters(self):
        if not self.raw_text:
            messagebox.showwarning("No text", "Load a book first.")
            return

        selected_indices = self.chapter_listbox.curselection()
        if self.chapters and selected_indices:
            selected_chapters = [
                {"title": self.chapters[i]["title"], "text": self.chapters[i]["text"]}
                for i in selected_indices
            ]
        else:
            selected_chapters = [{"title": "Full Book", "text": self.raw_text}]

        self.set_book_text_cb(selected_chapters)
        self.go_to_characters_cb()

    # ---------- Public API ----------
    def update_chapter_list(self, chapters):
        self.chapter_listbox.delete(0, tk.END)
        for ch in chapters:
            self.chapter_listbox.insert(tk.END, ch)

    def update_preview(self, text):
        self.chapter_preview.config(state="normal")
        self.chapter_preview.delete("1.0", "end")
        self.chapter_preview.insert("1.0", text)
        self.chapter_preview.config(state="disabled")

    def update_status(self, text):
        if hasattr(self, "status_label") and self.status_label is not None:
            self.status_label.configure(text=text)
