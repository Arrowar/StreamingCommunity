# 14.06.24

import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent


# Variable
max_timeout = config_manager.get_int("REQUESTS", "timeout")


class VideoSource:
    def __init__(self, cookie) -> None:
        """
        Initializes the VideoSource object with default values.
        """
        self.headers = {'user-agent': get_userAgent()}
        self.cookie = cookie

    def setup(self, url: str) -> None:
        """
        Sets up the video source with the provided URL.

        Parameters:
            - url (str): The URL of the video source.
        """
        self.url = url

    def make_request(self, url: str) -> str:
        """
        Make an HTTP GET request to the provided URL.

        Parameters:
            - url (str): The URL to make the request to.

        Returns:
            - str: The response content if successful, None otherwise.
        """
        try:
            response = httpx.get(
                url=url, 
                headers=self.headers, 
                cookies=self.cookie,
                timeout=max_timeout
            )
            response.raise_for_status()

            return response.text
        
        except Exception as err:
            logging.error(f"An error occurred: {err}")

        return None

    def get_playlist(self):
        """
        Retrieves the playlist URL from the video source.

        Returns:
            - tuple: The mp4 link if found, None otherwise.
        """
        try:
            text = self.make_request(self.url)

            if text:
                soup = BeautifulSoup(text, "html.parser")
                source = soup.find("source")

                if source:
                    mp4_link = source.get("src")
                    return mp4_link
            
                else:
                    logging.error("No <source> tag found in the HTML.")
                    
            else:
                logging.error("Failed to retrieve content from the URL.")

        except Exception as e:
            logging.error(f"An error occurred while parsing the playlist: {e}")