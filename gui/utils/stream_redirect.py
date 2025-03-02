from PyQt5.QtCore import QObject, pyqtSignal


class Stream(QObject):
    """Redirect script output to GUI"""

    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self):
        pass
