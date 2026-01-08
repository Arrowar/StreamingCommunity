# 28.07.25

import logging
from typing import Tuple, List, Dict, Optional


# Internal utilities
from .client import CrunchyrollClient


def _find_token_recursive(obj) -> Optional[str]:
    """Recursively search for 'token' field in playback response."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == "token" and isinstance(v, str) and len(v) > 10:
                return v
            token = _find_token_recursive(v)
            if token:
                return token
    elif isinstance(obj, list):
        for el in obj:
            token = _find_token_recursive(el)
            if token:
                return token
    return None


def _extract_subtitles(data: Dict) -> List[Dict]:
    """Extract all subtitles from playback data."""
    subtitles = []
    
    # Process regular subtitles
    subs_obj = data.get('subtitles') or {}
    for lang, info in subs_obj.items():
        if not info or not info.get('url'):
            continue

        subtitles.append({
            'language': lang,
            'url': info['url'],
            'format': info.get('format'),
            'type': info.get('type'),
            'closed_caption': bool(info.get('closed_caption')),
            'label': info.get('display') or info.get('title') or info.get('language')
        })

    # Process captions/closed captions
    captions_obj = data.get('captions') or data.get('closed_captions') or {}
    for lang, info in captions_obj.items():
        if not info or not info.get('url'):
            continue

        subtitles.append({
            'language': lang,
            'url': info['url'],
            'format': info.get('format'),
            'type': info.get('type') or 'captions',
            'closed_caption': True if info.get('closed_caption') is None else bool(info.get('closed_caption')),
            'label': info.get('display') or info.get('title') or info.get('language')
        })

    return subtitles


def get_playback_session(client: CrunchyrollClient, url_id: str, main_guid: Optional[str] = None) -> Tuple[str, Dict, List[Dict], Optional[str], Optional[str]]:
    """
    Get playback session with SINGLE API call.
    If main_guid is provided, fetch subtitles from main track for complete subs.
    
    Returns:
        - mpd_url: str
        - headers: Dict
        - subtitles: List[Dict]
        - token: Optional[str]
        - audio_locale: Optional[str]
    """
    playback_data = client.get_streams(url_id)

    # Extract relevant data
    mpd_url = playback_data.get('url')
    audio_locale = playback_data.get('audio_locale') or playback_data.get('audio', {}).get('locale')
    token = playback_data.get("token") or _find_token_recursive(playback_data)
    
    # Get subtitles: prefer main_guid for complete subtitles if available
    if main_guid and main_guid != url_id:
        try:
            # Fetch subtitles from main track
            main_playback_data = client.get_streams(main_guid)
            subtitles = _extract_subtitles(main_playback_data)
            
            # Deauth main track token
            main_token = main_playback_data.get("token") or _find_token_recursive(main_playback_data)
            if main_token:
                client.deauth_video(main_guid, main_token)

        except Exception as e:
            logging.error(f"Failed to fetch subtitles from main track: {e}")
            subtitles = _extract_subtitles(playback_data)

    else:
        subtitles = _extract_subtitles(playback_data)
    
    # Immediately deauth to free stream slot (non-blocking)
    if token:
        try:
            client.deauth_video(url_id, token)
        except Exception as e:
            logging.error(f"Deauth during playback failed: {e}")
    
    headers = client._get_headers()
    return mpd_url, headers, subtitles, token, audio_locale