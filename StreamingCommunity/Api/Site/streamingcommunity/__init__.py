# 21.05.24

import sys
import subprocess
from urllib.parse import quote_plus


# Internal utilities
from StreamingCommunity.Util.console import console, msg
from StreamingCommunity.Api.Template import get_select_title
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from .site import get_version_and_domain, title_search, table_show_manager, media_search_manager
from .film import download_film
from .series import download_series


# Variable
indice = 0
_useFor = "film_serie"
_deprecate = False
_priority = 1
_engineDownload = "hls"
from .costant import SITE_NAME, TELEGRAM_BOT


def search(string_to_search: str = None, get_onylDatabase: bool = False):
    """
    Main function of the application for film and series.
    """
    if TELEGRAM_BOT:
        bot = get_bot_instance()

        if string_to_search is None:
            
            # Chiedi la scelta all'utente con il bot Telegram
            string_to_search = bot.ask(
                "key_search",
                f"Inserisci la parola da cercare\noppure 🔙 back per tornare alla scelta: ",
                None
            )

            if string_to_search == 'back':
                # Riavvia lo script
                # Chiude il processo attuale e avvia una nuova istanza dello script
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit()
    
    else:
        if string_to_search is None:
            string_to_search = msg.ask(f"\n[purple]Insert word to search in [green]{SITE_NAME}").strip()

    # Get site domain and version and get result of the search
    site_version, domain = get_version_and_domain()
    len_database = title_search(quote_plus(string_to_search), domain)

    # Return list of elements
    if get_onylDatabase:
        return media_search_manager
    
    if len_database > 0:

        # Select title from list
        select_title = get_select_title(table_show_manager, media_search_manager)
        
        if select_title.type == 'tv':
            download_series(select_title, site_version)
        
        else:
            download_film(select_title)
    
    else:
        console.print(f"\n[red]Nothing matching was found for[white]: [purple]{string_to_search}")

        if TELEGRAM_BOT:
          bot.send_message(f"Nessun risultato trovato riprova", None)

        # Retry
        search()