# 14.06.24

import sys
import logging


# External libraries
import httpx
from bs4 import BeautifulSoup


# Internal utilities
from Src.Util.headers import get_headers
from Src.Util._jsonConfig import config_manager


class VideoSource:

    def __init__(self) -> None:
        """
        Initializes the VideoSource object with default values.

        Attributes:
            headers (dict): A dictionary to store HTTP headers.
            cookie (dict): A dictionary to store cookies.
        """
        self.headers = {'user-agent': get_headers()}
        self.cookie = config_manager.get_dict('REQUESTS', 'index')

    def setup(self, url: str) -> None:
        """
        Sets up the video source with the provided URL.

        Args:
            url (str): The URL of the video source.
        """
        self.url = url

    def make_request(self, url: str) -> str:
        """
        Make an HTTP GET request to the provided URL.

        Args:
            url (str): The URL to make the request to.

        Returns:
            str: The response content if successful, None otherwise.
        """
        try:
            response = httpx.get(url, headers=self.headers, cookies=self.cookie)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except Exception as err:
            logging.error(f"An error occurred: {err}")
        return None

    def get_playlist(self):
        """
        Retrieves the playlist URL from the video source.

        Returns:
            tuple: The mp4 link if found, None otherwise.
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
