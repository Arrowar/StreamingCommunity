# 25.07.25

import base64
import logging


# External libraries
import httpx
from rich.console import Console
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH


# Variable
console = Console()


def get_widevine_keys(pssh, license_url, cdm_device_path, headers=None, payload=None):
    """
    Extract Widevine CONTENT keys (KID/KEY) from a license using pywidevine.

    Args:
        pssh (str): PSSH base64.
        license_url (str): Widevine license URL.
        cdm_device_path (str): Path to CDM file (device.wvd).
        headers (dict): Optional HTTP headers.

    Returns:
        list: List of dicts {'kid': ..., 'key': ...} (only CONTENT keys) or None if error.
    """

    # Check if PSSH is a valid base64 string
    try:
        base64.b64decode(pssh)
    except Exception:
        console.print("[bold red] Invalid PSSH base64 string.[/bold red]")
        return None

    try:
        device = Device.load(cdm_device_path)
        cdm = Cdm.from_device(device)
        session_id = cdm.open()

        # Display security level in a more readable format
        security_levels = {1: "L1 (Hardware)", 2: "L2 (Software)", 3: "L3 (Software)"}
        security_level_str = security_levels.get(device.security_level, 'Unknown')
        logging.info(f"Security Level: {security_level_str}")

        # Only allow L3, otherwise warn and exit
        if device.security_level != 3:
            console.print(f"[bold yellow]⚠️ Only L3 (Software) security level is supported. Current: {security_level_str}[/bold yellow]")
            return None

        try:
            challenge = cdm.get_license_challenge(session_id, PSSH(pssh))
            req_headers = headers or {}
            req_headers['Content-Type'] = 'application/octet-stream'

            # Send license request
            response = httpx.post(license_url, data=challenge, headers=req_headers, content=payload)

            if response.status_code != 200:
                console.print(f"[bold red]License error:[/bold red] {response.status_code}, {response.text}")
                return None

            # Handle (JSON) or classic (binary) license response
            license_data = response.content
            content_type = response.headers.get("Content-Type", "")
            logging.info(f"License data: {license_data}, Content-Type: {content_type}")

            # Check if license_data is empty
            if not license_data:
                console.print("[bold red]License response is empty.[/bold red]")
                return None

            if "application/json" in content_type:
                try:
                    
                    # Try to decode as JSON only if plausible
                    data = None
                    try:
                        data = response.json()
                    except Exception:
                        data = None

                    if data and "license" in data:
                        license_data = base64.b64decode(data["license"])
                        
                    elif data is not None:
                        console.print("[bold red]'license' field not found in JSON response.[/bold red]")
                        return None
                    
                except Exception as e:
                    console.print(f"[bold red]Error parsing JSON license:[/bold red] {e}")

            cdm.parse_license(session_id, license_data)

            # Extract only CONTENT keys from the license
            content_keys = []
            for key in cdm.get_keys(session_id):
                if key.type == "CONTENT":
                    kid = key.kid.hex() if isinstance(key.kid, bytes) else str(key.kid)
                    key_val = key.key.hex() if isinstance(key.key, bytes) else str(key.key)

                    content_keys.append({
                        'kid': kid.replace('-', '').strip(),
                        'key': key_val.replace('-', '').strip()
                    })
                    logging.info(f"Use kid: {kid}, key: {key_val}")

            # Check if content_keys list is empty
            if not content_keys:
                console.print("[bold yellow]⚠️ No CONTENT keys found in license.[/bold yellow]")
                return None

            return content_keys
        
        finally:
            cdm.close(session_id)

    except Exception as e:
        console.print(f"[bold red]CDM error:[/bold red] {e}")
        return None