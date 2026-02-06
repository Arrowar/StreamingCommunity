# 29.01.26

import time

# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.utils.vault import obj_localDbValut, obj_externalSupaDbVault


# Logic
from .playready import get_playready_keys
from .widevine import get_widevine_keys


# Variable
console = Console()
DELAY = config_manager.remote_cdm.get_int('config', 'delay_after_request')


class DRMManager:
    def __init__(self, widevine_device_path: str = None, playready_device_path: str = None, widevine_remote_cdm_api: list[str] = None, playready_remote_cdm_api: list[str] = None):
        """
        Initialize DRM Manager with configuration file paths and database.
        """
        # CDM paths
        self.widevine_device_path = widevine_device_path
        self.playready_device_path = playready_device_path
        self.widevine_remote_cdm_api = widevine_remote_cdm_api
        self.playready_remote_cdm_api = playready_remote_cdm_api
        
        # Check database connections
        self.is_local_db_connected = obj_localDbValut is not None
        self.is_supa_db_connected = obj_externalSupaDbVault is not None
    
    def get_wv_keys(self, pssh_list: list[dict], license_url: str, headers: dict = None, key: str = None, kid_to_label: dict = None) -> list[str]:
        """
        Get Widevine keys with step: 
            1) Database lookup by license URL and PSSH
            2) Fallback search by KIDs only
            3) CDM extraction
                1) If .wvd file provided, use it
                2) Else, use remote CDM API if provided
        """
        # Step 0: Handle pre-existing key
        if key:
            manual_keys = []
            for keys in key.split('|'):
                k_split = keys.split(':')
                if len(k_split) == 2:
                    kid = k_split[0].replace('-', '').strip()
                    key_val = k_split[1].replace('-', '').strip()
                    masked_key = key_val[:-1] + "*"
                    
                    if not manual_keys:
                        console.print("[cyan]Using Manual Key.")
                    console.print(f"    - [red]{kid}[white]:[green]{masked_key} [cyan]| [red]Manual")
                    manual_keys.append(f"{kid}:{key_val}")
            if manual_keys:
                return manual_keys
            
        # Extract PSSH from first entry for database lookup
        pssh_val = pssh_list[0].get('pssh') if pssh_list else None
        
        if not pssh_val:
            console.print("[yellow]Warning: No PSSH provided for database lookup")
        
        # Step 1: Check local database by license URL and PSSH
        if self.is_local_db_connected and license_url and pssh_val:
            found_keys = obj_localDbValut.get_keys_by_pssh(license_url, pssh_val, 'widevine')
            
            if found_keys:
                return found_keys
            
        # Setp 1.1: Check external Supabase database if connected
        if self.is_supa_db_connected and license_url and pssh_val:
            found_keys = obj_externalSupaDbVault.get_keys_by_pssh(license_url, pssh_val, 'widevine')
            
            if found_keys:
                return found_keys
        
        # Step 3: Try CDM extraction
        try:
            keys = get_widevine_keys(pssh_list, license_url, self.widevine_device_path, self.widevine_remote_cdm_api, headers, key, kid_to_label)
            time.sleep(DELAY)
                
            if keys:
                if self.is_local_db_connected and license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to local database...")
                    obj_localDbValut.set_keys(keys, 'widevine', license_url, pssh_val, kid_to_label)

                if self.is_supa_db_connected and license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to Supabase database...")
                    obj_externalSupaDbVault.set_keys(keys, 'widevine', license_url, pssh_val, kid_to_label)

                return keys
            
            else:
                console.print("[yellow]CDM extraction returned no keys")
        
        except Exception as e:
            console.print(f"[red]CDM error: {e}")

        console.print("\n[red]All extraction methods failed for Widevine")
        return None
    
    def get_pr_keys(self, pssh_list: list[dict], license_url: str, headers: dict = None, key: str = None, kid_to_label: dict = None) -> list[str]:
        """
        Get PlayReady keys with step: 
            1) Database lookup by license URL and PSSH
            2) Fallback search by KIDs only
            3) CDM extraction
                1) If .prd file provided, use it
                2) Else, use remote CDM API if provided
        """
        # Handle pre-existing key
        if key:
            manual_keys = []
            for keys in key.split('|'):
                k_split = keys.split(':')
                if len(k_split) == 2:
                    kid = k_split[0].replace('-', '').strip()
                    key_val = k_split[1].replace('-', '').strip()
                    masked_key = key_val[:-1] + "*"
                    
                    if not manual_keys:
                        console.print("[cyan]Using Manual Key.")
                    console.print(f"    - [red]{kid}[white]:[green]{masked_key} [cyan]| [red]Manual")
                    manual_keys.append(f"{kid}:{key_val}")
            if manual_keys:
                return manual_keys
        
        # Extract PSSH from first entry for database lookup
        pssh_val = pssh_list[0].get('pssh') if pssh_list else None
        
        if not pssh_val:
            console.print("[yellow]Warning: No PSSH provided for database lookup")
        
        # Step 1: Check database by license URL and PSSH
        if self.is_local_db_connected and license_url and pssh_val:
            found_keys = obj_localDbValut.get_keys_by_pssh(license_url, pssh_val, 'playready')
            
            if found_keys:
                return found_keys
            
        # Setp 1.1: Check external Supabase database if connected
        if self.is_supa_db_connected and license_url and pssh_val:
            found_keys = obj_externalSupaDbVault.get_keys_by_pssh(license_url, pssh_val, 'playready')
            
            if found_keys:
                return found_keys
        
        # Step 3: Try CDM extraction
        try:
            keys = get_playready_keys(pssh_list, license_url, self.playready_device_path, self.playready_remote_cdm_api, headers, key, kid_to_label)
            time.sleep(DELAY)
            
            if keys:
                if self.is_local_db_connected and license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to local database...")
                    obj_localDbValut.set_keys(keys, 'playready', license_url, pssh_val, kid_to_label)

                if self.is_supa_db_connected and license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to Supabase database...")
                    obj_externalSupaDbVault.set_keys(keys, 'playready', license_url, pssh_val, kid_to_label)

                return keys
            else:
                console.print("[yellow]CDM extraction returned no keys")
        
        except Exception as e:
            console.print(f"[red]CDM error: {e}")
        
        console.print("\n[red]All extraction methods failed for PlayReady")
        return None