# 26.11.2025

import uuid
import random


# Internal utilities
from StreamingCommunity.utils.http_client import create_client, get_headers


def generate_params():
    """Generate all params automatically"""
    device_makes = ['opera', 'chrome', 'firefox', 'safari', 'edge']
    return {
        'appName': 'web',
        'appVersion': str(random.randint(100, 999)),
        'deviceVersion': str(random.randint(100, 999)),
        'deviceModel': 'web',
        'deviceMake': random.choice(device_makes),
        'deviceType': 'web',
        'clientID': str(uuid.uuid4()),
        'clientModelNumber': f"{random.randint(1, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        'channelID': ''.join(random.choice('0123456789abcdef') for _ in range(24))
    }


def get_bearer_token():
    """Get the Bearer token required for authentication."""
    response = create_client(headers=get_headers()).get('https://boot.pluto.tv/v4/start', params=generate_params())
    return response.json()['sessionToken']


def get_playback_url_episode(id_episode):
    """Get the playback URL for a given episode ID."""
    return f"https://cfd-v4-service-stitcher-dash-use1-1.prd.pluto.tv/v2/stitch/dash/episode/{id_episode}/main.mpd"