# 21.03.25

import logging


# External libraries


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.http_client import create_client


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")
REQUEST_VERIFY = config_manager.get_bool('REQUESTS', 'verify')

class VideoSource:
    def __init__(self, site_url, episode_data, session_id, csrf_token):
        """Initialize the VideoSource with session details, episode data, and URL."""
        self.session_id = session_id
        self.csrf_token = csrf_token
        self.episode_data = episode_data
        self.number = episode_data['number']
        self.link = site_url + episode_data['link']
        
        # Create an HTTP client with session cookies, headers, and base URL.
        self.client = create_client(
            cookies={"sessionId": session_id},
            headers={"User-Agent": get_userAgent(), "csrf-token": csrf_token}
        )

    def get_playlist(self):
        """Fetch the download link from AnimeWorld using the episode link."""
        try:
            # Make a POST request to the episode link and follow any redirects
            res = self.client.post(self.link, follow_redirects=True)
            data = res.json()

            # Extract the first available server link and return it after modifying the URL
            server_link = data["links"]["9"][list(data["links"]["9"].keys())[0]]["link"]
            return server_link.replace('download-file.php?id=', '')

        except Exception as e:
            logging.error(f"Error in new API system: {e}")
            return None
