# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication

from gui.utils.stream_redirect import Stream

class TestStreamRedirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a QApplication instance before running tests
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        # Create a fresh instance of Stream for each test
        self.stream = Stream()

        # Create a mock slot to connect to the newText signal
        self.mock_slot = MagicMock()
        self.stream.newText.connect(self.mock_slot)

    def tearDown(self):
        # Clean up after each test
        self.stream.newText.disconnect(self.mock_slot)
        self.stream = None
        self.mock_slot = None

    def test_write(self):
        """Test that the write method emits the newText signal with the correct text"""
        # Call the write method
        self.stream.write("Test message")

        # Check that the mock slot was called with the correct text
        self.mock_slot.assert_called_once_with("Test message")

        # Call the write method again with a different message
        self.stream.write("Another test")

        # Check that the mock slot was called again with the correct text
        self.mock_slot.assert_called_with("Another test")

        # Check that the mock slot was called exactly twice
        self.assertEqual(self.mock_slot.call_count, 2)

    def test_flush(self):
        """Test that the flush method does nothing (as required by the io interface)"""
        # Call the flush method
        self.stream.flush()

        # Check that the mock slot was not called
        self.mock_slot.assert_not_called()

if __name__ == '__main__':
    unittest.main()
