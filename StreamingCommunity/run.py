# 10.12.23

import os
import sys
import time
import glob
import logging
import platform
import argparse
import importlib
import threading, asyncio
from typing import Callable


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from .global_search import global_search
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import os_summary, internet_manager
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity.Upload.update import update as git_update
from StreamingCommunity.Lib.TMBD import tmdb
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance, TelegramSession


# Config
SHOW_TRENDING = config_manager.get_bool('DEFAULT', 'show_trending')
NOT_CLOSE_CONSOLE = config_manager.get_bool('DEFAULT', 'not_close')
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')


# Variable
console = Console()
msg = Prompt()


def run_function(func: Callable[..., None], close_console: bool = False, search_terms: str = None) -> None:
    """
    Run a given function indefinitely or once, depending on the value of close_console.

    Parameters:
        func (Callable[..., None]): The function to run.
        close_console (bool, optional): Whether to close the console after running the function once. Defaults to False.
        search_terms (str, optional): Search terms to use for the function. Defaults to None.
    """
    if close_console:
        while 1:
            func(search_terms)
    else:
        func(search_terms)


# !!! DA METTERE IN COMUNE CON QUELLA DI GLOBAL
def load_search_functions():
    modules = []
    loaded_functions = {}

    # Lista dei siti da escludere se TELEGRAM_BOT è attivo
    excluded_sites = {"cb01new", "guardaserie", "ilcorsaronero", "mostraguarda"} if TELEGRAM_BOT else set()

    # Find api home directory
    if getattr(sys, 'frozen', False):  # Modalità PyInstaller
        base_path = os.path.join(sys._MEIPASS, "StreamingCommunity")
    else:
        base_path = os.path.dirname(__file__)

    api_dir = os.path.join(base_path, 'Api', 'Site')
    init_files = glob.glob(os.path.join(api_dir, '*', '__init__.py'))

    # Retrieve modules and their indices
    for init_file in init_files:

        # Get folder name as module name
        module_name = os.path.basename(os.path.dirname(init_file))

        # Se il modulo è nella lista da escludere, saltalo
        if module_name in excluded_sites:
            continue

        logging.info(f"Load module name: {module_name}")

        try:
            # Dynamically import the module
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')

            # Get 'indice' from the module
            indice = getattr(mod, 'indice')
            use_for = getattr(mod, '_useFor')

            if not getattr(mod, '_deprecate'):
                modules.append((module_name, indice, use_for))

        except Exception as e:
            console.print(f"[red]Failed to import module {module_name}: {str(e)}")

    # Sort modules by 'indice'
    modules.sort(key=lambda x: x[1])

    # Load search functions in the sorted order
    for module_name, _, use_for in modules:

        # Construct a unique alias for the module
        module_alias = f'{module_name}_search'

        try:

            # Dynamically import the module
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')

            # Get the search function from the module (assuming the function is named 'search' and defined in __init__.py)
            search_function = getattr(mod, 'search')

            # Add the function to the loaded functions dictionary
            loaded_functions[module_alias] = (search_function, use_for)

        except Exception as e:
            console.print(f"[red]Failed to load search function from module {module_name}: {str(e)}")

    return loaded_functions


def initialize():

    # Get start message
    start_message()

    # Get system info
    os_summary.get_system_summary()

    # Set terminal size for win 7
    if platform.system() == "Windows" and "7" in platform.version():
        os.system('mode 120, 40')

    # Check python version
    if sys.version_info < (3, 7):
        console.log("[red]Install python version > 3.7.16")
        sys.exit(0)

    # Trending tmbd
    if SHOW_TRENDING:
        print()
        tmdb.display_trending_films()
        tmdb.display_trending_tv_shows()

    # Attempting GitHub update
    try:
        git_update()
    except:
        console.log("[red]Error with loading github.")

def restart_script():
    """Riavvia lo script con gli stessi argomenti della riga di comando."""
    print("\nRiavvio dello script...\n")
    python = sys.executable
    os.execv(python, [python] + sys.argv)


def force_exit():
    """Forza la chiusura dello script in qualsiasi contesto."""

    print("\nChiusura dello script in corso...")

    # 1 Chiudi tutti i thread tranne il principale
    for t in threading.enumerate():
        if t is not threading.main_thread():
            print(f"Chiusura thread: {t.name}")
            t.join(timeout=1)

    # 2 Ferma asyncio, se attivo
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            print("Arresto del loop asyncio...")
            loop.stop()
    except RuntimeError:
        pass

    # 3 Esce con sys.exit(), se fallisce usa os._exit()
    try:
        print("Uscita con sys.exit(0)")
        sys.exit(0)
    except SystemExit:
        pass

    print("Uscita forzata con os._exit(0)")
    os._exit(0)


def main(script_id = 0):

    color_map = {
        "anime": "red",
        "film_&_serie": "yellow",
        "serie": "blue",
        "torrent": "white"
    }

    if TELEGRAM_BOT:
        bot = get_bot_instance()
        bot.send_message(f"Avviato script {script_id}", None)

    start = time.time()

    # Create logger
    log_not = Logger()
    initialize()
    
    # if not internet_manager.check_dns_provider():
    #     print()
    #     console.print("[red]❌ ERROR: DNS configuration is required!")
    #     console.print("[red]The program cannot function correctly without proper DNS settings.")
    #     console.print("[yellow]Please configure one of these DNS servers:")
    #     console.print("[blue]• Cloudflare (1.1.1.1) 'https://developers.cloudflare.com/1.1.1.1/setup/windows/'")
    #     console.print("[blue]• Quad9 (9.9.9.9) 'https://docs.quad9.net/Setup_Guides/Windows/Windows_10/'")
    #     console.print("\n[yellow]⚠️ The program will not work until you configure your DNS settings.")

    #     time.sleep(2)        
    #     msg.ask("[yellow]Press Enter to continue ...")

    if not internet_manager.check_dns_resolve():
        print()
        console.print("[red]❌ ERROR: DNS configuration is required!")
        console.print("[red]The program cannot function correctly without proper DNS settings.")
        console.print("[yellow]Please configure one of these DNS servers:")
        console.print("[blue]• Cloudflare (1.1.1.1) 'https://developers.cloudflare.com/1.1.1.1/setup/windows/'")
        console.print("[blue]• Quad9 (9.9.9.9) 'https://docs.quad9.net/Setup_Guides/Windows/Windows_10/'")
        console.print("\n[yellow]⚠️ The program will not work until you configure your DNS settings.")

        os._exit(0)

    # Load search functions
    search_functions = load_search_functions()
    logging.info(f"Load module in: {time.time() - start} s")

    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Script to download movies and series from the internet. Use these commands to configure the script and control its behavior.'
    )

    parser.add_argument("script_id", nargs="?", default="unknown", help="ID dello script")

    # Add arguments for the main configuration parameters
    parser.add_argument(
        '--add_siteName', type=bool, help='Enable or disable adding the site name to the file name (e.g., true/false).'
    )
    parser.add_argument(
        '--not_close', type=bool, help='If set to true, the script will not close the console after execution (e.g., true/false).'
    )

    # Add arguments for M3U8 configuration
    parser.add_argument(
        '--default_video_worker', type=int, help='Number of workers for video during M3U8 download (default: 12).'
    )
    parser.add_argument(
        '--default_audio_worker', type=int, help='Number of workers for audio during M3U8 download (default: 12).'
    )

    # Add options for audio and subtitles
    parser.add_argument(
        '--specific_list_audio', type=str, help='Comma-separated list of specific audio languages to download (e.g., ita,eng).'
    )
    parser.add_argument(
        '--specific_list_subtitles', type=str, help='Comma-separated list of specific subtitle languages to download (e.g., eng,spa).'
    )

    # Add global search option
    parser.add_argument(
        '--global', action='store_true', help='Perform a global search across multiple sites.'
    )

    # Add arguments for search functions
    parser.add_argument('-s', '--search', default=None, help='Search terms')
    
    # Parse command-line arguments
    args = parser.parse_args()

    search_terms = args.search
    # Map command-line arguments to the config values
    config_updates = {}

    if args.add_siteName is not None:
        config_updates['DEFAULT.add_siteName'] = args.add_siteName
    if args.not_close is not None:
        config_updates['DEFAULT.not_close'] = args.not_close
    if args.default_video_worker is not None:
        config_updates['M3U8_DOWNLOAD.default_video_worker'] = args.default_video_worker
    if args.default_audio_worker is not None:
        config_updates['M3U8_DOWNLOAD.default_audio_worker'] = args.default_audio_worker
    if args.specific_list_audio is not None:
        config_updates['M3U8_DOWNLOAD.specific_list_audio'] = args.specific_list_audio.split(',')
    if args.specific_list_subtitles is not None:
        config_updates['M3U8_DOWNLOAD.specific_list_subtitles'] = args.specific_list_subtitles.split(',')

    # Apply the updates to the config file
    for key, value in config_updates.items():
        section, option = key.split('.')
        config_manager.set_key(section, option, value)

    config_manager.save_config()

    # Check if global search is requested
    if getattr(args, 'global'):
        global_search(search_terms)
        return

    # Create mappings using module indice
    input_to_function = {}
    choice_labels = {}
    
    for alias, (func, use_for) in search_functions.items():
        module_name = alias.split("_")[0]
        try:
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')
            site_index = str(getattr(mod, 'indice'))
            input_to_function[site_index] = func
            choice_labels[site_index] = (module_name.capitalize(), use_for.lower())
        except Exception as e:
            console.print(f"[red]Error mapping module {module_name}: {str(e)}")

    # Display the category legend
    legend_text = " | ".join([f"[{color}]{category.capitalize()}[/{color}]" for category, color in color_map.items()])
    console.print(f"\n[bold green]Category Legend:[/bold green] {legend_text}")

    # Construct prompt with proper color mapping
    prompt_message = "[green]Insert category [white](" + ", ".join(
        [f"[{color_map.get(label[1], 'white')}]{key}: {label[0]}[/{color_map.get(label[1], 'white')}]" 
         for key, label in choice_labels.items()]
    ) + "[white])"

    if TELEGRAM_BOT:
        category_legend_str = "Categorie: \n" + " | ".join([
            f"{category.capitalize()}" for category in color_map.keys()
        ])

        prompt_message = "Inserisci il sito:\n" + "\n".join(
            [f"{key}: {label[0]}" for key, label in choice_labels.items()]
        )

        console.print(f"\n{prompt_message}")

        category = bot.ask(
            "select_provider",
            f"{category_legend_str}\n\n{prompt_message}",
            None
        )

    else:
        category = msg.ask(prompt_message, choices=list(choice_labels.keys()), default="0", show_choices=False, show_default=False)

    # Run the corresponding function based on user input
    if category in input_to_function:
        run_function(input_to_function[category], search_terms=search_terms)
        
    else:
        if TELEGRAM_BOT:
            bot.send_message(f"Categoria non valida", None)

        console.print("[red]Invalid category.")

        if NOT_CLOSE_CONSOLE:
            restart_script()

        else:
            force_exit()

            if TELEGRAM_BOT:
                bot.send_message(f"Chiusura in corso", None)

                # Delete script_id
                script_id = TelegramSession.get_session()
                if script_id != "unknown":
                    TelegramSession.deleteScriptId(script_id)