from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import QProcess
import sys
from .tabs.run_tab import RunTab
from .utils.stream_redirect import Stream


class StreamingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = None
        self.init_ui()
        self.setup_output_redirect()

    def init_ui(self):
        self.setWindowTitle("StreamingCommunity GUI")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        main_layout = QVBoxLayout()

        self.run_tab = RunTab(self)
        main_layout.addWidget(self.run_tab)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def setup_output_redirect(self):
        self.stdout_stream = Stream()
        self.stdout_stream.newText.connect(self.run_tab.update_output)
        sys.stdout = self.stdout_stream

    def closeEvent(self, event):
        if self.process and self.process.state() == QProcess.Running:
            self.process.terminate()
            if not self.process.waitForFinished(1000):
                self.process.kill()
        sys.stdout = sys.__stdout__
        event.accept()
