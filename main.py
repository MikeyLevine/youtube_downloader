"""
main.py - Application entry point.
Usage: python main.py
"""

import sys
import os
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from gui.main_window import MainWindow, STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("YT Downloader")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("YTDownloader")

    app.setStyleSheet(STYLESHEET)

    # Prefer .ico on Windows (best quality), fall back to .png
    for icon_path in [
        os.path.join(ROOT, "img", "icon.ico"),
        os.path.join(ROOT, "img", "icon.png"),
        os.path.join(ROOT, "assets", "icons", "app_icon.png"),
    ]:
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break

    try:
        window = MainWindow()
        window.show()
    except Exception:
        tb = traceback.format_exc()
        print("STARTUP CRASH:\n", tb, flush=True)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Startup Error")
        msg.setText("The application failed to start.")
        msg.setDetailedText(tb)
        msg.exec()
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()