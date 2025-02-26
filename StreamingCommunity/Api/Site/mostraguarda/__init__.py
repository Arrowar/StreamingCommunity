# 26.05.24

from urllib.parse import quote_plus


# External library
from rich.console import Console
from rich.prompt import Prompt, Confirm


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Lib.TMBD import tmdb, Json_film
from .film import download_film


# Variable
indice = 9
_useFor = "film"
_deprecate = False
_priority = 2
_engineDownload = "hls"

msg = Prompt()
console = Console()


def search(string_to_search: str = None, get_onylDatabase: bool = False):
    """
    Main function of the application for film and series.
    """

    if string_to_search is None:
        string_to_search = msg.ask(f"\n[purple]Insert word to search in [green]{site_constant.SITE_NAME}").strip()

    # Not available for the moment
    if get_onylDatabase:
        return 0

    # Search on database
    movie_id = tmdb.search_movie(quote_plus(string_to_search))

    if movie_id is not None:
        movie_details: Json_film = tmdb.get_movie_details(tmdb_id=movie_id)

        # Download only film
        download_film(movie_details)

    else:
        console.print(f"\n[red]Nothing matching was found for[white]: [purple]{string_to_search}")

        # Retry
        search()