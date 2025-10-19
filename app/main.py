from app.ui.splash_screen import show_splash_screen
from app.ui.main_ui import run_app

if __name__ == "__main__":
    # Show splash screen first
    show_splash_screen(duration=2500)  # 2.5 seconds
    
    # Then launch main application
    run_app()