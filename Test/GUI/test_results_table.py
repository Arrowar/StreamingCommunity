# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)

# Import
import unittest
from PyQt5.QtWidgets import QApplication, QTableWidgetItem
from PyQt5.QtCore import Qt

from gui.widgets.results_table import ResultsTable

class TestResultsTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a QApplication instance before running tests
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        # Create a fresh instance of ResultsTable for each test
        self.results_table = ResultsTable()

    def tearDown(self):
        # Clean up after each test
        self.results_table.close()
        self.results_table = None

    def test_init(self):
        """Test that the ResultsTable initializes correctly"""
        # Check that the table is hidden initially
        self.assertFalse(self.results_table.isVisible())

        # Check that the table is not editable
        self.assertEqual(self.results_table.editTriggers(), ResultsTable.NoEditTriggers)

        # Check that the table has no selection
        self.assertEqual(self.results_table.selectionMode(), ResultsTable.NoSelection)

        # Check that the table has no focus
        self.assertEqual(self.results_table.focusPolicy(), Qt.NoFocus)

        # Check that the table has no drag and drop
        self.assertEqual(self.results_table.dragDropMode(), ResultsTable.NoDragDrop)

        # Check that the table has no context menu
        self.assertEqual(self.results_table.contextMenuPolicy(), Qt.NoContextMenu)

        # Check that the vertical header is hidden
        self.assertFalse(self.results_table.verticalHeader().isVisible())

        # Check that the table is disabled
        self.assertFalse(self.results_table.isEnabled())

    def test_update_with_seasons(self):
        """Test that the update_with_seasons method works correctly"""
        # Call the method with 3 seasons
        self.results_table.update_with_seasons(3)

        # Check that the table has 2 columns
        self.assertEqual(self.results_table.columnCount(), 2)

        # Check that the table has 3 rows
        self.assertEqual(self.results_table.rowCount(), 3)

        # Check that the column headers are set correctly
        self.assertEqual(self.results_table.horizontalHeaderItem(0).text(), "Index")
        self.assertEqual(self.results_table.horizontalHeaderItem(1).text(), "Season")

        # Check that the table cells are set correctly
        for i in range(3):
            self.assertEqual(self.results_table.item(i, 0).text(), str(i + 1))
            self.assertEqual(self.results_table.item(i, 1).text(), f"Stagione {i + 1}")

            # Check that the items are not editable
            self.assertEqual(self.results_table.item(i, 0).flags(), Qt.ItemIsEnabled)
            self.assertEqual(self.results_table.item(i, 1).flags(), Qt.ItemIsEnabled)

        # Check that the table is visible
        self.assertTrue(self.results_table.isVisible())

    def test_update_with_results(self):
        """Test that the update_with_results method works correctly"""
        # Define headers and rows
        headers = ["Column 1", "Column 2", "Column 3"]
        rows = [
            ["Row 1, Col 1", "Row 1, Col 2", "Row 1, Col 3"],
            ["Row 2, Col 1", "Row 2, Col 2", "Row 2, Col 3"],
        ]

        # Call the method
        self.results_table.update_with_results(headers, rows)

        # Check that the table has the correct number of columns
        self.assertEqual(self.results_table.columnCount(), len(headers))

        # Check that the table has the correct number of rows
        self.assertEqual(self.results_table.rowCount(), len(rows))

        # Check that the column headers are set correctly
        for i, header in enumerate(headers):
            self.assertEqual(self.results_table.horizontalHeaderItem(i).text(), header)

        # Check that the table cells are set correctly
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                self.assertEqual(self.results_table.item(i, j).text(), cell)

                # Check that the items are not editable
                self.assertEqual(self.results_table.item(i, j).flags(), Qt.ItemIsEnabled)

        # Check that the table is visible
        self.assertTrue(self.results_table.isVisible())

if __name__ == '__main__':
    unittest.main()
