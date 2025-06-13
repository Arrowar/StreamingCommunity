# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QProcess

from gui.tabs.run_tab import RunTab
from gui.utils.site_manager import sites

class TestRunTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a QApplication instance before running tests
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        # Create a parent widget and a fresh instance of RunTab for each test
        self.parent = QWidget()
        self.run_tab = RunTab(self.parent)

    def tearDown(self):
        # Clean up after each test
        self.run_tab.close()
        self.parent.close()
        self.run_tab = None
        self.parent = None

    def test_init(self):
        """Test that the RunTab initializes correctly"""
        # Check that the parent is set correctly
        self.assertEqual(self.run_tab.parent, self.parent)

        # Check that the process is None initially
        self.assertIsNone(self.run_tab.process)

        # Check that the current_context is None initially
        self.assertIsNone(self.run_tab.current_context)

        # Check that the selected_season is None initially
        self.assertIsNone(self.run_tab.selected_season)

        # Check that the buffer is empty initially
        self.assertEqual(self.run_tab.buffer, "")

    def test_create_search_group(self):
        """Test that the search group is created correctly"""
        # Get the search group
        search_group = self.run_tab.create_search_group()

        # Check that the search_terms QLineEdit is created
        self.assertIsNotNone(self.run_tab.search_terms)

        # Check that the site_combo QComboBox is created and populated
        self.assertIsNotNone(self.run_tab.site_combo)
        self.assertEqual(self.run_tab.site_combo.count(), len(sites))

        # Check that the first site is selected by default
        if len(sites) > 0:
            self.assertEqual(self.run_tab.site_combo.currentIndex(), 0)

    def test_create_control_layout(self):
        """Test that the control layout is created correctly"""
        # Get the control layout
        control_layout = self.run_tab.create_control_layout()

        # Check that the run_button is created
        self.assertIsNotNone(self.run_tab.run_button)

        # Check that the stop_button is created and disabled initially
        self.assertIsNotNone(self.run_tab.stop_button)
        self.assertFalse(self.run_tab.stop_button.isEnabled())

        # Check that the console_checkbox is created and unchecked initially
        self.assertIsNotNone(self.run_tab.console_checkbox)
        self.assertFalse(self.run_tab.console_checkbox.isChecked())

    def test_create_output_group(self):
        """Test that the output group is created correctly"""
        # Get the output group
        output_group = self.run_tab.create_output_group()

        # Check that the results_table is created
        self.assertIsNotNone(self.run_tab.results_table)

        # Check that the output_text is created and hidden initially
        self.assertIsNotNone(self.run_tab.output_text)
        self.assertFalse(self.run_tab.output_text.isVisible())

        # Check that the input_field is created and hidden initially
        self.assertIsNotNone(self.run_tab.input_field)
        self.assertFalse(self.run_tab.input_field.isVisible())

        # Check that the send_button is created and hidden initially
        self.assertIsNotNone(self.run_tab.send_button)
        self.assertFalse(self.run_tab.send_button.isVisible())

    def test_toggle_console(self):
        """Test that the toggle_console method works correctly"""
        # Import Qt here to avoid circular import
        from PyQt5.QtCore import Qt

        # Initially, the console_checkbox should be unchecked
        self.assertFalse(self.run_tab.console_checkbox.isChecked())

        # Check the console_checkbox
        self.run_tab.console_checkbox.setChecked(True)

        # Call the toggle_console method directly with the checked state
        self.run_tab.toggle_console(Qt.Checked)

        # Uncheck the console_checkbox
        self.run_tab.console_checkbox.setChecked(False)

        # Call the toggle_console method directly with the unchecked state
        self.run_tab.toggle_console(Qt.Unchecked)

    @patch('gui.tabs.run_tab.QProcess')
    def test_run_script(self, mock_qprocess):
        """Test that the run_script method works correctly"""
        # Set up the mock QProcess
        mock_process = MagicMock()
        mock_qprocess.return_value = mock_process

        # Set some search terms
        self.run_tab.search_terms.setText("test search")

        # Call the run_script method
        self.run_tab.run_script()

        # Check that the process was created
        self.assertIsNotNone(self.run_tab.process)

        # Check that the run_button is disabled
        self.assertFalse(self.run_tab.run_button.isEnabled())

        # Check that the stop_button is enabled
        self.assertTrue(self.run_tab.stop_button.isEnabled())

        # Check that the process was started with the correct arguments
        mock_process.start.assert_called_once()
        args = mock_process.start.call_args[0][1]
        self.assertIn("run_streaming.py", args[0])
        self.assertIn("-s", args[1:])
        self.assertIn("test search", args[1:])

    def test_stop_script(self):
        """Test that the stop_script method works correctly"""
        # Import QProcess here to avoid circular import
        from PyQt5.QtCore import QProcess as ActualQProcess

        # Create a mock process
        mock_process = MagicMock()

        # Set the process state to Running
        mock_process.state.return_value = ActualQProcess.Running

        # Mock the waitForFinished method to return True
        mock_process.waitForFinished.return_value = True

        # Set the process
        self.run_tab.process = mock_process

        # Call the stop_script method
        self.run_tab.stop_script()

        # Check that the process was terminated
        mock_process.terminate.assert_called_once()

        # Check that waitForFinished was called
        mock_process.waitForFinished.assert_called_once_with(3000)

        # Check that the run_button is enabled
        self.assertTrue(self.run_tab.run_button.isEnabled())

        # Check that the stop_button is disabled
        self.assertFalse(self.run_tab.stop_button.isEnabled())

if __name__ == '__main__':
    unittest.main()
