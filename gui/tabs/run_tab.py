from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QCheckBox,
    QLabel,
    QTextEdit,
)
from PyQt5.QtCore import Qt, QProcess
from ..widgets.results_table import ResultsTable
from ..utils.site_manager import sites
import sys


class RunTab(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.process = None
        self.current_context = None
        self.selected_season = None
        self.buffer = ""
        self.init_ui()

    def init_ui(self):
        run_tab = QWidget()
        run_layout = QVBoxLayout()

        # Add search group
        run_layout.addWidget(self.create_search_group())

        # Add control buttons
        run_layout.addLayout(self.create_control_layout())

        # Add status label
        self.status_label = QLabel("Richiesta in corso...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()
        run_layout.addWidget(self.status_label)

        # Add output group
        run_layout.addWidget(self.create_output_group())

        run_tab.setLayout(run_layout)
        self.addTab(run_tab, "Esecuzione")

    def create_search_group(self):
        search_group = QGroupBox("Parametri di Ricerca")
        search_layout = QFormLayout()

        self.search_terms = QLineEdit()
        search_layout.addRow("Termini di ricerca:", self.search_terms)

        self.site_combo = QComboBox()
        for site in sites:
            self.site_combo.addItem(f"{site['name']}", site["index"])
            self.site_combo.setItemData(site["index"], site["flag"], Qt.ToolTipRole)
        if self.site_combo.count() > 0:
            self.site_combo.setCurrentIndex(0)

        search_layout.addRow("Seleziona sito:", self.site_combo)
        search_group.setLayout(search_layout)
        return search_group

    def create_control_layout(self):
        control_layout = QHBoxLayout()

        self.run_button = QPushButton("Esegui Script")
        self.run_button.clicked.connect(self.run_script)
        control_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Ferma Script")
        self.stop_button.clicked.connect(self.stop_script)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        self.console_checkbox = QCheckBox("Mostra Console")
        self.console_checkbox.setChecked(False)
        self.console_checkbox.stateChanged.connect(self.toggle_console)
        control_layout.addWidget(self.console_checkbox)

        return control_layout

    def create_output_group(self):
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()

        self.results_table = ResultsTable()
        output_layout.addWidget(self.results_table)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.hide()
        output_layout.addWidget(self.output_text)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Inserisci l'indice del media...")
        self.input_field.returnPressed.connect(self.send_input)
        self.send_button = QPushButton("Invia")
        self.send_button.clicked.connect(self.send_input)

        self.input_field.hide()
        self.send_button.hide()

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        output_layout.addLayout(input_layout)

        output_group.setLayout(output_layout)
        return output_group

    def toggle_console(self, state):
        self.output_text.setVisible(state == Qt.Checked)
        # Don't hide the results table when toggling the console
        if state == Qt.Checked:
            self.results_table.setVisible(True)

    def run_script(self):
        if self.process is not None and self.process.state() == QProcess.Running:
            print("Script già in esecuzione.")
            return

        # Reset all state variables when starting a new search
        self.current_context = None
        self.selected_season = None
        self.buffer = ""
        self.results_table.setVisible(False)
        self.status_label.setText("Richiesta in corso...")
        self.status_label.show()

        args = []
        search_terms = self.search_terms.text()
        if search_terms:
            args.extend(["-s", search_terms])

        site_index = self.site_combo.currentIndex()
        if site_index >= 0:
            # Usa il nome completo del sito invece della flag abbreviata
            site_name = sites[site_index]["name"].lower()
            args.extend(["--site", site_name])

        self.output_text.clear()
        print(f"Avvio script con argomenti: {' '.join(args)}")

        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        python_executable = sys.executable
        script_path = "run_streaming.py"

        self.process.start(python_executable, [script_path] + args)
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8", errors="replace")
        self.update_output(stdout)

        self.buffer += stdout

        if "Episodes find:" in self.buffer:
            self.current_context = "episodes"
            self.input_field.setPlaceholderText(
                "Inserisci l'indice dell'episodio (es: 1, *, 1-2, 3-*)"
            )
        elif "Seasons found:" in self.buffer:
            self.current_context = "seasons"
            self.input_field.setPlaceholderText(
                "Inserisci il numero della stagione (es: 1, *, 1-2, 3-*)"
            )

        if "Episodes find:" in self.buffer:
            # If we've selected a season and we're now seeing episodes, update the table with episode data
            if self.selected_season is not None:
                # Check if we have a table to display
                if (("┏" in self.buffer or "┌" in self.buffer) and
                        ("┗" in self.buffer or "┛" in self.buffer or "└" in self.buffer)):
                    self.parse_and_show_results(self.buffer)
                    self.status_label.hide()
                else:
                    # We're still waiting for the table data
                    self.status_label.setText("Caricamento episodi...")
                    self.status_label.show()
            else:
                self.results_table.hide()
                self.current_context = "episodes"
                text_to_show = f"Trovati {self.buffer.split('Episodes find:')[1].split()[0]} episodi!"
                self.status_label.setText(text_to_show)
                self.status_label.show()
        elif (("┏" in self.buffer or "┌" in self.buffer) and
                ("┗" in self.buffer or "┛" in self.buffer or "└" in self.buffer)) or "Seasons found:" in self.buffer:
            self.parse_and_show_results(self.buffer)

        if "Insert" in self.buffer:
            self.input_field.show()
            self.send_button.show()
            self.input_field.setFocus()
            self.output_text.verticalScrollBar().setValue(
                self.output_text.verticalScrollBar().maximum()
            )

    def parse_and_show_results(self, text):
        if "Seasons found:" in text and not "Insert media index (e.g., 1)" in text:
            self.status_label.hide()
            num_seasons = int(text.split("Seasons found:")[1].split()[0])
            self.results_table.update_with_seasons(num_seasons)
            return

        # If we've selected a season and we're now seeing episodes, don't update the table with search results
        # But only if we don't have a table to display yet
        if self.selected_season is not None and "Episodes find:" in text and not (("┏" in text or "┌" in text) and
                ("┗" in text or "┛" in text or "└" in text)):
            return

        if ("┏━━━━━━━┳" in text or "┌───────┬" in text) and "└───────┴" in text:
            chars_to_find = []
            if "┏" in text:
                chars_to_find.append("┏")
                chars_to_find.append("┃")
            elif "┌" in text:
                chars_to_find.append("┌")
                chars_to_find.append("│")

            if not chars_to_find or len(chars_to_find) == 0:
                return
            self.status_label.hide()
            table_lines = text[text.find(chars_to_find[0]) : text.find("└")].split("\n")
            headers = [h.strip() for h in table_lines[1].split(chars_to_find[1])[1:-1]]

            rows = []
            for line in table_lines[3:]:
                if line.strip() and "│" in line:
                    cells = [cell.strip() for cell in line.split("│")[1:-1]]
                    rows.append(cells)

            # Make sure we're showing the table
            self.results_table.setVisible(True)
            self.results_table.update_with_results(headers, rows)

    def send_input(self):
        if not self.process or self.process.state() != QProcess.Running:
            return

        user_input = self.input_field.text().strip()

        if self.current_context == "seasons":
            if "-" in user_input or user_input == "*":
                self.results_table.hide()
            else:
                self.selected_season = user_input
                # Clear the buffer to ensure we don't mix old data with new episode data
                self.buffer = ""

        elif self.current_context == "episodes":
            if "-" in user_input or user_input == "*":
                self.results_table.hide()

        self.process.write(f"{user_input}\n".encode())
        self.input_field.clear()
        self.input_field.hide()
        self.send_button.hide()

        if self.current_context == "seasons" and not (
            "-" in user_input or user_input == "*"
        ):
            self.status_label.setText("Caricamento episodi...")
            self.status_label.show()

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8", errors="replace")
        self.update_output(stderr)

    def process_finished(self):
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.input_field.hide()
        self.send_button.hide()
        self.status_label.hide()
        # Reset selected_season when the process finishes
        self.selected_season = None
        print("Script terminato.")

    def update_output(self, text):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.output_text.setTextCursor(cursor)
        self.output_text.ensureCursorVisible()

    def stop_script(self):
        if self.process is not None and self.process.state() == QProcess.Running:
            self.process.terminate()
            if not self.process.waitForFinished(3000):
                self.process.kill()
            print("Script terminato.")
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
