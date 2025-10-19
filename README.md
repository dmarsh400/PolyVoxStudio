<div align="center"># PolyVox Studio

  

# 🎭 PolyVox Studio**Professional Audiobook Generation with AI Voice Synthesis**



### *Many voices, one story.**Many voices, one story.*



[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)---

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

[![GPU Support](https://img.shields.io/badge/GPU-CUDA%20%7C%20Legacy-green.svg)](GPU_COMPATIBILITY.md)## 🎙️ Overview



**Transform your novels into immersive audiobooks with AI-powered character voice cloning**PolyVox Studio is a powerful desktop application for creating professional audiobooks with AI-generated voices. It features:



[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [GPU Support](#-gpu-support) • [Documentation](#-documentation)- **Intelligent Character Detection** - Automatically identifies characters and dialogue

- **Multi-Voice Support** - Assign different voices to each character and narrator

![PolyVox Studio Interface](docs/screenshots/main_interface.png)- **XTTS v2 Integration** - High-quality voice cloning and synthesis

- **Professional Audio Processing** - Automatic enhancement and normalization

</div>- **Multi-GPU Support** - Efficient processing with automatic GPU load balancing

- **Chapter Management** - Smart chapter detection and organization

---- **Easy Voice Cloning** - Clone voices from audio samples



## 🎯 What is PolyVox Studio?---



PolyVox Studio is a powerful desktop application that automatically converts novels and books into professional-quality audiobooks with **distinct AI voices for each character**. Using advanced NLP and voice cloning technology, it:## 🚀 Quick Start



- 📖 **Automatically detects characters** in your book using BookNLP### Prerequisites

- 🗣️ **Assigns unique voices** to each character (or clone your own!)

- 🎙️ **Generates natural audiobook narration** with character dialogue- **Python 3.8+** (3.10 recommended)

- ✏️ **Provides full editing control** over character assignments and dialogue- **8GB+ RAM** (16GB+ recommended)

- 🎨 **Offers an intuitive GUI** built with CustomTkinter- **Optional**: NVIDIA GPU with CUDA support for faster processing



Whether you're an author wanting to hear your characters come alive, a reader who loves audiobooks, or a content creator producing audio content, PolyVox Studio makes it easy.### Installation



---1. **Clone or download this repository**

   ```bash

## ✨ Features   git clone https://github.com/yourusername/polyvox-studio.git

   cd polyvox-studio

### 🤖 Intelligent Character Detection   ```

- **Automatic character identification** using state-of-the-art BookNLP

- **Quote attribution** with speaker detection2. **Run the installer**

- **Coreference resolution** to track character mentions   ```bash

- **Handles complex narratives** with multiple POVs   python install.py

   ```

### 🎤 Advanced Voice Cloning   

- **30+ built-in voices** across multiple accents and styles   The installer will:

- **Clone custom voices** from audio samples (5-15 seconds)   - Install all dependencies

- **Voice assignment UI** with visual character management   - Download required language models

- **Narrator voice** for non-dialogue text   - Optionally create a desktop icon



### 📚 Smart Text Processing3. **Launch PolyVox Studio**

- **Chapter detection** and segmentation   

- **Dialogue extraction** with attribution confidence scoring   **Linux/Mac:**

- **Handles various book formats** (TXT, EPUB coming soon)   ```bash

- **BookNLP integration** for literary analysis   ./run_gui.sh

   ```

### 🎛️ Full Editorial Control   

- **Character merging** for variations (e.g., "John" + "Mr. Smith")   **Windows:**

- **Character renaming** to fix detection errors   ```bash

- **Line-by-line editing** of speaker assignments   run_gui.bat

- **Manual voice assignment** override   ```

   

### ⚡ Performance & Compatibility   Or use the desktop icon if you created one.

- **GPU acceleration** (NVIDIA CUDA)

- **Legacy GPU support** for older cards (GTX 700+, K80)---

- **CPU fallback mode** for systems without GPU

- **Batch processing** for long books## 📚 Features



### 🎨 Modern Interface### 1. Book Processing

- **Dark theme** CustomTkinter UI- Load `.txt`, `.epub`, or `.pdf` files

- **Real-time progress tracking** with detailed logs- Automatic chapter detection

- **Debug console** for troubleshooting- Smart text segmentation

- **Settings management** with persistent configuration

### 2. Character Detection

---- AI-powered character identification

- Dialogue attribution

## 🚀 Installation- Quote extraction

- Speaker recognition

PolyVox Studio offers two installation paths depending on your GPU:

### 3. Voice Management

<table>- Extensive voice library

<tr>- Voice cloning from audio samples

<td width="50%">- Per-character voice assignment

- Preview voices before processing

### 🔥 Standard Installation

**For modern GPUs (RTX 20xx+, GTX 16xx)**### 4. Audio Generation

- High-quality XTTS v2 synthesis

```bash- Multi-voice support

# Clone the repository- Automatic audio enhancement

git clone https://github.com/dmarsh400/PolyVoxStudio.git- Progress tracking

cd PolyVoxStudio- Chapter-by-chapter processing



# Linux/Mac### 5. GPU Acceleration

./install.sh- Automatic GPU detection

- Multi-GPU load balancing

# Windows- CPU fallback support

install.bat- Real-time GPU monitoring

```

---

**Requirements:**

- Python 3.9 or higher## 🎨 Usage

- NVIDIA GPU with Compute Capability 6.1+

- CUDA 12.1+ drivers### Basic Workflow

- 8GB+ VRAM recommended

1. **Load Your Book**

</td>   - Go to the "Book Processing" tab

<td width="50%">   - Click "Load Book" and select your file

   - Review detected chapters

### 🐢 Legacy GPU Installation

**For older GPUs (GTX 700-1080, K80)**2. **Detect Characters**

   - Switch to the "Characters" tab

```bash   - Click "Detect Characters"

# Clone the repository   - Review identified characters and dialogue

git clone https://github.com/dmarsh400/PolyVoxStudio.git

cd PolyVoxStudio3. **Assign Voices**

   - Go to the "Voices" tab

# Linux/Mac   - Assign a voice to each character

./install_legacy_gpu.sh   - Preview voices before finalizing



# Windows4. **Generate Audio**

install_legacy_gpu.bat   - Switch to "Audio Processing" tab

```   - Click "Generate Audio"

   - Wait for processing to complete

**Requirements:**   - Find your audiobook in the `output_audio/` folder

- Python 3.9

- NVIDIA GPU with Compute Capability 3.5+### Advanced Features

- CUDA 11.6 compatible drivers (450.80.02+)

- 6GB+ VRAM recommended#### Voice Cloning

1. Go to "Clone Voices" tab

</td>2. Record or upload a 10-30 second audio sample

</tr>3. Enter voice details

</table>4. Click "Save Voice"

5. Use the cloned voice like any other voice

👉 **Not sure which installation to use?** Check the [GPU Compatibility Guide](GPU_COMPATIBILITY.md)

#### Chapter-by-Chapter Processing

### 📦 Dependencies- Process large books one chapter at a time

- Each chapter is processed independently

Both installations automatically set up:- No cross-contamination between chapters

- **PyTorch** (2.1+ or 1.13 for legacy)

- **Coqui TTS** for voice synthesis---

- **BookNLP** for character detection

- **SpaCy** for NLP processing## ⚙️ Configuration

- **CustomTkinter** for the GUI

- And many more...### GPU Setup



---PolyVox Studio automatically detects and uses available GPUs. To force CPU mode:



## 🎬 Quick StartEdit `run_gui.sh` (Linux/Mac) or `run_gui.bat` (Windows):

```bash

### 1️⃣ Launch the Applicationexport CUDA_VISIBLE_DEVICES=""  # Force CPU mode

```

```bash

# Standard installation### Audio Quality

./run_gui.sh          # Linux/Mac

run_gui.bat           # WindowsAudio enhancement requires FFmpeg. Install it:



# Legacy GPU installation**Linux:**

./run_gui_legacy.sh   # Linux/Mac```bash

run_gui_legacy.bat    # Windowssudo apt install ffmpeg

``````



### 2️⃣ Process Your First Book**Mac:**

```bash

1. **Click "Load Book"** and select your text filebrew install ffmpeg

2. **Enter book details** (title, author, genre)```

3. **Click "Run BookNLP & Attribution"** to detect characters

4. **Review character detection** in the Characters tab**Windows:**

5. **Assign voices** in the Clone Voices tabDownload from [ffmpeg.org](https://ffmpeg.org/download.html)

6. **Generate audio** in the Settings tab

---

### 3️⃣ Advanced Workflows

## 📖 System Requirements

#### Merge Character Variations

If "John", "John Smith", and "Mr. Smith" are detected as separate characters:### Minimum

1. Go to **Characters tab**- Python 3.8+

2. Select all variations- 8GB RAM

3. Click **"Merge Characters"**- 10GB free disk space

4. Choose which name to keep- CPU: Multi-core processor



#### Clone Custom Voices### Recommended

1. Go to **Clone Voices tab**- Python 3.10+

2. Click **"Upload Audio"** (5-15 second sample)- 16GB+ RAM

3. Enter voice metadata- 20GB+ free disk space

4. Assign to characters- NVIDIA GPU with 8GB+ VRAM

- CUDA 11.8 or higher

#### Edit Dialogue Attribution

1. Select a character in **Characters tab**---

2. View all their dialogue lines

3. Click any line to reassign speaker## 🛠️ Troubleshooting

4. Changes save automatically

### Common Issues

---

**Issue:** "ModuleNotFoundError: No module named 'XXX'"

## 🖥️ GPU Support**Solution:** Run `python install.py` again or `pip install -r requirements_min.txt`



PolyVox Studio leverages GPU acceleration for significantly faster processing:**Issue:** Slow processing

**Solution:** Check GPU is being used. Install CUDA if you have NVIDIA GPU.

| Task | RTX 3080 | GTX 1080 | K80 | CPU Only |

|------|----------|----------|-----|----------|**Issue:** Audio quality is poor

| **Character Detection** | 30-60s | 1-2 min | 2-5 min | 5-10 min |**Solution:** Install FFmpeg for audio enhancement

| **Audio Generation** | 15-30s/min | 30-60s/min | 1-2 min/min | 5-10 min/min |

**Issue:** Chapter detection creates parts

### Supported GPUs**Solution:** Run `./clear_chapter_cache.sh` and re-detect chapters



✅ **Standard Installation:****Issue:** Characters not detected properly

- RTX 40 series (4090, 4080, 4070)**Solution:** Process chapters individually for better results

- RTX 30 series (3090, 3080, 3070, 3060)

- RTX 20 series (2080 Ti, 2070, 2060)---

- GTX 16 series (1660 Ti, 1650)

## 📝 File Structure

✅ **Legacy Installation:**

- GTX 10 series (1080 Ti, 1070, 1060)```

- GTX 900 series (980 Ti, 970, 960)polyvox-studio/

- GTX 700 series (780 Ti, 770, 760)├── app/                    # Main application code

- Tesla K80, K40│   ├── core/              # Core processing logic

- Quadro K-series│   ├── engine/            # TTS engines

│   └── ui/                # User interface

📖 **Full compatibility guide:** [GPU_COMPATIBILITY.md](GPU_COMPATIBILITY.md)├── assets/                # Application assets

│   └── polyvox_splash.png

---├── output/                # BookNLP processing output

├── output_audio/          # Generated audiobooks

## 📖 Documentation├── voices/                # Voice sample library

├── cleaned/               # Archive of dev files

### Core Guides├── requirements_min.txt   # Python dependencies

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions├── install.py             # Installation script

- [User Guide](docs/USER_GUIDE.md) - Step-by-step usage tutorial├── run_gui.sh             # Launch script (Linux/Mac)

- [GPU Compatibility](GPU_COMPATIBILITY.md) - Which installation for your GPU├── run_gui.bat            # Launch script (Windows)

- [Legacy GPU Setup](LEGACY_GPU_INSTALL.md) - Older GPU installation details└── USER_GUIDE.pdf         # Comprehensive user guide

```

### Technical Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - How PolyVox works---

- [Character Detection](docs/CHARACTER_DETECTION.md) - BookNLP integration details

- [Voice Cloning](docs/VOICE_CLONING.md) - TTS and voice synthesis## 🤝 Contributing

- [API Reference](docs/API.md) - For developers and contributors

Contributions are welcome! Please:

### Troubleshooting

- [FAQ](docs/FAQ.md) - Common questions and answers1. Fork the repository

- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Fix common issues2. Create a feature branch

- [Performance Tuning](docs/PERFORMANCE.md) - Optimize for your system3. Make your changes

4. Submit a pull request

---

---

## 🛠️ System Requirements

## 📄 License

### Minimum Requirements

- **OS:** Windows 10+, Linux (Ubuntu 20.04+), macOS 11+[Choose your license - MIT, GPL, etc.]

- **CPU:** 4-core processor (Intel i5 / AMD Ryzen 5 or better)

- **RAM:** 8GB (16GB recommended)---

- **Storage:** 10GB free space (models + workspace)

- **GPU:** NVIDIA GPU with 6GB VRAM (optional but recommended)## 🙏 Acknowledgments



### Recommended for Best Experience- **Coqui TTS** - XTTS v2 voice synthesis

- **CPU:** 8-core processor (Intel i7/i9 or AMD Ryzen 7/9)- **BookNLP** - Character and dialogue detection

- **RAM:** 16GB or more- **CustomTkinter** - Modern GUI framework

- **GPU:** RTX 3060 or better with 12GB+ VRAM- **Transformers** - NLP models

- **Storage:** SSD with 20GB+ free space- All open-source contributors



------



## 🎨 Screenshots## 📧 Support



<div align="center">- **Issues**: [GitHub Issues](https://github.com/yourusername/polyvox-studio/issues)

- **Discussions**: [GitHub Discussions](https://github.com/yourusername/polyvox-studio/discussions)

### Main Interface- **Documentation**: See `USER_GUIDE.pdf`

![Main Interface](docs/screenshots/main_interface.png)

---

### Character Detection

![Character Detection](docs/screenshots/characters_tab.png)## 🎉 Features Coming Soon



### Voice Assignment- [ ] Azure voice synthesis support

![Voice Cloning](docs/screenshots/clone_voices_tab.png)- [ ] Real-time voice preview

- [ ] Batch processing multiple books

### Settings & Configuration- [ ] Audio editing tools

![Settings](docs/screenshots/settings_tab.png)- [ ] Export to various formats

- [ ] Cloud rendering support

</div>

---

---

**PolyVox Studio** - Turn your books into audiobooks with many voices, one story. 🎙️📚

## 🤝 Contributing

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation, your help makes PolyVox better.

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Development Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/PolyVoxStudio.git
cd PolyVoxStudio

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses
- **BookNLP** - Apache 2.0 License
- **Coqui TTS** - Mozilla Public License 2.0
- **PyTorch** - BSD-style License
- **SpaCy** - MIT License

---

## 🙏 Acknowledgments

PolyVox Studio is built on the shoulders of giants:

- **[BookNLP](https://github.com/booknlp/booknlp)** by David Bamman - Character detection and literary NLP
- **[Coqui TTS](https://github.com/coqui-ai/TTS)** - High-quality voice synthesis
- **[XTTS v2](https://huggingface.co/coqui/XTTS-v2)** - Multilingual voice cloning
- **[PyTorch](https://pytorch.org/)** - Deep learning framework
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern GUI framework

Special thanks to all contributors and the open-source community!

---

## 📞 Support

### Get Help
- 📖 Check the [Documentation](docs/)
- ❓ Read the [FAQ](docs/FAQ.md)
- 🐛 Report bugs via [Issues](https://github.com/dmarsh400/PolyVoxStudio/issues)
- 💬 Join discussions in [Discussions](https://github.com/dmarsh400/PolyVoxStudio/discussions)

### Stay Updated
- ⭐ Star this repository to stay notified
- 👁️ Watch for updates and releases
- 🍴 Fork to create your own version

---

## 🗺️ Roadmap

### Coming Soon
- [ ] EPUB file support
- [ ] Audio export formats (M4B, OGG)
- [ ] Batch processing multiple books
- [ ] Cloud rendering options
- [ ] Mobile companion app

### Future Enhancements
- [ ] Emotional tone detection for voice modulation
- [ ] Multi-language support
- [ ] Advanced audio post-processing
- [ ] Character voice training from book descriptions
- [ ] API for programmatic access

---

<div align="center">

**Made with ❤️ by the PolyVox team**

[⬆ Back to Top](#-polyvox-studio)

</div>
