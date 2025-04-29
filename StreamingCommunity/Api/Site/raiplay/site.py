# 21.05.24

import threading
import queue


# External libraries
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.table import TVShowManager
from StreamingCommunity.Lib.TMBD.tmdb import tmdb


# Logic class
from StreamingCommunity.Api.Template.config_loader import site_constant
from StreamingCommunity.Api.Template.Class.SearchType import MediaManager


# Variable
console = Console()
media_search_manager = MediaManager()
table_show_manager = TVShowManager()
max_timeout = config_manager.get_int("REQUESTS", "timeout")
MAX_THREADS = 12


def determine_media_type(title):
    """
    Use TMDB to determine if a title is a movie or TV show.
    """
    try:
        # First search as a movie
        movie_results = tmdb._make_request("search/movie", {"query": title})
        movie_count = len(movie_results.get("results", []))
        
        # Then search as a TV show
        tv_results = tmdb._make_request("search/tv", {"query": title})
        tv_count = len(tv_results.get("results", []))
        
        # If results found in only one category, use that
        if movie_count > 0 and tv_count == 0:
            return "film"
        elif tv_count > 0 and movie_count == 0:
            return "tv"
        
        # If both have results, compare popularity
        if movie_count > 0 and tv_count > 0:
            top_movie = movie_results["results"][0]
            top_tv = tv_results["results"][0]
            
            return "film" if top_movie.get("popularity", 0) > top_tv.get("popularity", 0) else "tv"

        return "film"
    
    except Exception as e:
        console.log(f"Error determining media type with TMDB: {e}")
        return "film"


def worker_determine_type(work_queue, result_dict, worker_id):
    """
    Worker function to process items from queue and determine media types.
    
    Parameters:
        - work_queue: Queue containing items to process
        - result_dict: Dictionary to store results
        - worker_id: ID of the worker thread
    """
    while not work_queue.empty():
        try:
            index, item = work_queue.get(block=False)
            title = item.get('titolo', '')
            media_type = determine_media_type(title)
            
            result_dict[index] = {
                'id': item.get('id', ''),
                'name': title,
                'type': media_type,
                'path_id': item.get('path_id', ''),
                'url': f"https://www.raiplay.it{item.get('url', '')}",
                'image': f"https://www.raiplay.it{item.get('immagine', '')}",
            }
            
            work_queue.task_done()

        except queue.Empty:
            break

        except Exception as e:
            console.log(f"Worker {worker_id} error: {e}")
            work_queue.task_done()


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

    search_url = f"https://www.raiplay.it/atomatic/raiplay-search-service/api/v1/msearch"
    console.print(f"[cyan]Search url: [yellow]{search_url}")

    json_data = {
        'templateIn': '6470a982e4e0301afe1f81f1',
        'templateOut': '6516ac5d40da6c377b151642',
        'params': {
            'param': query,
            'from': None,
            'sort': 'relevance',
            'onlyVideoQuery': False,
        },
    }

    try:
        response = httpx.post(
            search_url, 
            headers={'user-agent': get_userAgent()}, 
            json=json_data, 
            timeout=max_timeout, 
            follow_redirects=True
        )
        response.raise_for_status()

    except Exception as e:
        console.print(f"[red]Site: {site_constant.SITE_NAME}, request search error: {e}")
        return 0

    # Limit to only 15 results for performance
    data = response.json().get('agg').get('titoli').get('cards')
    data = data[:15] if len(data) > 15 else data
    
    # Use multithreading to determine media types in parallel
    work_queue = queue.Queue()
    result_dict = {}
    
    # Add items to the work queue
    for i, item in enumerate(data):
        work_queue.put((i, item))
    
    # Create and start worker threads
    threads = []
    for i in range(min(MAX_THREADS, len(data))):
        thread = threading.Thread(
            target=worker_determine_type,
            args=(work_queue, result_dict, i),
            daemon=True
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Add all results to media manager in correct order
    for i in range(len(data)):
        if i in result_dict:
            media_search_manager.add_media(result_dict[i])
          
    # Return the number of titles found
    return media_search_manager.get_length()