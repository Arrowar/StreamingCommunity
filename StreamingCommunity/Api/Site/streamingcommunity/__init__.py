# 21.05.24
# Correzioni applicate per una migliore integrazione con Telegram Bot

import sys
import subprocess
# from urllib.parse import quote_plus # Non sembra usata qui

# External library
from rich.console import Console
from rich.prompt import Prompt # Usata solo se non è Telegram Bot

# Internal utilities
from StreamingCommunity.Api.Template import get_select_title # CRUCIALE per il problema della selezione "0"
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaItem
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance

# Logic class
from .site import title_search, table_show_manager, media_search_manager
from .film import download_film
from .series import download_series

# Variable
indice = 0
_useFor = "Film_&_Serie"
_priority = 0
_engineDownload = "hls"
_deprecate = False

# msg e console sono usati principalmente per l'output/input da terminale
msg = Prompt()
console = Console()


def get_user_input(string_to_search: str = None):
    """
    Asks the user to input a search term.
    Handles both Telegram bot input and direct input.
    """
    # Se string_to_search è già fornito (es. da riga di comando o chiamata precedente), usalo.
    if string_to_search is not None:
        return string_to_search.strip()

    # Altrimenti, chiedi all'utente
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()
        user_response = bot.ask(
            "key_search", # Tipo di richiesta
            "Enter the search term\nor type 'back' to return to the menu: ", # Messaggio per l'utente
            None # Nessuna scelta predefinita, l'utente digita
        )

        if user_response is None: # Timeout o nessun input
            bot.send_message("Timeout: Nessun termine di ricerca inserito.", None)
            return None # Indica che non c'è input

        if user_response.lower() == 'back':
            bot.send_message("Ritorno al menu principale...", None)
            # Gestire il "back" qui è complesso perché Popen e sys.exit terminano lo script corrente.
            # Idealmente, la logica di "back" dovrebbe essere gestita dal chiamante (run.py)
            # o restituendo un valore speciale. Per ora, manteniamo il riavvio ma è subottimale.
            try:
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit()
            except Exception as e:
                bot.send_message(f"Errore durante il tentativo di riavvio: {e}", None)
                return None # Non continuare se il riavvio fallisce
        
        return user_response.strip()
    else:
        # Input da console
        return msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

def process_search_result(select_title, selections=None):
    """
    Handles the search result and initiates the download for either a film or series.
    
    Parameters:
        select_title (MediaItem): The selected media item. Può essere None se la selezione fallisce.
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input
                                    {'season': season_selection, 'episode': episode_selection}
    """
    if not select_title: # Se select_title è None (es. l'utente non ha scelto o errore in get_select_title)
        if site_constant.TELEGRAM_BOT:
            bot = get_bot_instance()
            bot.send_message("Nessun titolo selezionato o selezione annullata.", None)
        else:
            console.print("[yellow]Nessun titolo selezionato o selezione annullata.")
        return # Esce se non c'è un titolo valido

    if select_title.type == 'tv':
        season_selection = None
        episode_selection = None
        
        if selections:
            season_selection = selections.get('season')
            episode_selection = selections.get('episode')

        download_series(select_title, season_selection, episode_selection)
    else:
        download_film(select_title)

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None):
    """
    Main function of the application for search.

    Parameters:
        string_to_search (str, optional): String to search for. Può essere passato da run.py.
        get_onlyDatabase (bool, optional): If True, return only the database object.
        direct_item (dict, optional): Direct item to process (bypass search).
        selections (dict, optional): Dictionary containing selection inputs that bypass manual input.
    """
    bot = None # Inizializza bot a None
    if site_constant.TELEGRAM_BOT:
        bot = get_bot_instance()

    if direct_item:
        # Se un item è fornito direttamente, lo processa e esce.
        # Utile per test o integrazioni future.
        select_title_obj = MediaItem(**direct_item)
        process_search_result(select_title_obj, selections)
        return

    # CORREZIONE BUG 1: Usa get_user_input per ottenere il termine di ricerca
    # string_to_search qui è quello passato come argomento alla funzione search.
    actual_search_query = get_user_input(string_to_search)
    if string_to_search is None:
        if site_constant.TELEGRAM_BOT:
            bot = get_bot_instance()
            string_to_search = bot.ask(
                "key_search",
                f"Enter the search term\nor type 'back' to return to the menu: ",
                None
            )

            if string_to_search == 'back':

                # Restart the script
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit()
        else:
            string_to_search = msg.ask(f"\n[purple]Insert a word to search in [green]{site_constant.SITE_NAME}").strip()

    if not actual_search_query: # Se l'utente ha scritto 'back' (gestito da get_user_input) o input vuoto/timeout
        if bot: # Invia messaggio solo se è in modalità bot e non è già stato gestito da 'back'
             if actual_search_query is None : # Solo se è None (timeout/errore), 'back' esce prima
                bot.send_message("Termine di ricerca non fornito. Ritorno al menu precedente.", None)
        # Non fare nulla, la funzione termina e run.py (o chi per esso) dovrebbe ripresentare il menu.
        return

    # Esegue la ricerca sul database (usando .site.title_search)
    # title_search (da site.py) MOSTRA la lista dei risultati all'utente via bot.
    len_database = title_search(actual_search_query)

    if get_onlyDatabase:
        # Se richiesto, restituisce solo il gestore del database e non procede con la selezione.
        return media_search_manager
    
    if len_database > 0:
        # Se ci sono risultati, chiama get_select_title per chiedere all'utente quale selezionare.
        # È DENTRO get_select_title CHE SI NASCONDE IL PROBLEMA DELLA SELEZIONE "0".
        select_title_obj = get_select_title(
            table_show_manager, # Usato per la visualizzazione tabellare in console
            media_search_manager, # Contiene i dati dei media trovati da title_search
            len_database # Passa il numero di risultati disponibili per la validazione dell'input
        )
        
        # select_title_obj sarà il MediaItem scelto, o None se la selezione fallisce o viene annullata.
        process_search_result(select_title_obj, selections)
    
    else:
        # CORREZIONE BUG 3: Nessun risultato trovato.
        no_results_message = f"Nessun risultato trovato per: '{actual_search_query}'"
        if bot:
            bot.send_message(no_results_message, None)
        else:
            console.print(f"\n[red]Nothing matching was found for[white]: [purple]{actual_search_query}")
        
        # NON chiamare search() ricorsivamente.
        # La funzione termina qui. Il flusso dovrebbe tornare a run.py
        # che può decidere se ripresentare il menu dei siti o chiedere un nuovo input.
        return
