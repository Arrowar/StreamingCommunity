# 16.03.25

import json
import time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET


# External library
import httpx
from rich.console import Console
try:
    from seleniumbase import Driver
    SELENIUMBASE_AVAILABLE = True
except ImportError:
    SELENIUMBASE_AVAILABLE = False
    Driver = None


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_headers, get_userAgent


# Variable
console = Console()
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")
beToken = None
network_data = []


def save_network_data(data):
    """Save network data and check for beToken"""
    global network_data
    
    # Filter only for login API responses
    if data.get('method') == 'Network.responseReceived':
        params = data.get('params', {})
        response = params.get('response', {})
        url = response.get('url', '')
        
        if "persona/login/v2.0" in url and params.get('type') != 'Preflight':
            network_data.append(data)
            console.print(f"[green]Found login API request to: {url}")


def generate_betoken(username: str, password: str, sleep_action: float = 1.0) -> str:
    """Generate beToken using browser automation"""
    
    if not SELENIUMBASE_AVAILABLE:
        console.print("[red]Error: seleniumbase is not installed. Cannot perform browser login.")
        console.print("[yellow]Install seleniumbase with: pip install seleniumbase")
        return None
    
    if not Driver:
        console.print("[red]Error: seleniumbase Driver is not available.")
        return None
    
    driver = Driver(uc=True, uc_cdp_events=True, incognito=True, headless=True)
    
    try:
        console.print("[cyan]Launching browser...")
        be_token_holder = {"token": None}
        global network_data
        network_data = []  # Reset network data

        # Load home page
        console.print("[cyan]Navigating to Mediaset Play...")
        driver.uc_open_with_reconnect("https://www.mediasetplay.mediaset.it", sleep_action)
        
        # Add CDP listeners after opening the page
        driver.add_cdp_listener(
            "Network.responseReceived",
            lambda data: save_network_data(data)
        )
        driver.sleep(sleep_action)

        # Accept privacy policy if present
        try:
            driver.click("#rti-privacy-accept-btn-screen1-id", timeout=3)
        except Exception:
            pass

        # Click Login using the specific div structure
        console.print("[cyan]Clicking login button...")
        try:
            driver.click('div.dwv_v span:contains("Login")', timeout=5)
        except Exception as e:
            print(f"Error clicking login: {e}")
            try:
                driver.click('div.dwv_v', timeout=3)
            except Exception:
                pass

        driver.sleep(sleep_action)

        # Click "Accedi con email e password" using the specific input
        console.print("[cyan]Clicking email/password login...")
        try:
            driver.click('input.gigya-input-submit[value="Accedi con email e password"]', timeout=5)
        except Exception as e:
            print(f"Error clicking email login: {e}")
            return None

        driver.sleep(sleep_action)

        # Fill login credentials using specific IDs
        console.print("[cyan]Filling login credentials...")
        try:
            email_input = 'input[name="username"].gigya-input-text'
            driver.wait_for_element(email_input, timeout=5)
            driver.type(email_input, username)
            
            password_input = 'input[name="password"].gigya-input-password'
            driver.wait_for_element(password_input, timeout=5)
            driver.type(password_input, password)
            
        except Exception as e:
            print(f"Error filling credentials: {e}")
            return None

        driver.sleep(sleep_action)

        # Click Continue/Procedi using the submit button
        console.print("[cyan]Clicking continue button...")
        try:
            driver.click('input.gigya-input-submit[type="submit"][value="Continua"]', timeout=5)
        except Exception as e:
            print(f"Error clicking continue: {e}")
            return None

        # Wait for login response and parse network data
        console.print("[cyan]Waiting for login response...")
        for attempt in range(30):
            driver.sleep(0.3)
            
            # Check network data for beToken - skip preflight requests
            for data in network_data:
                if data.get('method') == 'Network.responseReceived':
                    params = data.get('params', {})
                    response = params.get('response', {})
                    url = response.get('url', '')
                    request_type = params.get('type', '')
                    
                    if "persona/login/v2.0" in url and request_type != 'Preflight':
                        request_id = params.get('requestId')
                        
                        if request_id:
                            try:
                                response_body = driver.execute_cdp_cmd(
                                    'Network.getResponseBody', 
                                    {'requestId': request_id}
                                )
                                body = response_body.get('body', '')

                                if body:
                                    response_data = json.loads(body)
                                    be_token = response_data.get("response", {}).get("beToken")

                                    if be_token:
                                        be_token_holder["token"] = be_token
                                        console.print("[green]Login successful! BeToken found!")
                                        return be_token
                                    
                            except Exception:
                                continue

        console.print(f"[yellow]Login completed. Total network events captured: {len(network_data)}")
        return be_token_holder["token"]
        
    finally:
        driver.quit()


def get_bearer_token():
    """
    Gets the BEARER_TOKEN for authentication.

    Returns:
        str: The bearer token string.
    """
    global beToken

    # Read beToken from config if already present
    beToken = config_manager.get_dict("SITE_LOGIN", "mediasetinfinity")["beToken"]
    if beToken is not None and len(beToken) != 0:
        return beToken
        
    username = config_manager.get_dict("SITE_LOGIN", "mediasetinfinity").get("username", "")
    password = config_manager.get_dict("SITE_LOGIN", "mediasetinfinity").get("password", "")
    
    if username and password:
        if not SELENIUMBASE_AVAILABLE:
            console.print("[yellow]Warning: seleniumbase not available. Cannot perform automatic login.")
            console.print("[yellow]Please manually obtain beToken and set it in config.")
            return config_manager.get_dict("SITE_LOGIN", "mediasetinfinity")["beToken"]
        
        beToken = generate_betoken(username, password)
        
        if beToken is not None:

            # Save current beToken
            current_value = config_manager.get("SITE_LOGIN", "mediasetinfinity", dict)
            current_value["beToken"] = beToken
            config_manager.set_key("SITE_LOGIN", "mediasetinfinity", current_value)
            config_manager.save_config()

            return beToken
            
    return config_manager.get_dict("SITE_LOGIN", "mediasetinfinity")["beToken"]


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


def parse_tracking_data(tracking_value):
    """
    Parses the trackingData string into a dictionary.

    Args:
        tracking_value (str): The tracking data string.

    Returns:
        dict: Parsed tracking data.
    """
    return dict(item.split('=', 1) for item in tracking_value.split('|') if '=' in item)


def parse_smil_for_tracking_and_video(smil_xml):
    """
    Extracts all video_src and trackingData pairs from the SMIL.

    Args:
        smil_xml (str): The SMIL XML as a string.

    Returns:
        list: A list of dicts: {'video_src': ..., 'tracking_info': ...}
    """
    results = []
    root = ET.fromstring(smil_xml)
    ns = {'smil': root.tag.split('}')[0].strip('{')}

    # Search all <par>
    for par in root.findall('.//smil:par', ns):
        video_src = None
        tracking_info = None

        # Search <video> inside <par>
        video_elem = par.find('.//smil:video', ns)
        if video_elem is not None:
            video_src = video_elem.attrib.get('src')

        # Search <ref> inside <par>
        ref_elem = par.find('.//smil:ref', ns)
        if ref_elem is not None:
            # Search <param name="trackingData">
            for param in ref_elem.findall('.//smil:param', ns):
                if param.attrib.get('name') == 'trackingData':
                    tracking_value = param.attrib.get('value')
                    if tracking_value:
                        tracking_info = parse_tracking_data(tracking_value)
                    break

        if video_src and tracking_info:
            results.append({'video_src': video_src, 'tracking_info': tracking_info})

    return results


def get_tracking_info(BEARER_TOKEN, PLAYBACK_JSON):
    """
    Retrieves tracking information from the playback JSON.

    Args:
        BEARER_TOKEN (str): The authentication token.
        PLAYBACK_JSON (dict): The playback JSON object.

    Returns:
        list or None: List of tracking info dicts, or None if request fails.
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

        smil_xml = response.text
        time.sleep(0.2)
        results = parse_smil_for_tracking_and_video(smil_xml)
        return results
    
    except Exception:
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
        'releasePid': tracking_info['tracking_info'].get('pid'),
        'account': f"http://access.auth.theplatform.com/data/Account/{tracking_info['tracking_info'].get('aid')}",
        'schema': '1.0',
        'token': BEARER_TOKEN,
    }
    
    return f"{'https://widevine.entitlement.theplatform.eu/wv/web/ModularDrm/getRawWidevineLicense'}?{urlencode(params)}"