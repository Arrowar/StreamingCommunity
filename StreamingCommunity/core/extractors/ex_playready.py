# 29.12.25

from urllib.parse import urlencode


# External libraries
from curl_cffi import requests
from rich.console import Console
from pyplayready.cdm import Cdm
from pyplayready.device import Device
from pyplayready.system.pssh import PSSH


# Variable
console = Console()


def get_playready_keys(pssh: str, license_url: str, cdm_device_path: str, headers: dict = None, query_params: dict = None, key: str = None):
    """
    Extract PlayReady CONTENT keys (KID/KEY) from a license using pyplayready.

    Args:
        - pssh (str): PSSH base64 or PlayReady PRO header.
        - license_url (str): PlayReady license URL.
        - cdm_device_path (str): Path to CDM file (device.prd).
        - headers (dict): Optional HTTP headers for the license request.
        - query_params (dict): Optional query parameters to append to the URL.
        - key (str): Optional raw license data to bypass HTTP request.

    Returns:
        list: List of dicts {'kid': ..., 'key': ...} (only CONTENT keys) or None if error.
    """
    if cdm_device_path is None:
        console.print("[red]Device prd path is None.")
        return None
    
    device = Device.load(cdm_device_path)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()

    try:
        console.print(f"[cyan]PSSH [yellow](PR)[white]: [green]{pssh}")
        
        try:
            pssh_obj = PSSH(pssh)
        except Exception as e:
            console.print(f"[red]Invalid PlayReady PSSH/PRO header: {e}")
            return None
        
        if not pssh_obj.wrm_headers:
            console.print("[red]No WRM headers found in PSSH")
            return None
            
        challenge = cdm.get_license_challenge(session_id, pssh_obj.wrm_headers[0])
        
        # With request license
        if key is None:

            # Build request URL with query params
            request_url = license_url
            if query_params:
                request_url = f"{license_url}?{urlencode(query_params)}"

            # Prepare headers
            req_headers = headers.copy() if headers else {}
            request_kwargs = {}
            request_kwargs['data'] = challenge

            # Keep original Content-Type or default to text/xml for PlayReady
            if 'Content-Type' not in req_headers:
                req_headers['Content-Type'] = 'text/xml; charset=utf-8'

            if license_url is None:
                console.print("[red]License URL is None.")
                return None

            response = requests.post(request_url, headers=req_headers, impersonate="chrome124", **request_kwargs)

            if response.status_code != 200:
                console.print(f"[red]License error: {response.status_code}, {response.text}")
                return None

            # Parse license
            try:
                cdm.parse_license(session_id, response.text)
            except Exception as e:
                console.print(f"[red]Error parsing license: {e}")
                return None

            # Extract CONTENT keys
            content_keys = []
            for key_obj in cdm.get_keys(session_id):
                kid = key_obj.key_id.hex
                key_val = key_obj.key.hex()
                content_keys.append(f"{kid.replace('-', '').strip()}:{key_val.replace('-', '').strip()}")

            # Return keys
            for i, key in enumerate(content_keys):
                console.print(f"    [yellow]{i}) [cyan]Extracted kid: [red]{key.split(':')[0]} [cyan]| key: [green]{key.split(':')[1]}")
            return content_keys

        else:
            content_keys = []
            content_keys.append(f"{key.split(':')[0].replace('-', '').strip()}:{key.split(':')[1].replace('-', '').strip()}")
            return content_keys
    
    finally:
        cdm.close(session_id)