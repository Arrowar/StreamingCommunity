# 26.05.24

from urllib.parse import quote_plus


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import TVShowManager
from StreamingCommunity.utils.tmdb_client import tmdb
from StreamingCommunity.services._base import site_constants, EntriesManager, Entries
from StreamingCommunity.services._base.site_search_manager import base_process_search_result, base_search


# Logic
from .downloader import download_film


# Variable
indice = 2
_useFor = "Film"
_deprecate = True
_priority = 2
_engineDownload = "hls"

msg = Prompt()
console = Console()
entries_manager = EntriesManager()
table_show_manager = TVShowManager()


def title_search(query: str) -> int:
    """
    Search for titles based on a search query using TMDB.
      
    Parameters:
        - query (str): The query to search for.

    Returns:
        int: The number of titles found.
    """
    entries_manager.clear()
    table_show_manager.clear()

    # Search on TMDB
    movie_id = tmdb.search_movie(quote_plus(query))

    if movie_id is not None:
        movie_details = tmdb.get_movie_details(tmdb_id=movie_id)

        # Create Entries object
        media_item = Entries(
            id=movie_id,
            name=movie_details['title'],
            slug='',
            path_id=None,
            type='film',
            url='',  # Not needed for download
            poster=None,
            imdb_id=movie_details['imdb_id']
        )

        print("add to manager: ", media_item.__dict__)
        entries_manager.add(media_item)
  
    return len(entries_manager)


# WRAPPING FUNCTIONS
def process_search_result(select_title, selections=None, scrape_serie=None):
    """
    Wrapper for the generalized process_search_result function.
    """
    return base_process_search_result(
        select_title=select_title,
        download_film_func=download_film,
        download_series_func=None,
        media_search_manager=entries_manager,
        table_show_manager=table_show_manager,
        selections=selections,
        scrape_serie=scrape_serie
    )

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None, scrape_serie=None):
    """
    Wrapper for the generalized search function.
    """
    return base_search(
        title_search_func=title_search,
        process_result_func=process_search_result,
        media_search_manager=entries_manager,
        table_show_manager=table_show_manager,
        site_name=site_constants.SITE_NAME,
        string_to_search=string_to_search,
        get_onlyDatabase=get_onlyDatabase,
        direct_item=direct_item,
        selections=selections,
        scrape_serie=scrape_serie
    )