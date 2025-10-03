# 16.03.25

from urllib.parse import urlencode
import xml.etree.ElementTree as ET


# External library
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_headers, get_userAgent


# Variable
console = Console()
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")
network_data = []


def generate_betoken(username: str, password: str, sleep_action: float = 1.0) -> str:
    """Generate beToken using browser automation"""
    return response.json()['response']['beToken']


def get_bearer_token():
    """
    Gets the BEARER_TOKEN for authentication.

    Returns:
        str: The bearer token string.
    """
    global beToken
    beToken = generate_betoken("username", "password")
    print(f"beToken: {beToken}")
    return beToken
            


def get_playback_url(BEARER_TOKEN, CONTENT_ID):
    """
    Gets the playback URL for the specified content.

    Args:
        BEARER_TOKEN (str): The authentication token.
        CONTENT_ID (str): The content identifier.

    Returns:
        dict: The playback JSON object.
    """
    headers = get_headers()
    headers['authorization'] = f'Bearer {BEARER_TOKEN}'
    
    json_data = {
        'contentId': CONTENT_ID,
        'streamType': 'VOD'
    }

    try:
        response = httpx.post(
            'https://api-ott-prod-fe.mediaset.net/PROD/play/playback/check/v2.0',
            headers=headers,
            json=json_data,
            follow_redirects=True,
            timeout=MAX_TIMEOUT
        )
        response.raise_for_status()
        resp_json = response.json()

        # Check for PL022 error (Infinity+ rights)
        if 'error' in resp_json and resp_json['error'].get('code') == 'PL022':
            raise RuntimeError("Infinity+ required for this content.")
        
        # Check for PL402 error (TVOD not purchased)
        if 'error' in resp_json and resp_json['error'].get('code') == 'PL402':
            raise RuntimeError("Content available for rental: you must rent it first.")

        playback_json = resp_json['response']['mediaSelector']
        return playback_json
    
    except Exception as e:
        raise RuntimeError(f"Failed to get playback URL: {e}")

def parse_smil_for_media_info(smil_xml):
    """
    Extracts video streams with quality info and subtitle streams from SMIL.

    Args:
        smil_xml (str): The SMIL XML as a string.

    Returns:
        dict: {
            'videos': [{'url': str, 'quality': str, 'clipBegin': str, 'clipEnd': str, 'tracking_data': dict}, ...],
            'subtitles': [{'url': str, 'lang': str, 'type': str}, ...]
        }
    """   
    root = ET.fromstring(smil_xml)
    ns = {'smil': root.tag.split('}')[0].strip('{')}
    
    videos = []
    subtitles_raw = []
    
    # Process all <par> elements
    for par in root.findall('.//smil:par', ns):

        # Extract video information from <ref>
        ref_elem = par.find('.//smil:ref', ns)
        if ref_elem is not None:
            url = ref_elem.attrib.get('src')
            title = ref_elem.attrib.get('title', '')
            
            # Parse tracking data inline
            tracking_data = {}
            for param in ref_elem.findall('.//smil:param', ns):
                if param.attrib.get('name') == 'trackingData':
                    tracking_value = param.attrib.get('value', '')
                    tracking_data = dict(item.split('=', 1) for item in tracking_value.split('|') if '=' in item)
                    break
            
            if url and url.endswith('.mpd'):
                video_info = {
                    'url': url,
                    'title': title,
                    'tracking_data': tracking_data
                }
                videos.append(video_info)
    
        # Extract subtitle information from <textstream>
        for textstream in par.findall('.//smil:textstream', ns):
            sub_url = textstream.attrib.get('src')
            lang = textstream.attrib.get('lang', 'unknown')
            sub_type = textstream.attrib.get('type', 'unknown')
            
            if sub_url:
                subtitle_info = {
                    'url': sub_url,
                    'language': lang,
                    'type': sub_type
                }
                subtitles_raw.append(subtitle_info)
    
    # Filter subtitles: prefer VTT, fallback to SRT
    subtitles_by_lang = {}
    for sub in subtitles_raw:
        lang = sub['language']
        if lang not in subtitles_by_lang:
            subtitles_by_lang[lang] = []
        subtitles_by_lang[lang].append(sub)
    
    subtitles = []
    for lang, subs in subtitles_by_lang.items():
        vtt_subs = [s for s in subs if s['type'] == 'text/vtt']
        if vtt_subs:
            subtitles.append(vtt_subs[0])  # Take first VTT
            
        else:
            srt_subs = [s for s in subs if s['type'] == 'text/srt']
            if srt_subs:
                subtitles.append(srt_subs[0])  # Take first SRT
    
    return {
        'videos': videos,
        'subtitles': subtitles
    }

def get_tracking_info(BEARER_TOKEN, PLAYBACK_JSON):
    """
    Retrieves media information including videos and subtitles from the playback JSON.

    Args:
        BEARER_TOKEN (str): The authentication token.
        PLAYBACK_JSON (dict): The playback JSON object.

    Returns:
        dict or None: {'videos': [...], 'subtitles': [...]}, or None if request fails.
    """
    params = {
        "format": "SMIL",
        "auth": BEARER_TOKEN,
        "formats": "MPEG-DASH",
        "assetTypes": "HR,browser,widevine,geoIT|geoNo:HR,browser,geoIT|geoNo:SD,browser,widevine,geoIT|geoNo:SD,browser,geoIT|geoNo:SS,browser,widevine,geoIT|geoNo:SS,browser,geoIT|geoNo",
        "balance": "true",
        "auto": "true",
        "tracking": "true",
        "delivery": "Streaming"
    }

    if 'publicUrl' in PLAYBACK_JSON:
        params['publicUrl'] = PLAYBACK_JSON['publicUrl']

    try:
        response = httpx.get(
            PLAYBACK_JSON['url'],
            headers={'user-agent': get_userAgent()},
            params=params,
            follow_redirects=True,
            timeout=MAX_TIMEOUT
        )
        response.raise_for_status()

        results = parse_smil_for_media_info(response.text)
        return results
    
    except Exception as e:
        print(f"Error fetching tracking info: {e}")
        return None


def generate_license_url(BEARER_TOKEN, tracking_info):
    """
    Generates the URL to obtain the Widevine license.

    Args:
        BEARER_TOKEN (str): The authentication token.
        tracking_info (dict): The tracking info dictionary.

    Returns:
        str: The full license URL.
    """
    params = {
        'releasePid': tracking_info['tracking_data'].get('pid'),
        'account': f"http://access.auth.theplatform.com/data/Account/{tracking_info['tracking_data'].get('aid')}",
        'schema': '1.0',
        'token': BEARER_TOKEN,
    }
    
    return f"{'https://widevine.entitlement.theplatform.eu/wv/web/ModularDrm/getRawWidevineLicense'}?{urlencode(params)}"