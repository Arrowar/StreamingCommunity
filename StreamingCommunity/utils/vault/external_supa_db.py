# 29.01.26

from typing import List, Optional


# External import
from rich.console import Console
from StreamingCommunity.utils.http_client import create_client
from StreamingCommunity.utils.config import config_manager


# Variable
console = Console()


class ExternalSupaDBVault:
    def __init__(self):
        self.base_url = f"{config_manager.remote_cdm.get('external_supa_db', 'url')}/functions/v1"
        self.headers = {
            "Content-Type": "application/json"
        }
    
    def set_key(self, license_url: str, pssh: str, kid: str, key: str, drm_type: str, label: Optional[str] = None) -> bool:
        """
        Add a key to the vault
        
        Returns:
            bool: True if added successfully, False otherwise
        """
        url = f"{self.base_url}/set-key"
        
        payload = {
            "license_url": license_url,
            "pssh": pssh,
            "kid": kid,
            "key": key,
            "drm_type": drm_type,
            "label": label
        }
        
        try:
            response = create_client(headers=self.headers).post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                return True
            else:
                console.print(f"[yellow]⚠ {result.get('message', 'Key already exists')}")
                return False
                
        except Exception as e:
            console.print(f"[red]Error adding key: {e}")
            return False

    def set_keys(self, keys_list: List[str], drm_type: str, license_url: str, pssh: str) -> int:
        """
        Add multiple keys to the vault in batch
        
        Args:
            keys_list: List of "kid:key" strings
            
        Returns:
            int: Number of keys successfully added
        """
        if not keys_list:
            return 0
        
        added_count = 0
        
        for key_str in keys_list:
            if ':' not in key_str:
                continue
            
            kid, key = key_str.split(':', 1)
            label = None
            
            if self.set_key(license_url, pssh, kid, key, drm_type, label):
                added_count += 1
        
        return added_count
    
    def get_keys_by_pssh(self, license_url: str, pssh: str, drm_type: str) -> List[str]:
        """
        Retrieve all keys for a given license URL and PSSH
        
        Returns:
            List[str]: List of "kid:key" strings
        """
        url = f"{self.base_url}/get-keys"
        
        payload = {
            "license_url": license_url,
            "pssh": pssh,
            "drm_type": drm_type
        }
        
        try:
            response = create_client(headers=self.headers).post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            keys = result.get('keys', [])
            
            if keys:
                # Print header (reference from widevine.py)
                console.print("[cyan]Using Supabase Vault.")
                console.print(f"[red]{drm_type} [cyan](PSSH: [yellow]{pssh[:30]}...[cyan] KID: [red]N/A)")
                
                for key_data in keys:
                    kid, key_val = key_data['kid_key'].split(':')
                    masked_key = key_val[:-1] + "*"
                    label_str = f" [cyan]| [red]{key_data['label']}" if key_data.get('label') else ""
                    console.print(f"    - [red]{kid}[white]:[green]{masked_key}{label_str}")
            
            return [k['kid_key'] for k in keys]
            
        except Exception as e:
            console.print(f"[red]Error fetching keys: {e}")
            return []


# Initialize
is_supa_external_db_valid = not (config_manager.remote_cdm.get('external_supa_db', 'url') is None or config_manager.remote_cdm.get('external_supa_db', 'url') == "")
obj_externalSupaDbVault = ExternalSupaDBVault() if is_supa_external_db_valid else None