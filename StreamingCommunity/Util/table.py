# 03.03.24

import os
import sys
import logging
import importlib
from pathlib import Path
from typing import Dict, List, Any


# External library
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.style import Style


# Internal utilities
from .os import get_call_stack
from .message import start_message


# Telegram bot instance
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance
from StreamingCommunity.Util.config_json import config_manager
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')



class TVShowManager:
    def __init__(self):
        """
        Initialize TVShowManager with default values.
        """
        self.console = Console()
        self.tv_shows: List[Dict[str, Any]] = []
        self.slice_start = 0
        self.slice_end = 10
        self.step = self.slice_end
        self.column_info = []

    def add_column(self, column_info: Dict[str, Dict[str, str]]) -> None:
        """
        Add column information.
    
        Parameters:
            - column_info (Dict[str, Dict[str, str]]): Dictionary containing column names, their colors, and justification.
        """
        self.column_info = column_info

    def add_tv_show(self, tv_show: Dict[str, Any]) -> None:
        """
        Add a TV show to the list of TV shows.

        Parameters:
            - tv_show (Dict[str, Any]): Dictionary containing TV show details.
        """
        if tv_show:
            self.tv_shows.append(tv_show)

    def display_data(self, data_slice: List[Dict[str, Any]]) -> None:
        """
        Display TV show data in a tabular format.

        Parameters:
            - data_slice (List[Dict[str, Any]]): List of dictionaries containing TV show details to display.
        """
        if not data_slice:
            logging.error("Nothing to display.")
            return
            
        if not self.column_info:
            logging.error("Error: Column information not configured.")
            return

        table = Table(border_style="white")

        # Add columns dynamically based on provided column information
        for col_name, col_style in self.column_info.items():
            color = col_style.get("color", None)
            style = Style(color=color) if color else None
            table.add_column(col_name, style=style, justify='center')

        # Add rows dynamically based on available TV show data
        for entry in data_slice:
            if entry:
                row_data = [str(entry.get(col_name, '')) for col_name in self.column_info.keys()]
                table.add_row(*row_data)

        self.console.print(table)
    
    @staticmethod
    def run_back_command(research_func: dict) -> None:
        """
        Executes a back-end search command by dynamically importing a module and invoking its search function.

        Args:
            research_func (dict): A dictionary containing:
                - 'folder' (str): The absolute path to the directory containing the module to be executed.
        """
        try:
            # Get site name from folder
            site_name = Path(research_func['folder']).name

            # Find the project root directory
            current_path = research_func['folder']
            while not os.path.exists(os.path.join(current_path, 'StreamingCommunity')):
                current_path = os.path.dirname(current_path)
            
            project_root = current_path
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # Import using full absolute import
            module_path = f'StreamingCommunity.Api.Site.{site_name}'
            module = importlib.import_module(module_path)
            
            # Get and call the search function
            search_func = getattr(module, 'search')
            search_func(None)
            
        except Exception:
            logging.error("Error during search execution")
            
        finally:
            if project_root in sys.path:
                sys.path.remove(project_root)

    def run(self, force_int_input: bool = False, max_int_input: int = 0) -> str:
        """
        Run the TV show manager application.

        Parameters:
            - force_int_input(bool): If True, only accept integer inputs from 0 to max_int_input
            - max_int_input (int): range of row to show
        
        Returns:
            str: Last command executed before breaking out of the loop.
        """
        if not self.tv_shows:
            logging.error("Error: No data available for display.")
            return ""
            
        if not self.column_info:
            logging.error("Error: Columns not configured.")
            return ""

        total_items = len(self.tv_shows)
        last_command = ""
        is_telegram = config_manager.get_bool('DEFAULT', 'telegram_bot')
        bot = get_bot_instance() if is_telegram else None

        while True:
            start_message()
            
            # Check and adjust slice indices if out of bounds
            current_slice = self.tv_shows[self.slice_start:self.slice_end]
            if not current_slice and total_items > 0:
                self.slice_start = 0
                self.slice_end = min(self.step, total_items)
                current_slice = self.tv_shows[self.slice_start:self.slice_end]
            
            self.display_data(current_slice)

            # Resto del codice rimane uguale...
            research_func = next((
                f for f in get_call_stack()
                if f['function'] == 'search' and f['script'] == '__init__.py'
            ), None)

            # Handle pagination and user input
            if self.slice_end < total_items:
                self.console.print("\n[green]Press [red]Enter [green]for next page, [red]'q' [green]to quit, or [red]'back' [green]to search.")

                if not force_int_input:
                    prompt_msg = ("\n[cyan]Insert media index [yellow](e.g., 1), [red]* [cyan]to download all media, "
                                "[yellow](e.g., 1-2) [cyan]for a range of media, or [yellow](e.g., 3-*) [cyan]to download from a specific index to the end")
                    telegram_msg = "Menu di selezione degli episodi: \n\n" \
                                   "- Inserisci il numero dell'episodio (ad esempio, 1)\n" \
                                   "- Inserisci * per scaricare tutti gli episodi\n" \
                                   "- Inserisci un intervallo di episodi (ad esempio, 1-2) per scaricare da un episodio all'altro\n" \
                                   "- Inserisci (ad esempio, 3-*) per scaricare dall'episodio specificato fino alla fine della serie"
                    
                    if is_telegram:
                        key = bot.ask("select_title_episode", telegram_msg, None)
                    else:
                        key = Prompt.ask(prompt_msg)
                else:
                    # Include empty string in choices to allow pagination with Enter key
                    choices = [""] + [str(i) for i in range(max_int_input + 1)] + ["q", "quit", "b", "back"]
                    prompt_msg = "[cyan]Insert media [red]index"
                    telegram_msg = "Scegli il contenuto da scaricare:\n Serie TV -  Film -  Anime\noppure `back` per tornare indietro"
                    
                    if is_telegram:
                        key = bot.ask("select_title", telegram_msg, None)
                    else:
                        key = Prompt.ask(prompt_msg, choices=choices, show_choices=False)

                last_command = key

                if key.lower() in ["q", "quit"]:
                    break
                elif key == "":
                    self.slice_start += self.step
                    self.slice_end += self.step
                    if self.slice_end > total_items:
                        self.slice_end = total_items
                elif (key.lower() in ["b", "back"]) and research_func:
                    TVShowManager.run_back_command(research_func)
                else:
                    break

            else:
                # Last page handling
                self.console.print("\n[green]You've reached the end. [red]Enter [green]for first page, [red]'q' [green]to quit, or [red]'back' [green]to search.")
                
                if not force_int_input:
                    prompt_msg = ("\n[cyan]Insert media index [yellow](e.g., 1), [red]* [cyan]to download all media, "
                                "[yellow](e.g., 1-2) [cyan]for a range of media, or [yellow](e.g., 3-*) [cyan]to download from a specific index to the end")
                    telegram_msg = "Menu di selezione degli episodi: \n\n" \
                                   "- Inserisci il numero dell'episodio (ad esempio, 1)\n" \
                                   "- Inserisci * per scaricare tutti gli episodi\n" \
                                   "- Inserisci un intervallo di episodi (ad esempio, 1-2) per scaricare da un episodio all'altro\n" \
                                   "- Inserisci (ad esempio, 3-*) per scaricare dall'episodio specificato fino alla fine della serie"
                    
                    if is_telegram:
                        key = bot.ask("select_title_episode", telegram_msg, None)
                    else:
                        key = Prompt.ask(prompt_msg)
                else:
                    # Include empty string in choices to allow pagination with Enter key
                    choices = [""] + [str(i) for i in range(max_int_input + 1)] + ["q", "quit", "b", "back"]
                    prompt_msg = "[cyan]Insert media [red]index"
                    telegram_msg = "Scegli il contenuto da scaricare:\n Serie TV -  Film -  Anime\noppure `back` per tornare indietro"
                    
                    if is_telegram:
                        key = bot.ask("select_title", telegram_msg, None)
                    else:
                        key = Prompt.ask(prompt_msg, choices=choices, show_choices=False)

                last_command = key

                if key.lower() in ["q", "quit"]:
                    break
                elif key == "":
                    self.slice_start = 0
                    self.slice_end = self.step
                elif (key.lower() in ["b", "back"]) and research_func:
                    TVShowManager.run_back_command(research_func)
                else:
                    break

        return last_command

    def clear(self) -> None:
        """
        Clear all TV shows data.
        """
        self.tv_shows = []
        self.slice_start = 0
        self.slice_end = self.step