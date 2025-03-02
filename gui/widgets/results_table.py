from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt


class ResultsTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def setup_table(self):
        self.setVisible(False)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setDragDropMode(QTableWidget.NoDragDrop)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.verticalHeader().setVisible(False)

        # set custom style for diabled table
        self.setStyleSheet(
            """
            QTableWidget:disabled {
                color: white;
                background-color: #323232;
            }
        """
        )
        self.setEnabled(False)

    def update_with_seasons(self, num_seasons):
        self.clear()
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Index", "Season"])

        self.setRowCount(num_seasons)
        for i in range(num_seasons):
            index_item = QTableWidgetItem(str(i + 1))
            season_item = QTableWidgetItem(f"Stagione {i + 1}")
            index_item.setFlags(Qt.ItemIsEnabled)
            season_item.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 0, index_item)
            self.setItem(i, 1, season_item)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setEnabled(False)
        self.setVisible(True)

    def update_with_results(self, headers, rows):
        self.clear()
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        self.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                item = QTableWidgetItem(cell)
                item.setFlags(Qt.ItemIsEnabled)
                self.setItem(i, j, item)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setEnabled(False)
        self.setVisible(True)
