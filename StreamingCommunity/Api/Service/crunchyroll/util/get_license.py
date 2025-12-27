# 28.07.25

from typing import Tuple, List, Dict, Optional


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager


# Logic
from .client import CrunchyrollClient


def _find_token_recursive(obj) -> Optional[str]:
    """Recursively search for 'token' field in playback response."""
    if hasattr(obj, 'items'):
        for k, v in obj.items():
            if str(k).lower() == "token" and v and len(str(v)) > 10:
                return str(v)
            token = _find_token_recursive(v)
            if token:
                return token
            
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
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


def _get_version_info(client: CrunchyrollClient, url_id: str) -> Dict:
    """Fetch episode version information."""
    episode_url = f'{client.api_base_url}/content/v2/cms/objects/{url_id}'
    params = {'ratings': 'true', 'locale': client.locale}
    response = client.request('GET', episode_url, params=params)
    
    if response.status_code != 200:
        return {}
    
    data = response.json()
    item = (data.get("data") or [{}])[0] or {}
    meta = item.get('episode_metadata', {}) or {}
    
    return {
        'versions': meta.get("versions") or item.get("versions") or [],
        'item': item,
        'meta': meta
    }


def _find_audio_tracks(versions: List[Dict]) -> Tuple[Optional[str], Optional[str]]:
    """Find main track and preferred audio track GUIDs based on config."""
    specific_audio_list = config_manager.get_list('M3U8_DOWNLOAD', 'specific_list_audio')
    
    main_guid = None
    selected_guid = None
    
    # First pass: find main track
    for v in versions:
        roles = v.get("roles", [])
        if "main" in roles:
            main_guid = v.get("guid")
            break
    
    # Second pass: find preferred audio from config list
    if specific_audio_list:
        for preferred_locale in specific_audio_list:
            for v in versions:
                if v.get("audio_locale") == preferred_locale:
                    selected_guid = v.get("guid")
                    print(f"\n[INFO] Selected audio: {preferred_locale}")
                    break
            if selected_guid:
                break
    
    # Fallback to main track
    if not selected_guid:
        selected_guid = main_guid
        if main_guid:
            for v in versions:
                if v.get("guid") == main_guid:
                    print(f"\n[INFO] Using main track audio: {v.get('audio_locale', 'Unknown')}")
                    break
    
    return main_guid, selected_guid


def _cleanup_token(client: CrunchyrollClient, guid: str, token: str):
    """Safely cleanup playback token."""
    if token:
        try:
            client.deauth_video(guid, token)
        except Exception:
            pass


def get_playback_session(client: CrunchyrollClient, url_id: str) -> Tuple[str, Dict, List[Dict], Optional[str], Optional[str]]:
    """
    Get playback session with correct audio track and all subtitles.
    
    Returns:
        - mpd_url: str
        - headers: Dict
        - subtitles: List[Dict]
        - token: Optional[str]
        - audio_locale: Optional[str]
    """
    # Get version information
    version_info = _get_version_info(client, url_id)
    versions = version_info.get('versions', [])
    
    if not versions:
        data = client.get_streams(url_id)
        url = data.get('url')
        audio_locale = data.get('audio_locale') or data.get('audio', {}).get('locale')
        subtitles = _extract_subtitles(data)
        token = data.get("token") or _find_token_recursive(data)
        _cleanup_token(client, url_id, token)
        
        # Print available subtitles
        if subtitles:
            print(f"\n[INFO] Available subtitles: {', '.join([s.get('language', 'Unknown') for s in subtitles])}")
        
        return url, client._get_headers(), subtitles, token, audio_locale
    
    # Find audio tracks
    main_guid, selected_guid = _find_audio_tracks(versions)
    
    # Get subtitles from main track
    subtitles = []
    if main_guid:
        main_data = client.get_streams(main_guid)
        subtitles = _extract_subtitles(main_data)
    
    # Get playback from selected audio track
    final_guid = selected_guid or url_id
    
    playback_data = client.get_streams(final_guid)
    mpd_url = playback_data.get('url')
    audio_locale = playback_data.get('audio_locale') or playback_data.get('audio', {}).get('locale')
    
    # Fallback to current track subtitles if main didn't work
    if not subtitles:
        subtitles = _extract_subtitles(playback_data)
    
    # Print available subtitles
    if subtitles:
        print(f"\n[INFO] Available subtitles: {', '.join([s.get('language', 'Unknown') for s in subtitles])}")
    
    # Cleanup
    token = playback_data.get("token") or _find_token_recursive(playback_data)
    _cleanup_token(client, final_guid, token)
    
    return mpd_url, client._get_headers(), subtitles, token, audio_locale