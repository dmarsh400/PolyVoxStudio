# Contributing to PolyVox Studio# Contributing to PolyVox Studio



Thank you for considering contributing to PolyVox Studio! This document provides guidelines and instructions for contributing.Thank you for your interest in contributing to PolyVox Studio! This document provides guidelines for contributing to the project.



## 🎯 How Can I Contribute?## Ways to Contribute



### Reporting Bugs- 🐛 **Report Bugs**: Submit detailed bug reports with reproduction steps

- Use the GitHub Issues page- 💡 **Suggest Features**: Propose new features or enhancements

- Check if the bug has already been reported- 📝 **Improve Documentation**: Fix typos, clarify instructions, add examples

- Include detailed steps to reproduce- 🔧 **Submit Code**: Fix bugs or implement new features

- Provide system information (OS, GPU, Python version)- 🎨 **Enhance UI**: Improve user interface and experience

- Attach relevant log files from the Debug tab- 🧪 **Add Tests**: Increase test coverage

- 🌍 **Translations**: Help translate the application

### Suggesting Features

- Open a GitHub Discussion for feature requests## Getting Started

- Explain the use case and expected behavior

- Consider backward compatibility1. **Fork the repository** on GitHub

2. **Clone your fork** locally:

### Submitting Code   ```bash

- Fork the repository   git clone https://github.com/your-username/polyvox-studio.git

- Create a feature branch   cd polyvox-studio

- Write clear commit messages   ```

- Add tests for new functionality3. **Create a branch** for your changes:

- Update documentation as needed   ```bash

   git checkout -b feature/your-feature-name

## 🛠️ Development Setup   ```

4. **Make your changes** and test thoroughly

### Prerequisites5. **Commit your changes**:

- Python 3.9+   ```bash

- Git   git commit -m "Add: brief description of changes"

- NVIDIA GPU (optional but recommended)   ```

- Conda or virtualenv6. **Push to your fork**:

   ```bash

### Setup Steps   git push origin feature/your-feature-name

   ```

```bash7. **Submit a Pull Request** on GitHub

# Clone your fork

git clone https://github.com/YOUR_USERNAME/PolyVoxStudio.git## Development Setup

cd PolyVoxStudio

1. Install Python 3.10 or higher

# Create development environment2. Install dependencies:

conda create -n polyvox_dev python=3.9   ```bash

conda activate polyvox_dev   pip install -r requirements_min.txt

   pip install -r requirements_dev.txt  # Development dependencies

# Install dependencies   ```

pip install -r requirements.txt3. Install spaCy model:

   ```bash

# Install development dependencies   python -m spacy download en_core_web_sm

pip install pytest black flake8 mypy   ```

4. Run the application:

# Run in development mode   ```bash

python app/main.py   python -m app.main

```   ```



## 📝 Code Style## Code Standards



### Python Code### Python Style

- Follow PEP 8 style guide

- Use type hints where applicable- Follow **PEP 8** style guidelines

- Maximum line length: 120 characters- Use **4 spaces** for indentation (no tabs)

- Use docstrings for functions and classes- Maximum line length: **100 characters**

- Use descriptive variable names

```python- Add docstrings to functions and classes

def process_character(name: str, confidence: float) -> Dict[str, Any]:

    """### Code Example

    Process a detected character.

    ```python

    Args:def detect_characters(text: str, config: dict) -> list:

        name: Character name from BookNLP    """

        confidence: Detection confidence score (0.0-1.0)    Detect characters in the provided text.

            

    Returns:    Args:

        Dictionary with processed character data        text: The input text to analyze

    """        config: Configuration dictionary with detection parameters

    pass        

```    Returns:

        List of detected character dictionaries

### Code Formatting    """

We use `black` for automatic code formatting:    # Implementation here

    pass

```bash```

# Format all Python files

black app/ tools/ tests/### Naming Conventions



# Check without modifying- **Functions/Variables**: `snake_case`

black --check app/- **Classes**: `PascalCase`

```- **Constants**: `UPPER_SNAKE_CASE`

- **Private methods**: `_leading_underscore`

### Linting

Run `flake8` before committing:## Testing



```bashBefore submitting your changes:

flake8 app/ tools/ tests/ --max-line-length=120

```1. **Test your changes manually** in the GUI

2. **Run existing tests** (if available):

## 🧪 Testing   ```bash

   pytest tests/

### Running Tests   ```

```bash3. **Test on different platforms** if possible (Windows, Linux, Mac)

# Run all tests4. **Check for errors** in the Debug tab

pytest tests/

## Pull Request Guidelines

# Run specific test file

pytest tests/test_character_detection.py### Before Submitting



# Run with coverage- [ ] Code follows the project's style guidelines

pytest --cov=app tests/- [ ] Changes have been tested thoroughly

```- [ ] Documentation has been updated if needed

- [ ] Commit messages are clear and descriptive

### Writing Tests- [ ] No unnecessary files are included (use `.gitignore`)

- Place tests in `tests/` directory

- Name test files `test_*.py`### PR Description Template

- Use descriptive test names

```markdown

```python## Description

def test_character_merge_preserves_dialogue():Brief description of what this PR does.

    """Test that merging characters maintains all dialogue lines."""

    # Setup## Type of Change

    char1 = Character("John", lines=["Hello"])- [ ] Bug fix

    char2 = Character("John Smith", lines=["World"])- [ ] New feature

    - [ ] Documentation update

    # Execute- [ ] Performance improvement

    merged = merge_characters([char1, char2])- [ ] Code refactoring

    

    # Assert## Testing

    assert len(merged.lines) == 2Describe how you tested these changes.

    assert "Hello" in merged.lines

```## Screenshots (if applicable)

Add screenshots for UI changes.

## 📚 Documentation

## Related Issues

### DocstringsFixes #123

- Use Google-style docstrings```

- Include type information

- Provide examples for complex functions### PR Review Process



### User Documentation1. A maintainer will review your PR

- Update `docs/` when adding features2. You may be asked to make changes

- Include screenshots for UI changes3. Once approved, your PR will be merged

- Keep README.md in sync4. Your contribution will be credited in the changelog



## 🔄 Pull Request Process## Reporting Bugs



### Before Submitting### Before Reporting

1. ✅ Tests pass: `pytest tests/`

2. ✅ Code is formatted: `black app/`- Check if the bug has already been reported

3. ✅ Linting passes: `flake8 app/`- Try to reproduce the bug with the latest version

4. ✅ Documentation updated- Gather as much information as possible

5. ✅ Commit messages are clear

### Bug Report Template

### PR Guidelines

- Reference related issues```markdown

- Describe changes clearly**Describe the Bug**

- Include screenshots for UI changesA clear description of the bug.

- Keep PRs focused (one feature/fix per PR)

- Be responsive to review feedback**To Reproduce**

Steps to reproduce the behavior:

### Example PR Description1. Go to '...'

```markdown2. Click on '...'

## Description3. See error

Adds character renaming functionality to Characters tab

**Expected Behavior**

## Related IssueWhat you expected to happen.

Fixes #42

**Screenshots**

## ChangesIf applicable, add screenshots.

- Added rename_character() function

- Added "Rename Character" button to UI**Environment:**

- Updates all chapter results when renaming- OS: [e.g., Windows 11, Ubuntu 22.04]

- Preserves character colors- Python Version: [e.g., 3.10.5]

- GPU: [e.g., NVIDIA RTX 3060]

## Testing- Version: [e.g., 1.0.0]

- Tested with multiple books

- Verified color preservation**Logs**

- Checked edge cases (empty name, duplicates)Paste relevant logs from the Debug tab.

```

## Screenshots

![Rename Dialog](screenshots/rename_dialog.png)## Feature Requests

```

### Feature Request Template

## 🏗️ Project Structure

```markdown

```**Is your feature request related to a problem?**

PolyVoxStudio/A clear description of the problem.

├── app/

│   ├── core/           # Business logic**Describe the solution you'd like**

│   │   ├── character_detection.pyA clear description of what you want to happen.

│   │   ├── book_processor.py

│   │   └── ...**Describe alternatives you've considered**

│   ├── engine/         # TTS engineOther solutions you've thought about.

│   ├── ui/             # GUI components

│   │   ├── main_ui.py**Additional context**

│   │   ├── characters_tab.pyAny other context, screenshots, or examples.

│   │   └── ...```

│   └── utils/          # Utilities

├── tests/              # Test suite## Code of Conduct

├── docs/               # Documentation

├── tools/              # Development tools### Our Standards

└── output/             # Runtime outputs (gitignored)

```- Be respectful and inclusive

- Welcome newcomers and help them learn

## 🐛 Debugging- Accept constructive criticism gracefully

- Focus on what's best for the community

### Debug Mode- Show empathy towards others

Enable detailed logging in Settings tab or set:

```python### Unacceptable Behavior

DEBUG_AUDIT = True  # In character_detection.py

```- Harassment, discrimination, or trolling

- Personal attacks or insults

### Common Issues- Publishing others' private information

- Other unprofessional conduct

**Character Detection Problems:**

- Check `output/booknlp_*/book_input.trace.tsv`## Project Structure

- Review quote attribution logic

- Verify BookNLP model is installed```

polyvox-studio/

**Voice Cloning Issues:**├── app/

- Ensure audio sample is 5-15 seconds│   ├── core/           # Core processing logic

- Check sample rate (22050 Hz)│   ├── engine/         # TTS engines

- Verify TTS model loaded correctly│   └── ui/             # User interface

├── assets/             # Images, icons, etc.

**GPU Problems:**├── docs/               # Documentation

- Run `nvidia-smi` to check GPU status├── tests/              # Test files

- Review GPU_COMPATIBILITY.md└── output_audio/       # Generated audio

- Try legacy installation for older GPUs```



## 🎨 UI Development## Key Areas for Contribution



### CustomTkinter Guidelines### High Priority

- Use consistent color scheme (`#2b2d31` background)

- Follow existing tab structure- **Multi-language support**: Add support for languages other than English

- Test on multiple screen sizes- **Voice editor**: Fine-tune voice parameters (pitch, speed, emotion)

- Add tooltips for complex features- **Batch processing**: Process multiple books simultaneously

- **Export formats**: Support for MP3, M4B, etc.

### Adding a New Tab- **Audio player**: Built-in player to preview generated audio

1. Create `app/ui/new_tab.py`

2. Inherit from `ctk.CTkFrame`### Medium Priority

3. Register in `main_ui.py`

4. Add icon and label- **Character editor**: Advanced character merging and editing

- **Project files**: Save and load project state

## 📦 Release Process- **Undo/Redo**: Action history for UI operations

- **Themes**: Light/dark mode and custom themes

### Version Numbering- **Plugins**: Plugin system for extensibility

We use Semantic Versioning (SemVer):

- MAJOR.MINOR.PATCH (e.g., 1.2.3)### Documentation

- MAJOR: Breaking changes

- MINOR: New features (backward compatible)- Video tutorials

- PATCH: Bug fixes- More code examples

- API documentation

### Creating a Release- Translations of documentation

1. Update version in `app/__init__.py`

2. Update CHANGELOG.md## Questions?

3. Create git tag: `git tag -a v1.2.3 -m "Release v1.2.3"`

4. Push tag: `git push origin v1.2.3`If you have questions about contributing:

5. Create GitHub Release with notes

- Open a **Discussion** on GitHub

## 💬 Community Guidelines- Ask in the **#development** channel (if available)

- Tag maintainers in relevant issues

### Code of Conduct

- Be respectful and inclusive## Recognition

- Welcome newcomers

- Provide constructive feedbackContributors are recognized in:

- Focus on the issue, not the person- CHANGELOG.md for each release

- GitHub contributors page

### Communication Channels- Special mentions for significant contributions

- GitHub Issues: Bug reports and features

- GitHub Discussions: Questions and ideas## License

- Pull Requests: Code review and collaboration

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## 📖 Additional Resources

---

- [Architecture Overview](docs/ARCHITECTURE.md)

- [Character Detection Deep Dive](docs/CHARACTER_DETECTION.md)Thank you for contributing to PolyVox Studio! 🎙️

- [Voice Cloning Technical Details](docs/VOICE_CLONING.md)

## ❓ Questions?

If you have questions about contributing:
1. Check existing documentation
2. Search closed issues
3. Open a GitHub Discussion
4. Tag maintainers if needed

Thank you for contributing to PolyVox Studio! 🎭
