import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import StreamingGUI


def main():
    app = QApplication(sys.argv)
    gui = StreamingGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
