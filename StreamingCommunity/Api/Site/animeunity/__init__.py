# 21.05.24

import sys
import subprocess


# Internal utilities
from StreamingCommunity.Util.console import console, msg
from StreamingCommunity.Api.Template import get_select_title
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from .site import title_search, media_search_manager, table_show_manager
from .film_serie import download_film, download_series


# Variable
indice = 1
_useFor = "anime"
_deprecate = False
_priority = 2
_engineDownload = "mp4"
from .costant import SITE_NAME, TELEGRAM_BOT


def search(string_to_search: str = None, get_onylDatabase: bool = False):

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

    # Search on database
    len_database = title_search(string_to_search)

    # Return list of elements
    if get_onylDatabase:
        return media_search_manager

    if len_database > 0:

        # Select title from list (type: TV \ Movie \ OVA)
        select_title = get_select_title(table_show_manager, media_search_manager)

        if select_title.type == 'Movie' or select_title.type == 'OVA':
            download_film(select_title)

        else:
            download_series(select_title)
            
    else:
        if TELEGRAM_BOT:
            bot.send_message(f"Nessun risultato trovato riprova", None)
          
        console.print(f"\n[red]Nothing matching was found for[white]: [purple]{string_to_search}")

        # Retry
        search()