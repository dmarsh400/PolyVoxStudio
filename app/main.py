from app.ui_qt.splash_screen import show_splash_screen
from app.ui_qt.main_ui import run_app

if __name__ == "__main__":
    # Show splash screen first
    show_splash_screen(duration=2500)  # 2.5 seconds
    
    # Then launch main application
    raise SystemExit(run_app())