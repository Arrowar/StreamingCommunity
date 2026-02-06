# 16.03.25

# External library
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from StreamingCommunity.utils import TVShowManager
from StreamingCommunity.utils.http_client import create_client, get_userAgent
from StreamingCommunity.services._base import site_constants, MediaManager, MediaItem
from StreamingCommunity.services._base.site_search_manager import base_process_search_result, base_search


# Logic
from .downloader import download_film, download_series


# Variable
indice = 2
_useFor = "Film_&_Serie"


msg = Prompt()
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()


def title_search(query: str) -> int:
    """
    Search for titles based on a search query.
      
    Parameters:
        - query (str): The query to search for.

    Returns:
        int: The number of titles found.
    """
    media_search_manager.clear()
    table_show_manager.clear()

    search_url = f"{site_constants.FULL_URL}/?story={query}&do=search&subaction=search"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    try:
        response = create_client(headers={'user-agent': get_userAgent()}).get(search_url)
        response.raise_for_status()
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, request search error: {e}")
        return 0

    # Create soup instance
    soup = BeautifulSoup(response.text, "html.parser")

    # Collect data from search results
    try:
        dle_content = soup.find("div", id="dle-content")
        if not dle_content:
            console.print("[yellow]Warning: dle-content div not found")
            return 0
        
        # Try new structure first (movie cards in col divs)
        cols = dle_content.find_all("div", class_="col")
        
        if cols:
            # New structure with movie cards
            for col in cols:
                try:
                    movie_div = col.find("div", class_="movie")
                    if not movie_div:
                        continue
                    
                    # Find movie poster with link
                    poster_div = movie_div.find("div", class_="movie-poster")
                    if not poster_div:
                        continue
                    
                    main_link = poster_div.find("a")
                    if not main_link:
                        continue
                    
                    url = main_link.get("href")
                    if not url:
                        continue
                    
                    # Get image
                    img_tag = main_link.find("img")
                    image_url = None
                    if img_tag:
                        img_src = img_tag.get("src") or img_tag.get("data-src")
                        if img_src:
                            if img_src.startswith("/"):
                                image_url = f"{site_constants.FULL_URL}{img_src}"
                            else:
                                image_url = img_src
                    
                    # Get title from movie-info section
                    info_div = movie_div.find("div", class_="movie-info")
                    if not info_div:
                        continue
                    
                    title_tag = info_div.find("h2", class_="movie-title")
                    if not title_tag:
                        continue
                    
                    title_link = title_tag.find("a")
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    
                    # Determine type based on URL
                    tipo = "tv" if "/serie-tv/" in url else "film"

                    media_search_manager.add(MediaItem(url=url, name=title, type=tipo, image=image_url))
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Error parsing col item: {e}")
                    continue
        else:
            # Fallback to old structure (box divs)
            boxes = dle_content.find_all("div", class_="box")
            
            if not boxes:
                console.print("[yellow]Warning: No movie boxes found")
                return 0
                
            for box in boxes:
                try:
                    wrapper = box.find("div", class_="wrapperImage")
                    if not wrapper:
                        continue
                    
                    # Find the main link
                    main_link = wrapper.find("a")
                    if not main_link:
                        continue
                        
                    url = main_link.get("href")
                    if not url:
                        continue
                    
                    # Get image
                    img_tag = main_link.find("img")
                    image_url = None
                    if img_tag:
                        img_src = img_tag.get("src") or img_tag.get("data-src")
                        if img_src:
                            if img_src.startswith("/"):
                                image_url = f"{site_constants.FULL_URL}{img_src}"
                            else:
                                image_url = img_src
                    
                    # Get title from info section
                    info_div = wrapper.find("div", class_="info")
                    if not info_div:
                        continue
                        
                    title_tag = info_div.find("h2", class_="titleFilm")
                    if not title_tag:
                        continue
                        
                    title_link = title_tag.find("a")
                    if not title_link:
                        continue
                        
                    title = title_link.get_text(strip=True)
                    
                    # Determine type based on URL
                    tipo = "tv" if "/serie-tv/" in url else "film"

                    media_search_manager.add(MediaItem(url=url, name=title, type=tipo, image=image_url))
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Error parsing box item: {e}")
                    continue
            
    except Exception as e:
        console.print(f"[red]Site: {site_constants.SITE_NAME}, parsing search results error: {e}")
        return 0

    # Return the number of titles found
    return media_search_manager.get_length()



# WRAPPING FUNCTIONS
def process_search_result(select_title, selections=None):
    """
    Wrapper for the generalized process_search_result function.
    """
    return base_process_search_result(
        select_title=select_title,
        download_film_func=download_film,
        download_series_func=download_series,
        media_search_manager=media_search_manager,
        table_show_manager=table_show_manager,
        selections=selections
    )

def search(string_to_search: str = None, get_onlyDatabase: bool = False, direct_item: dict = None, selections: dict = None):
    """
    Wrapper for the generalized search function.
    """
    return base_search(
        title_search_func=title_search,
        process_result_func=process_search_result,
        media_search_manager=media_search_manager,
        table_show_manager=table_show_manager,
        site_name=site_constants.SITE_NAME,
        string_to_search=string_to_search,
        get_onlyDatabase=get_onlyDatabase,
        direct_item=direct_item,
        selections=selections
    )