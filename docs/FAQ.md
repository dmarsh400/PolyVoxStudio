# Frequently Asked Questions (FAQ)

## 📚 General Questions

### What is PolyVox Studio?
PolyVox Studio is an AI-powered desktop application that converts novels into audiobooks with unique voices for each character. It uses BookNLP for character detection and Coqui TTS for voice synthesis.

### Is PolyVox Studio free?
Yes! PolyVox Studio is open-source and free to use under the MIT License.

### What file formats are supported?
PolyVox Studio currently accepts `.txt`, `.pdf`, and `.epub` manuscripts. Additional formats are on the roadmap.

### Do I need a GPU?
No—both installers let you pick a CPU-only runtime. That said, GPU processing is typically 5–10× faster. See [GPU_COMPATIBILITY.md](../GPU_COMPATIBILITY.md) for driver guidance when choosing the CUDA 11.8 or 12.1 options.

---

## 🔧 Installation & Setup

### Which installation should I use?
- **Linux:** Run `install_linux.sh` and choose the CUDA 12.1, CUDA 11.8, or CPU option that matches your GPU/driver.
- **Windows:** Double-click (or run) `install_windows.bat`; the PowerShell installer will prompt for the same runtime choice.
- **Unsure?** Start with CPU to get running, then rerun the installer later to switch runtimes after confirming driver support.

See [GPU_COMPATIBILITY.md](../GPU_COMPATIBILITY.md) for help picking the right CUDA option.

### Installation failed. What should I do?
1. Confirm Python 3.9+ is on your PATH: `python --version` (or `py --version` on Windows).
2. Run the platform installer from the project root (`./install_linux.sh` or `install_windows.bat`) so relative paths resolve.
3. Review the console output for the first error message—wheel downloads and spaCy model installs are the most common culprits.
4. Consult [`INSTALL_LINUX.md`](INSTALL_LINUX.md) or [`INSTALL_WINDOWS.md`](INSTALL_WINDOWS.md) for troubleshooting tips (proxy settings, driver notes, system packages).
5. Still stuck? Open a GitHub issue and attach the full console log.

### Can I change my GPU runtime later?
Yes. Delete the `PolyVox` folder (or let the installer recreate it) and rerun `install_linux.sh` / `install_windows.bat`, choosing a different CUDA or CPU option when prompted.

### How much disk space do I need?
- **Initial installation:** ~5-8 GB (models + dependencies)
- **Per book processed:** 100-500 MB (depends on book length)
- **Recommended:** 20 GB free space for comfortable usage

---

## 🎭 Character Detection

### Why are some characters not detected?
Character detection depends on:
- Character appearing in dialogue or narration
- Having a name (pronouns alone aren't enough)
- BookNLP's NLP model accuracy

**Tip:** You can manually add missing characters in the Characters tab.

### Characters are split (e.g., "John" and "John Smith")
This is normal! Use the **Merge Characters** feature:
1. Go to Characters tab
2. Select all variations (Ctrl+Click)
3. Click "Merge Characters"
4. Choose which name to keep

### Can I rename a character?
Yes! Use the **Rename Character** button in the Characters tab:
1. Select the character
2. Click "Rename Character"
3. Enter the new name
4. All dialogue lines will be updated

### Why does the Narrator have dialogue?
Sometimes attribution isn't perfect. You can:
- Reassign lines to the correct character
- Adjust the attribution confidence threshold in Settings
- Review and edit in the Characters tab

---

## 🎤 Voice Cloning

### How long should my voice sample be?
**5-15 seconds** is ideal. Longer samples don't necessarily improve quality and may slow processing.

### What makes a good voice sample?
- Clear audio with no background noise
- Natural speech (not shouting or whispering)
- Multiple sentences with varied intonation
- 22050 Hz sample rate (converted automatically if different)

### Can I use my own voice?
Absolutely! Record a 10-second sample of yourself reading, upload it in the Clone Voices tab, and assign it to any character.

### How many voices can I clone?
You can clone **30 custom voices** (this is a UI limitation, not a technical one). Plus, there are 30+ built-in voices available.

### Voice quality is poor. What can I do?
- Use a better quality audio sample
- Ensure sample is 5-15 seconds
- Remove background noise
- Try a different built-in voice for comparison
- Check that GPU acceleration is enabled

---

## ⚡ Performance & GPU

### How fast is audiobook generation?
Depends on your GPU:
- **RTX 3080:** ~15-30 seconds per minute of audio
- **GTX 1080:** ~30-60 seconds per minute of audio
- **K80:** ~1-2 minutes per minute of audio
- **CPU only:** ~5-10 minutes per minute of audio

### My GPU isn't being detected
1. Check that NVIDIA drivers are installed: `nvidia-smi`
2. Verify CUDA is available: In Python, run:
   ```python
   import torch
   print(torch.cuda.is_available())
   ```
3. Rerun the installer and pick the CUDA 11.8 option (or CPU) if your card predates Ampere/RTX 30-series.
4. Check [GPU_COMPATIBILITY.md](../GPU_COMPATIBILITY.md)

### I'm getting "CUDA out of memory" errors
Reduce memory usage:
1. Go to Settings tab
2. Lower "Batch Size" (try 16 or 8)
3. Close other GPU-intensive applications
4. For very old GPUs, consider CPU mode

### Can I use AMD GPUs?
Currently, no. PolyVox Studio requires NVIDIA CUDA. AMD ROCm support may be added in the future.

---

## 📖 Book Processing

### How long does processing take?
For a typical 300-page novel:
- **Character Detection:** 10-30 minutes (GPU) or 1-2 hours (CPU)
- **Audio Generation:** 2-6 hours (GPU) or 10-20 hours (CPU)

### Can I process multiple books simultaneously?
Not currently within the same instance. You can run multiple instances of PolyVox Studio in separate terminals.

### The application froze. What happened?
Long processing tasks can appear frozen. Check:
1. The Debug tab for progress messages
2. CPU/GPU usage (should be high if processing)
3. The progress bar (may update slowly for large books)

**Tip:** First-time GPU use may have a 1-2 minute delay for JIT compilation.

### Can I pause and resume processing?
Not currently. Processing must complete or be cancelled. This feature is on the roadmap.

---

## 🔊 Audio Output

### What audio format is the output?
Currently WAV format. MP3, M4B, and OGG support are planned.

### Where are the audio files saved?
- **Default:** `output/audio/` directory
- **Per-character files:** `output/audio/[character_name]/`
- **Full audiobook:** Combined file in `output/audio/` (if enabled)

### Can I adjust audio quality?
Yes, in the Settings tab:
- Sample rate (default: 22050 Hz)
- Bit depth
- Encoding quality

### Audio has strange pauses or pacing
This can happen with complex punctuation. Try:
- Reviewing the text in Characters tab
- Manually adjusting dialogue breaks
- Adjusting TTS speed settings (coming soon)

---

## 🛠️ Troubleshooting

### "Module not found" errors
Activate the PolyVox virtual environment first:
```bash
# Linux / macOS
source PolyVox/bin/activate

# Windows (PowerShell)
./PolyVox/Scripts/Activate.ps1
```

### Application won't start
1. Check Python version: `python --version` (should be 3.9+)
2. Activate the `PolyVox` environment (see above)
3. Launch with `./run_gui.sh` (Linux/macOS) or `./run_gui.bat` (Windows) and watch the terminal for errors
4. If dependencies are missing, rerun the installer (`install_linux.sh` or `install_windows.bat`) and let it recreate the environment

### BookNLP model download failed
- Check your internet connection
- Try manually downloading from [BookNLP releases](https://github.com/booknlp/booknlp/releases)
- Place in `models/` directory

### Changes aren't saving
- Check file permissions in the project directory
- Ensure you're not running multiple instances
- Look for error messages in the Debug tab

---

## 🤝 Contributing & Support

### How can I contribute?
See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines. Contributions welcome!

### I found a bug. Where do I report it?
Open a [GitHub Issue](https://github.com/dmarsh400/PolyVoxStudio/issues) with:
- Bug description
- Steps to reproduce
- System information
- Debug log output

### Can I request a feature?
Yes! Open a [Feature Request](https://github.com/dmarsh400/PolyVoxStudio/issues/new?template=feature_request.md) or start a [Discussion](https://github.com/dmarsh400/PolyVoxStudio/discussions).

### How do I get help?
1. Check this FAQ
2. Read the [documentation](README.md)
3. Search [existing issues](https://github.com/dmarsh400/PolyVoxStudio/issues)
4. Open a new issue or discussion

---

## 📜 Legal & Licensing

### Can I use PolyVox Studio commercially?
Yes, under the MIT License. However, check the licenses of:
- The books you're processing (copyright)
- Voice samples you're cloning (permissions)
- Third-party models (BookNLP, TTS)

### Can I distribute audiobooks I create?
Only if you have rights to the source material. Respect copyright laws.

### Can I modify and redistribute PolyVox Studio?
Yes! Under the MIT License. See [LICENSE](../LICENSE) for details.

---

## 🔮 Roadmap & Future Features

### What features are planned?
- EPUB file support
- Multiple audio formats (MP3, M4B)
- Emotional tone detection
- Multi-language support
- Cloud rendering options
- Mobile companion app

See the [Roadmap](../README.md#-roadmap) in the main README.

### How can I vote on features?
- ⭐ Star feature requests you want
- 💬 Comment with your use case
- 👍 React to issues with thumbs up

---

**Still have questions?** Open a [Discussion](https://github.com/dmarsh400/PolyVoxStudio/discussions) or [Issue](https://github.com/dmarsh400/PolyVoxStudio/issues)!
