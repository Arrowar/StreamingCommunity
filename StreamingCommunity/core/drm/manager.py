# 29.01.26

import time
from urllib.parse import urlparse

# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.utils.vault import obj_localDbValut, obj_externalSupaDbVault
from StreamingCommunity.source.utils.object import KeysManager


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
    
    def _clean_license_url(self, license_url: str) -> str:
        """Extract base URL from license URL (remove query parameters and fragments)"""
        if not license_url:
            return ""
        parsed = urlparse(license_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return base_url.rstrip('/')

    def get_wv_keys(self, pssh_list: list[dict], license_url: str, headers: dict = None, key: str = None):
        """
        Get Widevine keys with step: 
            1) Database lookup by license URL and KIDs
            2) CDM extraction
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
                return KeysManager(manual_keys)
        
        # Base URL for DB lookup and storage
        base_license_url = self._clean_license_url(license_url)
        
        # Extract all KIDs for lookup
        all_kids = []
        for item in pssh_list:
            kid = item.get('kid')
            if kid and kid != 'N/A':
                all_kids.append(kid.replace('-', '').strip().lower())
        
        # Step 1: Check databases — single bulk request per DB (license URL + all KIDs)
        if (self.is_local_db_connected or self.is_supa_db_connected) and base_license_url and all_kids:
            found_keys = []

            # 1.1 Local DB — one query for all KIDs
            if self.is_local_db_connected:
                lk = obj_localDbValut.get_keys_by_kids(base_license_url, all_kids, 'widevine')
                if lk:
                    found_keys.extend(lk)
                else:
                    # Fallback: global KID-only search
                    lk_f = obj_localDbValut.get_keys_by_kids(None, all_kids, 'widevine')
                    if lk_f:
                        found_keys.extend(lk_f)

            # 1.2 Supabase DB — one request for all KIDs
            if self.is_supa_db_connected:
                sk = obj_externalSupaDbVault.get_keys_by_kids(base_license_url, all_kids, 'widevine')
                if sk:
                    found_keys.extend(sk)
                else:
                    # Fallback: global KID-only search (no license filter)
                    sk_f = obj_externalSupaDbVault.get_keys_by_kids(None, all_kids, 'widevine')
                    if sk_f:
                        found_keys.extend(sk_f)

            if found_keys:
                unique_keys = list(set(found_keys))
                needed_unique_kids = set(all_kids)
                found_unique_kids = {k.split(':')[0].replace('-', '').strip().lower() for k in unique_keys}

                if needed_unique_kids.issubset(found_unique_kids):
                    return KeysManager(unique_keys)
        
        # Step 3: Try CDM extraction
        try:
            console.print(f"[dim]Waiting {DELAY} seconds after CDM request ...")
            time.sleep(DELAY)
            keys = get_widevine_keys(pssh_list, license_url, self.widevine_device_path, self.widevine_remote_cdm_api, headers, key)
                
            if keys:
                keys_list = keys.get_keys_list()
                pssh_val = next((item.get('pssh') for item in pssh_list if item.get('pssh')), None)

                if self.is_local_db_connected and base_license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to local database...")
                    obj_localDbValut.set_keys(keys_list, 'widevine', base_license_url, pssh_val)

                if self.is_supa_db_connected and base_license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to Supabase database...")
                    obj_externalSupaDbVault.set_keys(keys_list, 'widevine', base_license_url, pssh_val)

                return keys
            
            else:
                console.print("[yellow]CDM extraction returned no keys")
        
        except Exception as e:
            console.print(f"[red]CDM error: {e}")

        console.print("\n[red]All extraction methods failed for Widevine")
        return None
    
    def get_pr_keys(self, pssh_list: list[dict], license_url: str, headers: dict = None, key: str = None):
        """
        Get PlayReady keys with step: 
            1) Database lookup by license URL and KIDs
            2) CDM extraction
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
                return KeysManager(manual_keys)
        
        # Base URL for DB lookup and storage
        base_license_url = self._clean_license_url(license_url)
        
        # Extract all KIDs for lookup
        all_kids = []
        for item in pssh_list:
            kid = item.get('kid')
            if kid and kid != 'N/A':
                all_kids.append(kid.replace('-', '').strip().lower())
        
        # Step 1: Check databases — single bulk request per DB (license URL + all KIDs)
        if (self.is_local_db_connected or self.is_supa_db_connected) and base_license_url and all_kids:
            found_keys = []

            # 1.1 Local DB — one query for all KIDs
            if self.is_local_db_connected:
                lk = obj_localDbValut.get_keys_by_kids(base_license_url, all_kids, 'playready')
                if lk:
                    found_keys.extend(lk)
                else:
                    lk_f = obj_localDbValut.get_keys_by_kids(None, all_kids, 'playready')
                    if lk_f:
                        found_keys.extend(lk_f)

            # 1.2 Supabase DB — one request for all KIDs
            if self.is_supa_db_connected:
                sk = obj_externalSupaDbVault.get_keys_by_kids(base_license_url, all_kids, 'playready')
                if sk:
                    found_keys.extend(sk)
                else:
                    sk_f = obj_externalSupaDbVault.get_keys_by_kids(None, all_kids, 'playready')
                    if sk_f:
                        found_keys.extend(sk_f)

            if found_keys:
                unique_keys = list(set(found_keys))
                needed_unique_kids = set(all_kids)
                found_unique_kids = {k.split(':')[0].replace('-', '').strip().lower() for k in unique_keys}

                if needed_unique_kids.issubset(found_unique_kids):
                    return KeysManager(unique_keys)
        
        # Step 3: Try CDM extraction
        try:
            console.print(f"[dim]Waiting {DELAY} seconds after CDM request ...")
            time.sleep(DELAY)
            keys = get_playready_keys(pssh_list, license_url, self.playready_device_path, self.playready_remote_cdm_api, headers, key)
            
            if keys:
                keys_list = keys.get_keys_list()
                pssh_val = next((item.get('pssh') for item in pssh_list if item.get('pssh')), None)

                if self.is_local_db_connected and base_license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to local database...")
                    obj_localDbValut.set_keys(keys_list, 'playready', base_license_url, pssh_val)

                if self.is_supa_db_connected and base_license_url and pssh_val:
                    console.print(f"Storing {len(keys)} key(s) to Supabase database...")
                    obj_externalSupaDbVault.set_keys(keys_list, 'playready', base_license_url, pssh_val)

                return keys
            else:
                console.print("[yellow]CDM extraction returned no keys")
        
        except Exception as e:
            console.print(f"[red]CDM error: {e}")
        
        console.print("\n[red]All extraction methods failed for PlayReady")
        return None