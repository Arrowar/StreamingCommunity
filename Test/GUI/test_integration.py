# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QProcess

from gui.main_window import StreamingGUI
from gui.tabs.run_tab import RunTab
from gui.widgets.results_table import ResultsTable
from gui.utils.stream_redirect import Stream
from gui.utils.site_manager import sites

class TestGUIIntegration(unittest.TestCase):
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

    def test_main_window_has_run_tab(self):
        """Test that the main window has a RunTab instance"""
        self.assertIsInstance(self.gui.run_tab, RunTab)

    def test_run_tab_has_results_table(self):
        """Test that the RunTab has a ResultsTable instance"""
        self.assertIsInstance(self.gui.run_tab.results_table, ResultsTable)

    def test_stdout_redirection(self):
        """Test that stdout is redirected to the RunTab's output_text"""
        # Get the original stdout
        original_stdout = sys.stdout

        # Check that stdout is now a Stream instance
        self.assertIsInstance(sys.stdout, Stream)

        # Check that the Stream's newText signal is connected to the RunTab's update_output method
        # We can't directly check the connections, but we can test the behavior

        # First, make the output_text visible
        # Import Qt here to avoid circular import
        from PyQt5.QtCore import Qt
        self.gui.run_tab.toggle_console(Qt.Checked)

        # Then, print something
        print("Test message")

        # Check that the message appears in the output_text
        self.assertIn("Test message", self.gui.run_tab.output_text.toPlainText())

        # Restore the original stdout for cleanup
        sys.stdout = original_stdout

    @patch('gui.tabs.run_tab.QProcess')
    def test_run_script_integration(self, mock_qprocess):
        """Test that the run_script method integrates with other components"""
        # Set up the mock QProcess
        mock_process = MagicMock()
        mock_qprocess.return_value = mock_process

        # Set some search terms
        self.gui.run_tab.search_terms.setText("test search")

        # Call the run_script method
        self.gui.run_tab.run_script()

        # Check that the process was created
        self.assertIsNotNone(self.gui.run_tab.process)

        # Check that the run_button is disabled
        self.assertFalse(self.gui.run_tab.run_button.isEnabled())

        # Check that the stop_button is enabled
        self.assertTrue(self.gui.run_tab.stop_button.isEnabled())

        # Check that the process was started with the correct arguments
        mock_process.start.assert_called_once()
        args = mock_process.start.call_args[0][1]
        self.assertIn("run_streaming.py", args[0])
        self.assertIn("-s", args[1:])
        self.assertIn("test search", args[1:])

    def test_toggle_console_integration(self):
        """Test that the toggle_console method integrates with other components"""
        # Import Qt here to avoid circular import
        from PyQt5.QtCore import Qt

        # Initially, the console_checkbox should be unchecked
        self.assertFalse(self.gui.run_tab.console_checkbox.isChecked())

        # Check the console_checkbox
        self.gui.run_tab.console_checkbox.setChecked(True)

        # Call the toggle_console method directly with the checked state
        self.gui.run_tab.toggle_console(Qt.Checked)

        # Uncheck the console_checkbox
        self.gui.run_tab.console_checkbox.setChecked(False)

        # Call the toggle_console method directly with the unchecked state
        self.gui.run_tab.toggle_console(Qt.Unchecked)

    def test_stop_script_integration(self):
        """Test that the stop_script method integrates with other components"""
        # Import QProcess here to avoid circular import
        from PyQt5.QtCore import QProcess as ActualQProcess

        # Create a mock process
        mock_process = MagicMock()

        # Set the process state to Running
        mock_process.state.return_value = ActualQProcess.Running

        # Mock the waitForFinished method to return True
        mock_process.waitForFinished.return_value = True

        # Set the process directly
        self.gui.run_tab.process = mock_process

        # Enable the stop button
        self.gui.run_tab.stop_button.setEnabled(True)

        # Disable the run button
        self.gui.run_tab.run_button.setEnabled(False)

        # Stop the script
        self.gui.run_tab.stop_script()

        # Check that the process was terminated
        mock_process.terminate.assert_called_once()

        # Check that waitForFinished was called
        mock_process.waitForFinished.assert_called_once_with(3000)

        # Check that the run_button is enabled
        self.assertTrue(self.gui.run_tab.run_button.isEnabled())

        # Check that the stop_button is disabled
        self.assertFalse(self.gui.run_tab.stop_button.isEnabled())

if __name__ == '__main__':
    unittest.main()
