# 25.07.25

import base64
from urllib.parse import urlencode


# External libraries
from curl_cffi import requests
from rich.console import Console
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH


# Variable
console = Console()


def filter_valid_keys(content_keys: list) -> list:
    """
    Filter out invalid keys (all zeros) and return only potentially valid keys.
    
    Args:
        content_keys (list): List of key dictionaries with 'kid' and 'key' fields
    """
    valid_keys = []
    
    for key_info in content_keys:
        key_value = key_info.get('key', '').replace('-', '').strip()
        if key_value and not all(c == '0' for c in key_value):
            valid_keys.append(key_info)
    
    return valid_keys


def select_best_key(valid_keys: list) -> dict:
    """
    Select the best key from valid keys based on heuristics.
    
    Args:
        valid_keys (list): List of valid key dictionaries
    """
    if len(valid_keys) == 1:
        return valid_keys[0]
    
    # Heuristics for key selection:
    # 1. Prefer keys that are not all the same character
    # 2. Prefer keys with more entropy (variety in hex characters)
    scored_keys = []
    for key_info in valid_keys:
        key_value = key_info.get('key', '')
        score = 0
        
        # Score based on character variety
        unique_chars = len(set(key_value))
        score += unique_chars
        
        # Penalize keys with too many repeated patterns
        if len(key_value) > 8:
            
            # Check for repeating patterns
            has_pattern = False
            for i in range(2, len(key_value) // 2):
                pattern = key_value[:i]
                if key_value.startswith(pattern * (len(key_value) // i)):
                    has_pattern = True
                    break
            
            if not has_pattern:
                score += 10
        
        scored_keys.append((score, key_info))
        console.log(f"[cyan]Found key [red]{key_info.get('kid', 'unknown')}[cyan] with score: [red]{score}")
    
    # Sort by score (descending) and return the best key
    scored_keys.sort(key=lambda x: x[0], reverse=True)
    best_key = scored_keys[0][1]
    
    console.log(f"[cyan]Selected key: [red]{best_key.get('kid', 'unknown')}[cyan] with score: [red]{scored_keys[0][0]}")
    return best_key


def get_widevine_keys(pssh: str, license_url: str, cdm_device_path: str, headers: dict = None, query_params: dict =None, key: str=None):
    """
    Extract Widevine CONTENT keys (KID/KEY) from a license using pywidevine.

    Args:
        - pssh (str): PSSH base64.
        - license_url (str): Widevine license URL.
        - cdm_device_path (str): Path to CDM file (device.wvd).
        - headers (dict): Optional HTTP headers for the license request (from fetch).
        - query_params (dict): Optional query parameters to append to the URL.
        - key (str): Optional raw license data to bypass HTTP request.

    Returns:
        list: List of dicts {'kid': ..., 'key': ...} (only CONTENT keys) or None if error.
    """
    if not cdm_device_path:
        console.print("[red]Invalid CDM device path.")
        return None

    device = Device.load(cdm_device_path)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()

    try:
        console.log(f"[cyan]PSSH: [green]{pssh}")
        challenge = cdm.get_license_challenge(session_id, PSSH(pssh))
        
        # With request license
        if key is None:

            # Build request URL with query params
            request_url = license_url
            if query_params:
                request_url = f"{license_url}?{urlencode(query_params)}"

            # Prepare headers (use original headers from fetch)
            req_headers = headers.copy() if headers else {}
            request_kwargs = {}
            request_kwargs['data'] = challenge

            # Keep original Content-Type or default to octet-stream
            if 'Content-Type' not in req_headers:
                req_headers['Content-Type'] = 'application/octet-stream'

            response = requests.post(request_url, headers=req_headers, impersonate="chrome124", **request_kwargs)

            if response.status_code != 200:
                console.print(f"[red]License error: {response.status_code}, {response.text}")
                return None

            # Parse license response
            license_bytes = response.content
            content_type = response.headers.get("Content-Type", "")

            # Handle JSON response
            if "application/json" in content_type:
                try:
                    data = response.json()
                    if "license" in data:
                        license_bytes = base64.b64decode(data["license"])
                    else:
                        console.print(f"[red]'license' field not found in JSON response: {data}.")
                        return None
                except Exception as e:
                    console.print(f"[red]Error parsing JSON license: {e}")
                    return None

            if not license_bytes:
                console.print("[red]License data is empty.")
                return None

            # Parse license
            try:
                cdm.parse_license(session_id, license_bytes)
            except Exception as e:
                console.print(f"[red]Error parsing license: {e}")
                return None

            # Extract CONTENT keys
            content_keys = []
            for key in cdm.get_keys(session_id):
                if key.type == "CONTENT":
                    kid = key.kid.hex() if isinstance(key.kid, bytes) else str(key.kid)
                    key_val = key.key.hex() if isinstance(key.key, bytes) else str(key.key)

                    content_keys.append({
                        'kid': kid.replace('-', '').strip(),
                        'key': key_val.replace('-', '').strip()
                    })

            if not content_keys:
                console.print("[yellow]⚠️ No CONTENT keys found in license.")
                return None

            # Filter and select the best key
            valid_keys = filter_valid_keys(content_keys)
            
            # Select the best key automatically
            best_key = select_best_key(valid_keys)
            
            if best_key:
                console.log(f"[cyan]Selected KID: [green]{best_key['kid']} [white]| [cyan]KEY: [green]{best_key['key']}")
                
                # Return all valid keys but with the best one first
                result_keys = [best_key]
                for key_info in valid_keys:
                    if key_info['kid'] != best_key['kid']:
                        result_keys.append(key_info)
                
                return result_keys
            else:
                console.print("[red]❌ Could not select best key")
                return None
        else:
            content_keys = []
            raw_kid = key.split(":")[0]
            raw_key = key.split(":")[1]
            content_keys.append({
                'kid': raw_kid.replace('-', '').strip(),
                'key': raw_key.replace('-', '').strip()
            })

            # Return keys
            console.log(f"[cyan]KID: [green]{content_keys[0]['kid']} [white]| [cyan]KEY: [green]{content_keys[0]['key']}")
            return content_keys
    
    finally:
        cdm.close(session_id)


def get_info_wvd(cdm_device_path):
    """
    Extract device information from a Widevine CDM device file (.wvd).

    Args:
        cdm_device_path (str): Path to CDM file (device.wvd).
    """
    device = Device.load(cdm_device_path)

    # Extract client info
    info = {ci.name: ci.value for ci in device.client_id.client_info}
    caps = device.client_id.client_capabilities

    company = info.get("company_name", "N/A")
    model = info.get("model_name", "N/A")

    device_name = info.get("device_name", "").lower()
    build_info = info.get("build_info", "").lower()

    # Extract device type
    is_emulator = any(x in device_name for x in [
        "generic", "sdk", "emulator", "x86"
    ]) or "test-keys" in build_info or "userdebug" in build_info
    
    if "tv" in model.lower():
        dev_type = "Android TV"
    elif is_emulator:
        dev_type = "Android Emulator"
    else:
        dev_type = "Android Phone"

    console.print(
        f"[cyan]Load WVD: "
        f"[red]L{device.security_level} [cyan]| [red]{dev_type} [cyan]| "
        f"[red]{company} {model} [cyan]| API [red]{caps.oem_crypto_api_version} [cyan]| "
        f"[cyan]SysID: [red]{device.system_id}"
    )