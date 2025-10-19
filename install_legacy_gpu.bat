@echo off
REM VOX Audiobook Generator - Legacy GPU Installation (Windows)
REM For NVIDIA K80 and older GPUs

echo =========================================
echo VOX Audiobook Generator - Legacy GPU Setup
echo For NVIDIA K80 and older GPUs
echo =========================================
echo.

REM Check for conda
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: conda not found!
    echo Please install Miniconda or Anaconda first:
    echo   https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)

echo Step 1: Creating conda environment 'vox_legacy'...
echo ----------------------------------------------
call conda create -n vox_legacy python=3.9 -y

echo.
echo Step 2: Installing PyTorch 1.13 with CUDA 11.6 (K80 compatible)...
echo ----------------------------------------------------------------
call conda install -n vox_legacy pytorch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 pytorch-cuda=11.6 -c pytorch -c nvidia -y

echo.
echo Step 3: Installing TTS (Coqui-ai) for legacy GPU...
echo ---------------------------------------------------
call conda run -n vox_legacy pip install TTS==0.17.0

echo.
echo Step 4: Installing core dependencies...
echo ---------------------------------------
call conda run -n vox_legacy pip install numpy==1.23.5 scipy==1.10.1 librosa==0.10.0 soundfile pydub matplotlib customtkinter pillow sounddevice

echo.
echo Step 5: Installing NLP dependencies...
echo --------------------------------------
call conda run -n vox_legacy pip install spacy==3.5.0 transformers==4.30.0 sentencepiece

REM Install spaCy English model
call conda run -n vox_legacy python -m spacy download en_core_web_sm

echo.
echo Step 6: Installing BookNLP (character detection)...
echo --------------------------------------------------
call conda run -n vox_legacy pip install booknlp==1.0.7

echo.
echo Step 7: Installing additional utilities...
echo -----------------------------------------
call conda run -n vox_legacy pip install ebooklib charset-normalizer ffmpeg-python

echo.
echo Step 8: Verifying installation...
echo --------------------------------

REM Test PyTorch and CUDA
echo Testing PyTorch and CUDA...
call conda run -n vox_legacy python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}' if torch.cuda.is_available() else 'CPU mode')"

REM Test TTS
echo.
echo Testing TTS installation...
call conda run -n vox_legacy python -c "from TTS.api import TTS; print('TTS imported successfully')"

echo.
echo =========================================
echo Installation Complete!
echo =========================================
echo.
echo To use the legacy GPU environment:
echo.
echo   conda activate vox_legacy
echo   python app\main.py
echo.
echo Or use the launcher script:
echo   run_gui_legacy.bat
echo.
echo NOTE: This environment uses:
echo   - PyTorch 1.13.1 with CUDA 11.6
echo   - TTS 0.17.0
echo   - Compatible with K80, GTX 700/900/1000 series
echo.
echo If you still get GPU errors, you may need to:
echo   1. Update NVIDIA drivers to 450.80.02 or newer
echo   2. Or use CPU mode by disabling GPU in Settings
echo.
pause
