"""
Splash screen for PolyVox Studio.
Displays the PolyVox logo while the application initializes.
"""
import tkinter as tk
from PIL import Image, ImageTk
import os
import time


class SplashScreen:
    def __init__(self, image_path, duration=2000):
        """
        Create and display a splash screen.
        
        Args:
            image_path: Path to the splash screen image
            duration: How long to display the splash screen in milliseconds (default: 2000ms = 2 seconds)
        """
        self.duration = duration
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window initially
        
        # Create splash window
        self.splash = tk.Toplevel(self.root)
        self.splash.overrideredirect(True)  # Remove window decorations
        
        # Load and display the image
        try:
            if os.path.exists(image_path):
                # Load image
                image = Image.open(image_path)
                
                # Resize if needed (keep aspect ratio)
                max_width = 800
                max_height = 600
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # Create label with image
                label = tk.Label(self.splash, image=photo, bg='#2b2d31')
                label.image = photo  # Keep a reference to prevent garbage collection
                label.pack()
                
                # Get image dimensions
                img_width = photo.width()
                img_height = photo.height()
            else:
                # Fallback: text-based splash screen
                img_width = 600
                img_height = 400
                label = tk.Label(
                    self.splash,
                    text="PolyVox Studio\n\nMany voices, one story.",
                    font=("Helvetica", 32, "bold"),
                    bg='#2b2d31',
                    fg='white',
                    width=30,
                    height=10
                )
                label.pack()
        except Exception as e:
            print(f"[SplashScreen] Error loading image: {e}")
            # Fallback to text
            img_width = 600
            img_height = 400
            label = tk.Label(
                self.splash,
                text="PolyVox Studio\n\nMany voices, one story.",
                font=("Helvetica", 32, "bold"),
                bg='#2b2d31',
                fg='white',
                width=30,
                height=10
            )
            label.pack()
        
        # Center the splash screen
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - img_width) // 2
        y = (screen_height - img_height) // 2
        self.splash.geometry(f"{img_width}x{img_height}+{x}+{y}")
        
        # Ensure splash is on top
        self.splash.lift()
        self.splash.attributes('-topmost', True)
        
        # Schedule splash screen to close
        self.splash.after(self.duration, self.close)
        
    def close(self):
        """Close the splash screen."""
        self.splash.destroy()
        self.root.quit()
    
    def show(self):
        """Display the splash screen."""
        self.root.mainloop()


def show_splash_screen(image_path=None, duration=2000):
    """
    Show the splash screen and wait for it to close.
    
    Args:
        image_path: Path to the splash screen image (optional)
        duration: How long to display in milliseconds (default: 2000ms)
    """
    if image_path is None:
        # Default path
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "polyvox_splash.png"
        )
    
    splash = SplashScreen(image_path, duration)
    splash.show()


if __name__ == "__main__":
    # Test the splash screen
    show_splash_screen(duration=3000)
