# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication

from gui.main_window import StreamingGUI

class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a QApplication instance before running tests
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        # Create a fresh instance of StreamingGUI for each test
        self.gui = StreamingGUI()

    def tearDown(self):
        # Clean up after each test
        self.gui.close()
        self.gui = None

    def test_init(self):
        """Test that the main window initializes correctly"""
        # Check that the window title is set correctly
        self.assertEqual(self.gui.windowTitle(), "StreamingCommunity GUI")

        # Check that the window size is set correctly
        self.assertEqual(self.gui.geometry().width(), 1000)
        self.assertEqual(self.gui.geometry().height(), 700)

        # Check that the run_tab is created
        self.assertIsNotNone(self.gui.run_tab)

        # Check that the stdout_stream is set up
        self.assertIsNotNone(self.gui.stdout_stream)

    def test_close_event(self):
        """Test that the close event handler works correctly"""
        # Mock the process
        self.gui.process = MagicMock()
        self.gui.process.state.return_value = QApplication.instance().startingUp()  # Not running

        # Create a mock event
        event = MagicMock()

        # Call the close event handler
        self.gui.closeEvent(event)

        # Check that the event was accepted
        event.accept.assert_called_once()

        # Check that sys.stdout was restored
        self.assertEqual(sys.stdout, sys.__stdout__)

    def test_close_event_with_running_process(self):
        """Test that the close event handler terminates running processes"""
        # Import QProcess here to avoid circular import
        from PyQt5.QtCore import QProcess

        # Mock the process as running
        self.gui.process = MagicMock()
        self.gui.process.state.return_value = QProcess.Running

        # Mock the waitForFinished method to return True
        self.gui.process.waitForFinished.return_value = True

        # Create a mock event
        event = MagicMock()

        # Call the close event handler
        self.gui.closeEvent(event)

        # Check that terminate was called
        self.gui.process.terminate.assert_called_once()

        # Check that waitForFinished was called
        self.gui.process.waitForFinished.assert_called_once_with(1000)

        # Check that the event was accepted
        event.accept.assert_called_once()

        # Check that sys.stdout was restored
        self.assertEqual(sys.stdout, sys.__stdout__)

if __name__ == '__main__':
    unittest.main()
