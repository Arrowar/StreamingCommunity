# 4.04.24

import random


# External library
import ua_generator


def get_headers() -> str:
    """
    Generate a random user agent to use in HTTP requests.

    Returns:
        - str: A random user agent string.
    """
    
    # Get a random user agent string from the user agent rotator
    user_agent =  ua_generator.generate().text
    return user_agent


def random_headers(referer: str = None):
    """
    Generate random HTTP headers to simulate human-like behavior.

    Returns:
        dict: Generated HTTP headers.
    """
    ua = ua_generator.generate()

    headers = {
        'User-Agent': ua.text,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US', 'en-GB', 'fr-FR', 'es-ES', 'de-DE']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }

    if referer:
        headers['Origin'] = referer
        headers['Referer'] = referer
    
    return headers