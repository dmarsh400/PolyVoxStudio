import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import os
import subprocess

class ChapterProcessingTab(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        # Input file selection
        self.input_path = tk.StringVar()
        ttk.Label(self, text="Input File (.txt or .epub):").grid(row=0, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.input_path, width=50).grid(row=0, column=1, sticky="ew")
        ttk.Button(self, text="Browse", command=self.browse_file).grid(row=0, column=2)

        # Output dir
        self.out_dir = tk.StringVar()
        ttk.Label(self, text="Output Directory:").grid(row=1, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.out_dir, width=50).grid(row=1, column=1, sticky="ew")
        ttk.Button(self, text="Browse", command=self.browse_out).grid(row=1, column=2)

        # Processing mode
        self.proc_mode = tk.StringVar(value="auto")
        ttk.Label(self, text="Processing Mode:").grid(row=2, column=0, sticky="w")
        modes = [("CPU", "cpu"), ("Auto GPU", "auto"), ("Manual GPU", "manual")]
        for i, (label, val) in enumerate(modes):
            ttk.Radiobutton(self, text=label, variable=self.proc_mode, value=val).grid(row=2, column=i+1, sticky="w")

        # Manual GPU entry
        self.gpu_ids = tk.StringVar()
        ttk.Label(self, text="GPU IDs (comma separated):").grid(row=3, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.gpu_ids, width=20).grid(row=3, column=1, sticky="w")

        # Buttons
        ttk.Button(self, text="Start Processing", command=self.start_processing).grid(row=4, column=0, pady=10)
        ttk.Button(self, text="Merge Results", command=self.merge_results).grid(row=4, column=1, pady=10)

        # Progress
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        self.status_text = tk.StringVar(value="Idle")
        ttk.Label(self, textvariable=self.status_text).grid(row=6, column=0, columnspan=3, sticky="w")

        # Log window
        self.log_box = tk.Text(self, height=15, wrap="word", state="disabled")
        self.log_box.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=5)
        scrollbar = ttk.Scrollbar(self, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=7, column=3, sticky="ns")

        self.columnconfigure(1, weight=1)
        self.rowconfigure(7, weight=1)

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text or EPUB", "*.txt *.epub")])
        if path:
            self.input_path.set(path)

    def browse_out(self):
        path = filedialog.askdirectory()
        if path:
            self.out_dir.set(path)

    def start_processing(self):
        infile = self.input_path.get()
        outdir = self.out_dir.get()
        if not infile or not outdir:
            messagebox.showerror("Error", "Please select input file and output directory")
            return

        mode = self.proc_mode.get()
        gpus = self.gpu_ids.get().strip()

        cmd = ["python", "-m", "app.core.workers", "--input", infile, "--out", outdir]
        if mode == "cpu":
            cmd.append("--cpu")
        elif mode == "manual" and gpus:
            cmd.extend(["--gpus", gpus])

        self.status_text.set("Running...")
        self._clear_log()
        threading.Thread(target=self._run_subprocess, args=(cmd,), daemon=True).start()

    def merge_results(self):
        outdir = self.out_dir.get()
        if not outdir:
            messagebox.showerror("Error", "Please select output directory")
            return

        subdirs = [os.path.join(outdir, d) for d in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, d))]
        if not subdirs:
            messagebox.showerror("Error", "No chapter output folders found")
            return

        cmd = ["python", "-m", "app.core.merge", "--out", os.path.join(outdir, "merged_out"), "--inputs"] + subdirs

        self.status_text.set("Merging...")
        self._clear_log()
        threading.Thread(target=self._run_subprocess, args=(cmd,), daemon=True).start()

    def _run_subprocess(self, cmd):
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                self._append_log(line.strip())
            proc.wait()
            self.status_text.set("Done")
        except Exception as e:
            self.status_text.set(f"Error: {e}")
            self._append_log(str(e))

    def _append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("PolyVox Studio - Chapter Processing")
    tab = ChapterProcessingTab(root)
    tab.pack(fill="both", expand=True)
    root.mainloop()
