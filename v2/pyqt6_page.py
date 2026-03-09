import sys

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


def main():
    # Keep the entry file minimal: app bootstrap only.
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
