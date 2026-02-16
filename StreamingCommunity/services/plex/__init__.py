# 12.02.26

# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import TVShowManager
from StreamingCommunity.services._base import site_constants, EntriesManager, Entries
from StreamingCommunity.services._base.site_search_manager import base_process_search_result, base_search


# Logic
from .downloader import download_series, download_film
from .client import get_client


# Variable
indice = 18
_useFor = "Film_Serie"
_drm = ["widevine", "playready"]
msg = Prompt()
console = Console()
entries_manager = EntriesManager()
table_show_manager = TVShowManager()


def title_search(query: str) -> int:
    """
    Search for titles based on a search query on Plex.
    """
    entries_manager.clear()
    table_show_manager.clear()

    api = get_client()
    search_url = "https://discover.provider.plex.tv/library/search/"
    
    params = {
        "searchProviders": "discover,plexAVOD,plexFAST",
        "includeGroups": "1",
        "searchTypes": "all,livetv,movies,tv,people",
        "includeMetadata": "1",
        "filterPeople": "1",
        "limit": "10",
        "query": query,
    }

    try:
        response = api.client.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request search error: {e}")
        return 0

    for result_group in data.get("MediaContainer", {}).get("SearchResults", []):
        group_id = result_group.get("id", "")
        if group_id not in ["plex", "external"]:
            continue
        
        for result in result_group.get("SearchResult", []):
            metadata = result.get("Metadata", {})
            kind = metadata.get("type")
            slug = metadata.get("slug")
            
            # Skip if not movie or show
            if kind not in ["movie", "show"]:
                continue
            
            # For free content, check source
            source = metadata.get("source", "")
            if "provider://tv.plex.provider.vod" not in source and "provider://tv.plex.provider.discover" not in source:
                continue
            
            if kind and slug:
                entries_manager.add(Entries(
                    id=slug,
                    slug=slug,
                    name=metadata.get("title", "No Title"),
                    type="tv" if kind == "show" else "film",
                    image=metadata.get("thumb") or metadata.get("art"),
                    year=metadata.get("year", "9999"),
                    url=f"https://watch.plex.tv/{kind}/{slug}"
                ))

    return len(entries_manager.media_list)


# WRAPPING FUNCTIONS
def process_search_result(select_title, selections=None, scrape_serie=None):
    """
    Wrapper for the generalized process_search_result function.
    """
    return base_process_search_result(
        select_title=select_title,
        download_film_func=download_film,
        download_series_func=download_series,
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