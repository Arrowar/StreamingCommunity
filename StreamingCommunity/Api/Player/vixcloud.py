# 01.03.24

import sys
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# External libraries
import httpx
from bs4 import BeautifulSoup
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.config_json import config_manager
from .Helper.Vixcloud.util import WindowVideo, WindowParameter, StreamsCollection
from .Helper.Vixcloud.js_parser import JavaScriptParser


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")
console = Console()


class VideoSource:
    def __init__(self, url: str, is_series: bool):
        """
        Initialize video source for streaming site.
        
        Args:
            - url (str): The URL of the streaming site.
            - is_series (bool): Flag for series or movie content
        """
        self.headers = {'user-agent': get_userAgent()}
        self.url = url
        self.is_series = is_series

    def setup(self, media_id: int):
        """
        Configure media-specific context.
        
        Args:
            media_id (int): Unique identifier for media item
        """
        self.media_id = media_id

    def get_iframe(self, episode_id: int) -> None:
        """
        Retrieve iframe source for specified episode.
        
        Args:
            episode_id (int): Unique identifier for episode
        """
        params = {}

        if self.is_series:
            params = {
                'episode_id': episode_id, 
                'next_episode': '1'
            }

        try:
            response = httpx.get(f"{self.url}/iframe/{self.media_id}", params=params, timeout=MAX_TIMEOUT)
            response.raise_for_status()

            # Parse response with BeautifulSoup to get iframe source
            soup = BeautifulSoup(response.text, "html.parser")
            self.iframe_src = soup.find("iframe").get("src")

        except Exception as e:
            logging.error(f"Error getting iframe source: {e}")
            raise

    def parse_script(self, script_text: str) -> None:
        """
        Convert raw script to structured video metadata.
        
        Args:
            script_text (str): Raw JavaScript/HTML script content
        """
        try:
            converter = JavaScriptParser.parse(js_string=str(script_text))

            # Create window video, streams and parameter objects
            self.canPlayFHD = bool(converter.get('canPlayFHD'))
            self.window_video = WindowVideo(converter.get('video'))
            self.window_streams = StreamsCollection(converter.get('streams'))
            self.window_parameter = WindowParameter(converter.get('masterPlaylist'))

        except Exception as e:
            logging.error(f"Error parsing script: {e}")
            raise

    def get_content(self) -> None:
        """
        Fetch and process video content from iframe source.
        
        Workflow:
            - Validate iframe source
            - Retrieve content
            - Parse embedded script
        """
        try:
            if self.iframe_src is not None:
                response = httpx.get(self.iframe_src, headers=self.headers, timeout=MAX_TIMEOUT)
                response.raise_for_status()

                # Parse response with BeautifulSoup to get content
                soup = BeautifulSoup(response.text, "html.parser")
                script = soup.find("body").find("script").text

                # Parse script to get video information
                self.parse_script(script_text=script)

        except Exception as e:
            logging.error(f"Error getting content: {e}")
            raise

    def get_playlist(self) -> str:
        """
        Generate authenticated playlist URL.

        Returns:
            str: Fully constructed playlist URL with authentication parameters
        """
        params = {}

        # Add 'h' parameter if video quality is 1080p
        if self.canPlayFHD:
            params['h'] = 1

        # Parse the original URL
        parsed_url = urlparse(self.window_parameter.url)
        query_params = parse_qs(parsed_url.query)

        # Check specifically for 'b=1' in the query parameters
        if 'b' in query_params and query_params['b'] == ['1']:
            params['b'] = 1

        # Add authentication parameters (token and expiration)
        params.update({
            "token": self.window_parameter.token,
            "expires": self.window_parameter.expires
        })

        # Build the updated query string
        query_string = urlencode(params)

        # Construct the new URL with updated query parameters
        return urlunparse(parsed_url._replace(query=query_string))


class VideoSourceAnime(VideoSource):
    def __init__(self, url: str):
        """
        Initialize anime-specific video source.
        
        Args:
            - url (str): The URL of the streaming site.
        
        Extends base VideoSource with anime-specific initialization
        """
        self.headers = {'user-agent': get_userAgent()}
        self.url = url
        self.src_mp4 = None

    def get_embed(self, episode_id: int):
        """
        Retrieve embed URL and extract video source.
        
        Args:
            episode_id (int): Unique identifier for episode
        
        Returns:
            str: Parsed script content
        """
        try:
            response = httpx.get(f"{self.url}/embed-url/{episode_id}", headers=self.headers, timeout=MAX_TIMEOUT)
            response.raise_for_status()

            # Extract and clean embed URL
            embed_url = response.text.strip()
            self.iframe_src = embed_url

            # Fetch video content using embed URL
            video_response = httpx.get(embed_url)
            video_response.raise_for_status()

            # Parse response with BeautifulSoup to get content of the scriot
            soup = BeautifulSoup(video_response.text, "html.parser")
            script = soup.find("body").find("script").text
            self.src_mp4 = soup.find("body").find_all("script")[1].text.split(" = ")[1].replace("'", "")

            return script
        
        except Exception as e:
            logging.error(f"Error fetching embed URL: {e}")
            return None