@echo off
REM Activate conda environment (adjust path if needed)
call conda activate epub_adv

REM Run the GUI
python -m app.ui.main_ui

pause
