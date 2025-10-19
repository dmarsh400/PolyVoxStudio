<div align="center"><div align="center"># PolyVox Studio

  

# 🎭 PolyVox Studio  



### *Many voices, one story.*# 🎭 PolyVox Studio**Professional Audiobook Generation with AI Voice Synthesis**



[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

[![GPU Support](https://img.shields.io/badge/GPU-CUDA%20%7C%20Legacy-green.svg)](GPU_COMPATIBILITY.md)### *Many voices, one story.**Many voices, one story.*



**Transform your novels into immersive audiobooks with AI-powered character voice cloning**



[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [GPU Support](#-gpu-support) • [Documentation](#-documentation)[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)---



![PolyVox Studio Interface](docs/screenshots/main_interface.png)[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)



</div>[![GPU Support](https://img.shields.io/badge/GPU-CUDA%20%7C%20Legacy-green.svg)](GPU_COMPATIBILITY.md)## 🎙️ Overview



---



## 🎯 What is PolyVox Studio?**Transform your novels into immersive audiobooks with AI-powered character voice cloning**PolyVox Studio is a powerful desktop application for creating professional audiobooks with AI-generated voices. It features:



PolyVox Studio is a powerful desktop application that automatically converts novels and books into professional-quality audiobooks with **distinct AI voices for each character**. Using advanced NLP and voice cloning technology, it:



- 📖 **Automatically detects characters** in your book using BookNLP[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [GPU Support](#-gpu-support) • [Documentation](#-documentation)- **Intelligent Character Detection** - Automatically identifies characters and dialogue

- 🗣️ **Assigns unique voices** to each character (or clone your own!)

- 🎙️ **Generates natural audiobook narration** with character dialogue- **Multi-Voice Support** - Assign different voices to each character and narrator

- ✏️ **Provides full editing control** over character assignments and dialogue

- 🎨 **Offers an intuitive GUI** built with CustomTkinter![PolyVox Studio Interface](docs/screenshots/main_interface.png)- **XTTS v2 Integration** - High-quality voice cloning and synthesis



Whether you're an author wanting to hear your characters come alive, a reader who loves audiobooks, or a content creator producing audio content, PolyVox Studio makes it easy.- **Professional Audio Processing** - Automatic enhancement and normalization



---</div>- **Multi-GPU Support** - Efficient processing with automatic GPU load balancing



## ✨ Features- **Chapter Management** - Smart chapter detection and organization



### 🤖 Intelligent Character Detection---- **Easy Voice Cloning** - Clone voices from audio samples

- **Automatic character identification** using state-of-the-art BookNLP

- **Quote attribution** with speaker detection

- **Coreference resolution** to track character mentions

- **Handles complex narratives** with multiple POVs## 🎯 What is PolyVox Studio?---



### 🎤 Advanced Voice Cloning

- **30+ built-in voices** across multiple accents and styles

- **Clone custom voices** from audio samples (5-15 seconds)PolyVox Studio is a powerful desktop application that automatically converts novels and books into professional-quality audiobooks with **distinct AI voices for each character**. Using advanced NLP and voice cloning technology, it:## 🚀 Quick Start

- **Voice assignment UI** with visual character management

- **Narrator voice** for non-dialogue text



### 📚 Smart Text Processing- 📖 **Automatically detects characters** in your book using BookNLP### Prerequisites

- **Chapter detection** and segmentation

- **Dialogue extraction** with attribution confidence scoring- 🗣️ **Assigns unique voices** to each character (or clone your own!)

- **Handles various book formats** (TXT, EPUB coming soon)

- **BookNLP integration** for literary analysis- 🎙️ **Generates natural audiobook narration** with character dialogue- **Python 3.8+** (3.10 recommended)



### 🎛️ Full Editorial Control- ✏️ **Provides full editing control** over character assignments and dialogue- **8GB+ RAM** (16GB+ recommended)

- **Character merging** for variations (e.g., "John" + "Mr. Smith")

- **Character renaming** to fix detection errors- 🎨 **Offers an intuitive GUI** built with CustomTkinter- **Optional**: NVIDIA GPU with CUDA support for faster processing

- **Line-by-line editing** of speaker assignments

- **Manual voice assignment** override



### ⚡ Performance & CompatibilityWhether you're an author wanting to hear your characters come alive, a reader who loves audiobooks, or a content creator producing audio content, PolyVox Studio makes it easy.### Installation

- **GPU acceleration** (NVIDIA CUDA)

- **Legacy GPU support** for older cards (GTX 700+, K80)

- **CPU fallback mode** for systems without GPU

- **Batch processing** for long books---1. **Clone or download this repository**



### 🎨 Modern Interface   ```bash

- **Dark theme** CustomTkinter UI

- **Real-time progress tracking** with detailed logs## ✨ Features   git clone https://github.com/yourusername/polyvox-studio.git

- **Debug console** for troubleshooting

- **Settings management** with persistent configuration   cd polyvox-studio



---### 🤖 Intelligent Character Detection   ```



## 🚀 Installation- **Automatic character identification** using state-of-the-art BookNLP



PolyVox Studio offers two installation paths depending on your GPU:- **Quote attribution** with speaker detection2. **Run the installer**



### 🔥 Standard Installation- **Coreference resolution** to track character mentions   ```bash

**For modern GPUs (RTX 20xx+, GTX 16xx)**

- **Handles complex narratives** with multiple POVs   python install.py

```bash

# Clone the repository   ```

git clone https://github.com/dmarsh400/PolyVoxStudio.git

cd PolyVoxStudio### 🎤 Advanced Voice Cloning   



# Linux/Mac- **30+ built-in voices** across multiple accents and styles   The installer will:

./install.sh

- **Clone custom voices** from audio samples (5-15 seconds)   - Install all dependencies

# Windows

install.bat- **Voice assignment UI** with visual character management   - Download required language models

```

- **Narrator voice** for non-dialogue text   - Optionally create a desktop icon

**Requirements:**

- Python 3.9 or higher

- NVIDIA GPU with Compute Capability 6.1+

- CUDA 12.1+ drivers### 📚 Smart Text Processing3. **Launch PolyVox Studio**

- 8GB+ VRAM recommended

- **Chapter detection** and segmentation   

### 🐢 Legacy GPU Installation

**For older GPUs (GTX 700-1080, K80)**- **Dialogue extraction** with attribution confidence scoring   **Linux/Mac:**



```bash- **Handles various book formats** (TXT, EPUB coming soon)   ```bash

# Clone the repository

git clone https://github.com/dmarsh400/PolyVoxStudio.git- **BookNLP integration** for literary analysis   ./run_gui.sh

cd PolyVoxStudio

   ```

# Linux/Mac

./install_legacy_gpu.sh### 🎛️ Full Editorial Control   



# Windows- **Character merging** for variations (e.g., "John" + "Mr. Smith")   **Windows:**

install_legacy_gpu.bat

```- **Character renaming** to fix detection errors   ```bash



**Requirements:**- **Line-by-line editing** of speaker assignments   run_gui.bat

- Python 3.9

- NVIDIA GPU with Compute Capability 3.5+- **Manual voice assignment** override   ```

- CUDA 11.6 compatible drivers (450.80.02+)

- 6GB+ VRAM recommended   



👉 **Not sure which installation to use?** Check the [GPU Compatibility Guide](GPU_COMPATIBILITY.md)### ⚡ Performance & Compatibility   Or use the desktop icon if you created one.



### 📦 Dependencies- **GPU acceleration** (NVIDIA CUDA)



Both installations automatically set up:- **Legacy GPU support** for older cards (GTX 700+, K80)---

- **PyTorch** (2.1+ or 1.13 for legacy)

- **Coqui TTS** for voice synthesis- **CPU fallback mode** for systems without GPU

- **BookNLP** for character detection

- **SpaCy** for NLP processing- **Batch processing** for long books## 📚 Features

- **CustomTkinter** for the GUI

- And many more...



---### 🎨 Modern Interface### 1. Book Processing



## 🎬 Quick Start- **Dark theme** CustomTkinter UI- Load `.txt`, `.epub`, or `.pdf` files



### 1️⃣ Launch the Application- **Real-time progress tracking** with detailed logs- Automatic chapter detection



```bash- **Debug console** for troubleshooting- Smart text segmentation

# Standard installation

./run_gui.sh          # Linux/Mac- **Settings management** with persistent configuration

run_gui.bat           # Windows

### 2. Character Detection

# Legacy GPU installation

./run_gui_legacy.sh   # Linux/Mac---- AI-powered character identification

run_gui_legacy.bat    # Windows

```- Dialogue attribution



### 2️⃣ Process Your First Book## 🚀 Installation- Quote extraction



1. **Click "Load Book"** and select your text file- Speaker recognition

2. **Enter book details** (title, author, genre)

3. **Click "Run BookNLP & Attribution"** to detect charactersPolyVox Studio offers two installation paths depending on your GPU:

4. **Review character detection** in the Characters tab

5. **Assign voices** in the Clone Voices tab### 3. Voice Management

6. **Generate audio** in the Settings tab

<table>- Extensive voice library

### 3️⃣ Advanced Workflows

<tr>- Voice cloning from audio samples

#### Merge Character Variations

If "John", "John Smith", and "Mr. Smith" are detected as separate characters:<td width="50%">- Per-character voice assignment

1. Go to **Characters tab**

2. Select all variations- Preview voices before processing

3. Click **"Merge Characters"**

4. Choose which name to keep### 🔥 Standard Installation



#### Clone Custom Voices**For modern GPUs (RTX 20xx+, GTX 16xx)**### 4. Audio Generation

1. Go to **Clone Voices tab**

2. Click **"Upload Audio"** (5-15 second sample)- High-quality XTTS v2 synthesis

3. Enter voice metadata

4. Assign to characters```bash- Multi-voice support



#### Edit Dialogue Attribution# Clone the repository- Automatic audio enhancement

1. Select a character in **Characters tab**

2. View all their dialogue linesgit clone https://github.com/dmarsh400/PolyVoxStudio.git- Progress tracking

3. Click any line to reassign speaker

4. Changes save automaticallycd PolyVoxStudio- Chapter-by-chapter processing



---



## 🖥️ GPU Support# Linux/Mac### 5. GPU Acceleration



PolyVox Studio leverages GPU acceleration for significantly faster processing:./install.sh- Automatic GPU detection



| Task | RTX 3080 | GTX 1080 | K80 | CPU Only |- Multi-GPU load balancing

|------|----------|----------|-----|----------|

| **Character Detection** | 30-60s | 1-2 min | 2-5 min | 5-10 min |# Windows- CPU fallback support

| **Audio Generation** | 15-30s/min | 30-60s/min | 1-2 min/min | 5-10 min/min |

install.bat- Real-time GPU monitoring

### Supported GPUs

```

✅ **Standard Installation:**

- RTX 40 series (4090, 4080, 4070)---

- RTX 30 series (3090, 3080, 3070, 3060)

- RTX 20 series (2080 Ti, 2070, 2060)**Requirements:**

- GTX 16 series (1660 Ti, 1650)

- Python 3.9 or higher## 🎨 Usage

✅ **Legacy Installation:**

- GTX 10 series (1080 Ti, 1070, 1060)- NVIDIA GPU with Compute Capability 6.1+

- GTX 900 series (980 Ti, 970, 960)

- GTX 700 series (780 Ti, 770, 760)- CUDA 12.1+ drivers### Basic Workflow

- Tesla K80, K40

- Quadro K-series- 8GB+ VRAM recommended



📖 **Full compatibility guide:** [GPU_COMPATIBILITY.md](GPU_COMPATIBILITY.md)1. **Load Your Book**



---</td>   - Go to the "Book Processing" tab



## 📖 Documentation<td width="50%">   - Click "Load Book" and select your file



### Core Guides   - Review detected chapters

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions

- [User Guide](docs/USER_GUIDE.md) - Step-by-step usage tutorial### 🐢 Legacy GPU Installation

- [GPU Compatibility](GPU_COMPATIBILITY.md) - Which installation for your GPU

- [Legacy GPU Setup](LEGACY_GPU_INSTALL.md) - Older GPU installation details**For older GPUs (GTX 700-1080, K80)**2. **Detect Characters**



### Technical Documentation   - Switch to the "Characters" tab

- [Architecture Overview](docs/ARCHITECTURE.md) - How PolyVox works

- [Character Detection](docs/CHARACTER_DETECTION.md) - BookNLP integration details```bash   - Click "Detect Characters"

- [Voice Cloning](docs/VOICE_CLONING.md) - TTS and voice synthesis

- [API Reference](docs/API.md) - For developers and contributors# Clone the repository   - Review identified characters and dialogue



### Troubleshootinggit clone https://github.com/dmarsh400/PolyVoxStudio.git

- [FAQ](docs/FAQ.md) - Common questions and answers

- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Fix common issuescd PolyVoxStudio3. **Assign Voices**

- [Performance Tuning](docs/PERFORMANCE.md) - Optimize for your system

   - Go to the "Voices" tab

---

# Linux/Mac   - Assign a voice to each character

## 🛠️ System Requirements

./install_legacy_gpu.sh   - Preview voices before finalizing

### Minimum Requirements

- **OS:** Windows 10+, Linux (Ubuntu 20.04+), macOS 11+

- **CPU:** 4-core processor (Intel i5 / AMD Ryzen 5 or better)

- **RAM:** 8GB (16GB recommended)# Windows4. **Generate Audio**

- **Storage:** 10GB free space (models + workspace)

- **GPU:** NVIDIA GPU with 6GB VRAM (optional but recommended)install_legacy_gpu.bat   - Switch to "Audio Processing" tab



### Recommended for Best Experience```   - Click "Generate Audio"

- **CPU:** 8-core processor (Intel i7/i9 or AMD Ryzen 7/9)

- **RAM:** 16GB or more   - Wait for processing to complete

- **GPU:** RTX 3060 or better with 12GB+ VRAM

- **Storage:** SSD with 20GB+ free space**Requirements:**   - Find your audiobook in the `output_audio/` folder



---- Python 3.9



## 🎨 Screenshots- NVIDIA GPU with Compute Capability 3.5+### Advanced Features



<div align="center">- CUDA 11.6 compatible drivers (450.80.02+)



### Main Interface- 6GB+ VRAM recommended#### Voice Cloning

![Main Interface](docs/screenshots/main_interface.png)

1. Go to "Clone Voices" tab

### Character Detection

![Character Detection](docs/screenshots/characters_tab.png)</td>2. Record or upload a 10-30 second audio sample



### Voice Assignment</tr>3. Enter voice details

![Voice Cloning](docs/screenshots/clone_voices_tab.png)

</table>4. Click "Save Voice"

### Settings & Configuration

![Settings](docs/screenshots/settings_tab.png)5. Use the cloned voice like any other voice



</div>👉 **Not sure which installation to use?** Check the [GPU Compatibility Guide](GPU_COMPATIBILITY.md)



---#### Chapter-by-Chapter Processing



## 🤝 Contributing### 📦 Dependencies- Process large books one chapter at a time



We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation, your help makes PolyVox better.- Each chapter is processed independently



### How to ContributeBoth installations automatically set up:- No cross-contamination between chapters

1. Fork the repository

2. Create a feature branch (`git checkout -b feature/AmazingFeature`)- **PyTorch** (2.1+ or 1.13 for legacy)

3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)

4. Push to the branch (`git push origin feature/AmazingFeature`)- **Coqui TTS** for voice synthesis---

5. Open a Pull Request

- **BookNLP** for character detection

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

- **SpaCy** for NLP processing## ⚙️ Configuration

### Development Setup

```bash- **CustomTkinter** for the GUI

# Clone your fork

git clone https://github.com/YOUR_USERNAME/PolyVoxStudio.git- And many more...### GPU Setup

cd PolyVoxStudio



# Install in development mode

pip install -e .---PolyVox Studio automatically detects and uses available GPUs. To force CPU mode:



# Run tests

python -m pytest tests/

```## 🎬 Quick StartEdit `run_gui.sh` (Linux/Mac) or `run_gui.bat` (Windows):



---```bash



## 📜 License### 1️⃣ Launch the Applicationexport CUDA_VISIBLE_DEVICES=""  # Force CPU mode



This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.```



### Third-Party Licenses```bash

- **BookNLP** - Apache 2.0 License

- **Coqui TTS** - Mozilla Public License 2.0# Standard installation### Audio Quality

- **PyTorch** - BSD-style License

- **SpaCy** - MIT License./run_gui.sh          # Linux/Mac



---run_gui.bat           # WindowsAudio enhancement requires FFmpeg. Install it:



## 🙏 Acknowledgments



PolyVox Studio is built on the shoulders of giants:# Legacy GPU installation**Linux:**



- **[BookNLP](https://github.com/booknlp/booknlp)** by David Bamman - Character detection and literary NLP./run_gui_legacy.sh   # Linux/Mac```bash

- **[Coqui TTS](https://github.com/coqui-ai/TTS)** - High-quality voice synthesis

- **[XTTS v2](https://huggingface.co/coqui/XTTS-v2)** - Multilingual voice cloningrun_gui_legacy.bat    # Windowssudo apt install ffmpeg

- **[PyTorch](https://pytorch.org/)** - Deep learning framework

- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern GUI framework``````



Special thanks to all contributors and the open-source community!



---### 2️⃣ Process Your First Book**Mac:**



## 📞 Support```bash



### Get Help1. **Click "Load Book"** and select your text filebrew install ffmpeg

- 📖 Check the [Documentation](docs/)

- ❓ Read the [FAQ](docs/FAQ.md)2. **Enter book details** (title, author, genre)```

- 🐛 Report bugs via [Issues](https://github.com/dmarsh400/PolyVoxStudio/issues)

- 💬 Join discussions in [Discussions](https://github.com/dmarsh400/PolyVoxStudio/discussions)3. **Click "Run BookNLP & Attribution"** to detect characters



### Stay Updated4. **Review character detection** in the Characters tab**Windows:**

- ⭐ Star this repository to stay notified

- 👁️ Watch for updates and releases5. **Assign voices** in the Clone Voices tabDownload from [ffmpeg.org](https://ffmpeg.org/download.html)

- 🍴 Fork to create your own version

6. **Generate audio** in the Settings tab

---

---

## 🗺️ Roadmap

### 3️⃣ Advanced Workflows

### Coming Soon

- [ ] EPUB file support## 📖 System Requirements

- [ ] Audio export formats (M4B, OGG)

- [ ] Batch processing multiple books#### Merge Character Variations

- [ ] Cloud rendering options

- [ ] Mobile companion appIf "John", "John Smith", and "Mr. Smith" are detected as separate characters:### Minimum



### Future Enhancements1. Go to **Characters tab**- Python 3.8+

- [ ] Emotional tone detection for voice modulation

- [ ] Multi-language support2. Select all variations- 8GB RAM

- [ ] Advanced audio post-processing

- [ ] Character voice training from book descriptions3. Click **"Merge Characters"**- 10GB free disk space

- [ ] API for programmatic access

4. Choose which name to keep- CPU: Multi-core processor

---



<div align="center">

#### Clone Custom Voices### Recommended

**Made with ❤️ by the PolyVox team**

1. Go to **Clone Voices tab**- Python 3.10+

[⬆ Back to Top](#-polyvox-studio)

2. Click **"Upload Audio"** (5-15 second sample)- 16GB+ RAM

</div>

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
