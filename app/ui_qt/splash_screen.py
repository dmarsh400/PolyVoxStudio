import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QSplashScreen


def show_splash_screen(duration=2000, image_path=None):
    app = QApplication.instance()
    owns_app = False
    if app is None:
        app = QApplication([])
        owns_app = True

    if image_path is None:
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets",
            "polyvox_splash.png",
        )

    if os.path.exists(image_path):
        pixmap = QPixmap(image_path)
    else:
        pixmap = QPixmap(600, 300)
        pixmap.fill(Qt.GlobalColor.black)

    splash = QSplashScreen(pixmap)
    if pixmap.isNull() or pixmap.width() <= 1:
        splash.setStyleSheet("background: #1f2329; color: white; font-size: 22px; font-weight: 700;")
        splash.showMessage("PolyVox Studio\nMany voices, one story.", Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)

    splash.show()
    app.processEvents()

    done = {"value": False}

    def close_splash():
        done["value"] = True
        splash.close()

    QTimer.singleShot(duration, close_splash)
    while not done["value"]:
        app.processEvents()

    if owns_app:
        app.quit()
