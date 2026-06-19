import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
