# 24.08.24

import sys


# External libraries
import httpx
from rich.console import Console


# Internal utilities
from .obj_tmbd import Json_film
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.table import TVShowManager


# Variable
console = Console()
table_show_manager = TVShowManager()
api_key = "a800ed6c93274fb857ea61bd9e7256c5"
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")


def get_select_title(table_show_manager, generic_obj):
    """
    Display a selection of titles and prompt the user to choose one.

    Returns:
        dict: The selected media item.
    """
    if not generic_obj:
        console.print("\n[red]No media items available.")
        return None
    
    # Example of available colors for columns
    available_colors = ['red', 'magenta', 'yellow', 'cyan', 'green', 'blue', 'white']
    
    # Retrieve the keys of the first item as column headers
    first_item = generic_obj[0]
    column_info = {"Index": {'color': available_colors[0]}}  # Always include Index with a fixed color

    # Assign colors to the remaining keys dynamically
    color_index = 1
    for key in first_item.keys():
        if key in ('name', 'date', 'number'):  # Custom prioritization of colors
            if key == 'name':
                column_info["Name"] = {'color': 'magenta'}
            elif key == 'date':
                column_info["Date"] = {'color': 'cyan'}
            elif key == 'number':
                column_info["Number"] = {'color': 'yellow'}

        else:
            column_info[key.capitalize()] = {'color': available_colors[color_index % len(available_colors)]}
            color_index += 1
    
    table_show_manager.add_column(column_info)

    # Populate the table with title information
    for i, item in enumerate(generic_obj):
        item_dict = {'Index': str(i)}

        for key in item.keys():
            # Ensure all values are strings for rich add table
            item_dict[key.capitalize()] = str(item[key])

        table_show_manager.add_tv_show(item_dict)

    # Run the table and handle user input
    last_command = table_show_manager.run(force_int_input=True, max_int_input=len(generic_obj))
    table_show_manager.clear()

    # Handle user's quit command
    if last_command == "q" or last_command == "quit":
        console.print("\n[red]Quit ...")
        sys.exit(0)

    # Check if the selected index is within range
    if 0 <= int(last_command) < len(generic_obj):
        return generic_obj[int(last_command)]
    
    else:
        console.print("\n[red]Wrong index")
        sys.exit(0)


class TheMovieDB:
    def __init__(self, api_key):
        """
        Initialize the class with the API key.
        
        Parameters:
            - api_key (str): The API key for authenticating requests to TheMovieDB.
        """
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self._cached_trending_tv = None
        self._cached_trending_movies = None

    def _make_request(self, endpoint, params=None):
        """
        Make a request to the given API endpoint with optional parameters.
        
        Parameters:
            - endpoint (str): The API endpoint to hit.
            - params (dict): Additional parameters for the request.
        
        Returns:
            dict: JSON response as a dictionary.
        """
        if params is None:
            params = {}

        params['api_key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        response = httpx.get(url, params=params, timeout=MAX_TIMEOUT)
        response.raise_for_status()
        
        return response.json()

    def _display_top_5(self, category: str, data, name_key='title'):
        """
        Display top 5 most popular items in a single line with colors.
        
        Parameters:
            - category (str): Category label (e.g., "Trending films", "Trending TV shows")
            - data (list): List of media items
            - name_key (str): Key to use for the name ('title' for movies, 'name' for TV shows)
        """
        # Colors for the titles
        colors = ['cyan', 'magenta', 'yellow', 'green', 'blue']
        
        # Sort by popularity and get top 5
        sorted_data = sorted(data, key=lambda x: x.get('popularity', 0), reverse=True)[:5]
        
        # Create list of colored titles
        colored_items = []
        for item, color in zip(sorted_data, colors):
            title = item.get(name_key, 'Unknown')
            colored_items.append(f"[{color}]{title}[/]")
        
        # Join with colored arrows and print with proper category label
        console.print(
            f"[bold purple]{category}:[/] {' [red]->[/] '.join(colored_items)}"
        )

    def display_trending_tv_shows(self):
        """
        Fetch and display the top 5 trending TV shows of the week.
        Uses cached data if available, otherwise makes a new request.
        """
        if self._cached_trending_tv is None:
            self._cached_trending_tv = self._make_request("trending/tv/week").get("results", [])
        
        self._display_top_5("Trending TV shows", self._cached_trending_tv, name_key='name')

    def refresh_trending_tv_shows(self):
        """
        Force a refresh of the trending TV shows cache.
        """
        self._cached_trending_tv = self._make_request("trending/tv/week").get("results", [])
        return self._cached_trending_tv

    def display_trending_films(self):
        """
        Fetch and display the top 5 trending films of the week.
        Uses cached data if available, otherwise makes a new request.
        """
        if self._cached_trending_movies is None:
            self._cached_trending_movies = self._make_request("trending/movie/week").get("results", [])
        
        self._display_top_5("Trending films", self._cached_trending_movies, name_key='title')

    def refresh_trending_films(self):
        """
        Force a refresh of the trending films cache.
        """
        self._cached_trending_movies = self._make_request("trending/movie/week").get("results", [])
        return self._cached_trending_movies
      
    def search_movie(self, movie_name: str):
        """
        Search for a movie by name and return its TMDB ID.
        
        Parameters:
            - movie_name (str): The name of the movie to search for.
        
        Returns:
            int: The TMDB ID of the selected movie.
        """
        generic_obj = []
        data = self._make_request("search/movie", {"query": movie_name}).get("results", [])
        if not data:
            console.print("No movies found with that name.", style="red")
            return None

        console.print("\nSelect a Movie:")
        for i, movie in enumerate(data, start=1):
            generic_obj.append({
                'name': movie['title'],
                'date': movie.get('release_date', 'N/A'),
                'id': movie['id']
            })

        choice = get_select_title(table_show_manager, generic_obj)
        return choice["id"]

    def get_movie_details(self, tmdb_id: int) -> Json_film:
        """
        Fetch and display details for a specific movie using its TMDB ID.

        Parameters:
            - tmdb_id (int): The TMDB ID of the movie.
        
        Returns:
            - Json_film: The movie details as a class.
        """
        movie = self._make_request(f"movie/{tmdb_id}")
        if not movie:
            console.print("Movie not found.", style="red")
            return None
        
        return Json_film(movie)

    def search_tv_show(self, tv_name: str):
        """
        Search for a TV show by name and return its TMDB ID.
        
        Parameters:
            - tv_name (str): The name of the TV show to search for.
        
        Returns:
            int: The TMDB ID of the selected TV show.
        """
        data = self._make_request("search/tv", {"query": tv_name}).get("results", [])
        if not data:
            console.print("No TV shows found with that name.", style="red")
            return None

        console.print("\nSelect a TV Show:")
        for i, show in enumerate(data, start=1):
            console.print(f"{i}. {show['name']} (First Air Date: {show.get('first_air_date', 'N/A')})")

        choice = int(input("Enter the number of the show you want: ")) - 1
        selected_show = data[choice]
        return selected_show["id"]  # Return the TMDB ID of the selected TV show

    def get_seasons(self, tv_show_id: int):
        """
        Get seasons for a given TV show.
        
        Parameters:
            - tv_show_id (int): The TMDB ID of the TV show.
        
        Returns:
            int: The season number selected by the user.
        """
        data = self._make_request(f"tv/{tv_show_id}").get("seasons", [])
        if not data:
            console.print("No seasons found for this TV show.", style="red")
            return None

        console.print("\nSelect a Season:")
        for i, season in enumerate(data, start=1):
            console.print(f"{i}. {season['name']} (Episodes: {season['episode_count']})")

        choice = int(input("Enter the number of the season you want: ")) - 1
        return data[choice]["season_number"]

    def get_episodes(self, tv_show_id: int, season_number: int):
        """
        Get episodes for a given season of a TV show.
        
        Parameters:
            - tv_show_id (int): The TMDB ID of the TV show.
            - season_number (int): The season number.
        
        Returns:
            dict: The details of the selected episode.
        """
        data = self._make_request(f"tv/{tv_show_id}/season/{season_number}").get("episodes", [])
        if not data:
            console.print("No episodes found for this season.", style="red")
            return None

        console.print("\nSelect an Episode:")
        for i, episode in enumerate(data, start=1):
            console.print(f"{i}. {episode['name']} (Air Date: {episode.get('air_date', 'N/A')})")

        choice = int(input("Enter the number of the episode you want: ")) - 1
        return data[choice]



# Output
tmdb = TheMovieDB(api_key)