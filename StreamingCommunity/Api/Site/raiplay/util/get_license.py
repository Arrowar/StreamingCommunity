# 16.03.25


# External library
import httpx


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_headers


# Variable
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")



def generate_license_url(mpd_id: str):
    """
    Generates the URL to obtain the Widevine license.

    Args:
        mpd_id (str): The ID of the MPD (Media Presentation Description) file.

    Returns:
        str: The full license URL.
    """
    params = {
        'cont': mpd_id,
        'output': '62',
    }

    response = httpx.get('https://mediapolisvod.rai.it/relinker/relinkerServlet.htm', params=params, headers=get_headers(), timeout=MAX_TIMEOUT)
    response.raise_for_status() 

    # Extract the license URL from the response in two lines
    json_data = response.json()
    license_url = json_data.get('licence_server_map').get('drmLicenseUrlValues')[0].get('licenceUrl')

    return license_url