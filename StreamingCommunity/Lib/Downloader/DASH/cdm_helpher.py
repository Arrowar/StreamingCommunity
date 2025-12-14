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


def get_widevine_keys(pssh, license_url, cdm_device_path, headers=None, query_params=None):
    """
    Extract Widevine CONTENT keys (KID/KEY) from a license using pywidevine.

    Args:
        pssh (str): PSSH base64.
        license_url (str): Widevine license URL.
        cdm_device_path (str): Path to CDM file (device.wvd).
        headers (dict): Optional HTTP headers for the license request (from fetch).
        query_params (dict): Optional query parameters to append to the URL.

    Returns:
        list: List of dicts {'kid': ..., 'key': ...} (only CONTENT keys) or None if error.
    """
    if not cdm_device_path:
        console.print("[bold red]Invalid CDM device path.[/bold red]")
        return None

    try:
        device = Device.load(cdm_device_path)
        cdm = Cdm.from_device(device)
        session_id = cdm.open()

        try:
            challenge = cdm.get_license_challenge(session_id, PSSH(pssh))
            
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

            # Send license request
            try:
                # response = httpx.post(license_url, data=challenge, headers=req_headers, content=payload)
                response = requests.post(request_url, headers=req_headers, impersonate="chrome124", **request_kwargs)

            except Exception as e:
                console.print(f"[bold red]Request error:[/bold red] {e}")
                return None

            if response.status_code != 200:
                console.print(f"[bold red]License error:[/bold red] {response.status_code}, {response.text}")
                console.print({
                    "url": license_url,
                    "headers": req_headers,
                    "session_id": session_id.hex(),
                    "pssh": pssh
                })
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
                        console.print(f"[bold red]'license' field not found in JSON response: {data}.[/bold red]")
                        return None
                except Exception as e:
                    console.print(f"[bold red]Error parsing JSON license:[/bold red] {e}")
                    return None

            if not license_bytes:
                console.print("[bold red]License data is empty.[/bold red]")
                return None

            # Parse license
            try:
                cdm.parse_license(session_id, license_bytes)
            except Exception as e:
                console.print(f"[bold red]Error parsing license:[/bold red] {e}")
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
                console.print("[bold yellow]⚠️ No CONTENT keys found in license.[/bold yellow]")
                return None

            return content_keys
        
        finally:
            cdm.close(session_id)

    except Exception as e:
        console.print(f"[bold red]CDM error:[/bold red] {e}")
        return None