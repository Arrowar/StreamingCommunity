# 29.12.25

import time


# External libraries
from curl_cffi_smart import requests
from rich.console import Console
from pyplayready.cdm import Cdm
from pyplayready.device import Device
from pyplayready.system.pssh import PSSH


# Variable
console = Console()


def get_playready_keys(pssh_list: list[dict], license_url: str, cdm_device_path: str, headers: dict = None, key: str = None):
    """
    Extract PlayReady CONTENT keys (KID/KEY) from a license using pyplayready.

    Args:
        - pssh_list (list[dict]): List of dicts {'pssh': ..., 'kid': ..., 'type': ...}
        - license_url (str): PlayReady license URL.
        - cdm_device_path (str): Path to CDM file (device.prd).
        - headers (dict): Optional HTTP headers for the license request.
        - key (str): Optional raw license data to bypass HTTP request.

    Returns:
        list: List of strings "KID:KEY" (only CONTENT keys) or None if error.
    """
    if cdm_device_path is None:
        console.print("[red]Device prd path is None.")
        return None
    
    if key:
        k_split = key.split(':')
        if len(k_split) == 2:
            return [f"{k_split[0].replace('-', '').strip()}:{k_split[1].replace('-', '').strip()}"]
        return None

    device = Device.load(cdm_device_path)
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    
    all_content_keys = []

    try:
        for i, item in enumerate(pssh_list):
            pssh = item['pssh']
            kid_info = item.get('kid', 'N/A')
            type_info = item.get('type', 'unknown')
            
            console.print(f" [yellow]{i}) [cyan]PSSH [yellow](PR) [cyan]for Kid: [red]{kid_info} [cyan]Type: [red]{type_info}")
            
            try:
                pssh_obj = PSSH(pssh)
            except Exception as e:
                console.print(f"[red]Invalid PlayReady PSSH/PRO header: {e}")
                continue
            
            if not pssh_obj.wrm_headers:
                console.print("[red]No WRM headers found in PSSH")
                continue
                
            challenge = cdm.get_license_challenge(session_id, pssh_obj.wrm_headers[0])
            
            # Prepare headers
            req_headers = headers.copy() if headers else {}
            if 'Content-Type' not in req_headers:
                req_headers['Content-Type'] = 'text/xml; charset=utf-8'

            if license_url is None:
                console.print("[red]License URL is None.")
                continue

            response = requests.post(license_url, headers=req_headers, data=challenge, impersonate="chrome99")
            time.sleep(0.25)

            if response.status_code != 200:
                console.print(f"[red]License error: {response.status_code}, {response.text}")
                continue

            # Parse license
            try:
                cdm.parse_license(session_id, response.text)
            except Exception as e:
                console.print(f"[red]Error parsing license: {e}")
                continue

            # Extract CONTENT keys
            for key_obj in cdm.get_keys(session_id):
                kid = key_obj.key_id.hex.replace('-', '').strip()
                if all(c == '0' for c in kid):
                    continue
                
                key_val = key_obj.key.hex().replace('-', '').strip()
                formatted_key = f"{kid}:{key_val}"
                if formatted_key not in all_content_keys:
                    all_content_keys.append(formatted_key)

            # Break if 'all' type requested or single PSSH with keys extracted
            if (type_info.lower() == 'all' and len(all_content_keys) >= 1) or (len(pssh_list) == 1 and len(all_content_keys) >= 1):
                break

        # Return keys
        for i, k in enumerate(all_content_keys):
            console.print(f"    [yellow]{i}) [cyan]Extracted kid: [red]{k.split(':')[0]} [cyan]| key: [green]{k.split(':')[1]}")
        
        return all_content_keys if all_content_keys else None
    
    finally:
        cdm.close(session_id)