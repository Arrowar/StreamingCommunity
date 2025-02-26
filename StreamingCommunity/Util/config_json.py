# 29.01.24

import os
import sys
import json
import logging
import requests
from typing import Any, List


# External library
from rich.console import Console


# Variable
console = Console()


class ConfigManager:
    def __init__(self, file_name: str = 'config.json') -> None:
        """Initialize the ConfigManager.

        Parameters:
            - file_name (str, optional): The name of the configuration file. Default is 'config.json'.
        """
        if getattr(sys, 'frozen', False):
            base_path = os.path.join(".")
        else:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            
        self.file_path = os.path.join(base_path, file_name)
        self.domains_path = os.path.join(base_path, 'domains.json')
        self.config = {}
        self.configSite = {}
        self.cache = {}
        self.reference_config_url = 'https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/config.json'
        
        # Validate and update config before proceeding
        self._validate_and_update_config()
        self._read_initial_config()
        
        console.print(f"[bold cyan]ConfigManager initialized:[/bold cyan] [green]{self.file_path}[/green]")

    def _validate_and_update_config(self) -> None:
        """Validate local config against reference config and update missing keys."""
        try:

            # Load local config if exists
            local_config = {}
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    local_config = json.load(f)
                console.print(f"[bold cyan]Local configuration loaded:[/bold cyan] [green]{len(local_config)} keys found[/green]")

            # Download reference config
            console.print(f"[bold cyan]Downloading reference config from:[/bold cyan] [green]{self.reference_config_url}[/green]")
            response = requests.get(self.reference_config_url, timeout=10)

            if response.ok:
                raise Exception(f"Failed to download reference config. Status code: {response.status_code}")
            
            reference_config = response.json()
            console.print(f"[bold cyan]Reference config downloaded:[/bold cyan] [green]{len(reference_config)} keys available[/green]")

            # Compare and update missing keys
            merged_config = self._deep_merge_configs(local_config, reference_config)
            
            if merged_config != local_config:
                added_keys = self._get_added_keys(local_config, merged_config)

                # Save the merged config
                with open(self.file_path, 'w') as f:
                    json.dump(merged_config, f, indent=4)
                console.print(f"[bold green]Configuration updated with {len(added_keys)} new keys:[/bold green] {', '.join(added_keys[:5])}{' and more...' if len(added_keys) > 5 else ''}")

            else:
                console.print("[bold green]Configuration is up to date.[/bold green]")

            self.config = merged_config

        except Exception as e:
            console.print(f"[bold red]Configuration validation error:[/bold red] {str(e)}")

            if not self.config:
                console.print("[bold yellow]Falling back to reference configuration...[/bold yellow]")
                self.download_requirements(self.reference_config_url, self.file_path)

                with open(self.file_path, 'r') as f:
                    self.config = json.load(f)

                console.print(f"[bold green]Reference config loaded successfully with {len(self.config)} keys[/bold green]")

    def _get_added_keys(self, old_config: dict, new_config: dict, prefix="") -> list:
        """
        Get list of keys added in the new config compared to old config.
        
        Args:
            old_config (dict): The original configuration
            new_config (dict): The new configuration
            prefix (str): Key prefix for nested keys
            
        Returns:
            list: List of added key names
        """
        added_keys = []
        
        for key, value in new_config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if key not in old_config:
                added_keys.append(full_key)
            elif isinstance(value, dict) and isinstance(old_config.get(key), dict):
                added_keys.extend(self._get_added_keys(old_config[key], value, full_key))
                
        return added_keys

    def _deep_merge_configs(self, local_config: dict, reference_config: dict) -> dict:
        """
        Recursively merge reference config into local config, preserving local values.
        
        Args:
            local_config (dict): The local configuration
            reference_config (dict): The reference configuration
            
        Returns:
            dict: Merged configuration
        """
        merged = local_config.copy()
        
        for key, value in reference_config.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._deep_merge_configs(merged[key], value)
                
        return merged

    def _read_initial_config(self) -> None:
        """Read initial configuration to get use_api setting."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.config = json.load(f)

                self.use_api = self.config.get('DEFAULT', {}).get('use_api', True)
                console.print(f"[bold cyan]API usage setting:[/bold cyan] [{'green' if self.use_api else 'yellow'}]{self.use_api}[/{'green' if self.use_api else 'yellow'}]")

            else:
                self.use_api = True
                console.print("[bold yellow]Configuration file not found. Using default API setting: True[/bold yellow]")

        except Exception as e:
            self.use_api = True
            console.print("[bold red]Error reading API setting. Using default: True[/bold red]")

    def read_config(self) -> None:
        """Read the configuration file."""
        try:
            logging.info(f"Reading file: {self.file_path}")

            # Check if file exists
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.config = json.load(f)
                console.print(f"[bold green]Configuration loaded:[/bold green] {len(self.config)} keys, {sum(1 for _ in json.dumps(self.config))} bytes")

            else:
                console.print(f"[bold yellow]Configuration file not found at:[/bold yellow] {self.file_path}")
                console.print(f"[bold cyan]Downloading from:[/bold cyan] {self.reference_config_url}")
                self.download_requirements(self.reference_config_url, self.file_path)

                # Load the downloaded config.json into the config attribute
                with open(self.file_path, 'r') as f:
                    self.config = json.load(f)
                console.print(f"[bold green]Configuration downloaded and saved:[/bold green] {len(self.config)} keys")

            # Update site configuration separately
            self.update_site_config()

            console.print("[bold cyan]Configuration processing complete[/bold cyan]")

        except Exception as e:
            logging.error(f"Error reading configuration file: {e}")
            console.print(f"[bold red]Failed to read configuration:[/bold red] {str(e)}")

    def download_requirements(self, url: str, filename: str) -> None:
        """
        Download a file from the specified URL if not found locally using requests.

        Args:
            url (str): The URL to download the file from.
            filename (str): The local filename to save the file as.
        """
        try:
            logging.info(f"Downloading {filename} from {url}...")
            console.print(f"[bold cyan]Downloading file:[/bold cyan] {os.path.basename(filename)}")
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                file_size = len(response.content) / 1024
                console.print(f"[bold green]Download successful:[/bold green] {os.path.basename(filename)} ({file_size:.2f} KB)")
                
            else:
                error_msg = f"HTTP Status: {response.status_code}, Response: {response.text[:100]}"
                console.print(f"[bold red]Download failed:[/bold red] {error_msg}")
                logging.error(f"Failed to download {filename}. {error_msg}")
                sys.exit(0)

        except Exception as e:
            console.print(f"[bold red]Download error:[/bold red] {str(e)}")
            logging.error(f"Failed to download {filename}: {e}")
            sys.exit(0)

    def update_site_config(self) -> None:
        """Fetch and update the site configuration with data from the API or local file."""
        if self.use_api:
            headers = {
                "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp2Zm5ncG94d3Jnc3duenl0YWRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAxNTIxNjMsImV4cCI6MjA1NTcyODE2M30.FNTCCMwi0QaKjOu8gtZsT5yQttUW8QiDDGXmzkn89QE",
                "Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp2Zm5ncG94d3Jnc3duenl0YWRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAxNTIxNjMsImV4cCI6MjA1NTcyODE2M30.FNTCCMwi0QaKjOu8gtZsT5yQttUW8QiDDGXmzkn89QE",
                "Content-Type": "application/json"
            }

            try:
                console.print("[bold cyan]Fetching site data from API...[/bold cyan]")
                response = requests.get("https://zvfngpoxwrgswnzytadh.supabase.co/rest/v1/public", headers=headers, timeout=10)

                if response.ok:
                    data = response.json()
                    if data and len(data) > 0:
                        self.configSite = data[0]['data']
                        
                        # Display available sites and their domains
                        site_count = len(self.configSite) if isinstance(self.configSite, dict) else 0
                        console.print(f"[bold green]Site data fetched:[/bold green] {site_count} streaming services available")
                        
                        # List a few sites as examples
                        if site_count > 0:
                            examples = list(self.configSite.items())[:3]
                            sites_info = []
                            for site, info in examples:
                                sites_info.append(f"[cyan]{site}[/cyan]: {info.get('full_url', 'N/A')}")
                            
                            console.print("[bold cyan]Sample sites:[/bold cyan]")
                            for info in sites_info:
                                console.print(f"  {info}")
                            
                            if site_count > 3:
                                console.print(f"  ... and {site_count - 3} more")
                                
                    else:
                        console.print("[bold yellow]API returned empty data set[/bold yellow]")
                else:
                    console.print(f"[bold red]API request failed:[/bold red] HTTP {response.status_code}, {response.text[:100]}")

            except Exception as e:
                console.print(f"[bold red]API connection error:[/bold red] {str(e)}")
        else:
            try:
                if os.path.exists(self.domains_path):
                    console.print(f"[bold cyan]Reading domains from:[/bold cyan] {self.domains_path}")
                    with open(self.domains_path, 'r') as f:
                        self.configSite = json.load(f)
                    
                else:
                    error_msg = f"domains.json not found at {self.domains_path} and API usage is disabled"
                    console.print(f"[bold red]Configuration error:[/bold red] {error_msg}")
                    raise FileNotFoundError(error_msg)

            except Exception as e:
                console.print(f"[bold red]Domains file error:[/bold red] {str(e)}")
                raise
            
    def read_key(self, section: str, key: str, data_type: type = str, from_site: bool = False) -> Any:
        """Read a key from the configuration.

        Parameters:
            - section (str): The section in the configuration.
            - key (str): The key to be read.
            - data_type (type, optional): The expected data type of the key's value. Default is str.
            - from_site (bool, optional): Whether to read from site config. Default is False.

        Returns:
            The value of the key converted to the specified data type.
        """
        cache_key = f"{'site' if from_site else 'config'}.{section}.{key}"
        logging.info(f"Read key: {cache_key}")

        if cache_key in self.cache:
            return self.cache[cache_key]

        config_source = self.configSite if from_site else self.config
        
        if section in config_source and key in config_source[section]:
            value = config_source[section][key]
        else:
            raise ValueError(f"Key '{key}' not found in section '{section}' of {'site' if from_site else 'main'} config")

        value = self._convert_to_data_type(value, data_type)
        self.cache[cache_key] = value

        return value

    def _convert_to_data_type(self, value: str, data_type: type) -> Any:
        """Convert the value to the specified data type.

        Parameters:
            - value (str): The value to be converted.
            - data_type (type): The expected data type.

        Returns:
            The value converted to the specified data type.
        """
        if data_type == int:
            return int(value)
        elif data_type == bool:
            return bool(value)
        elif data_type == list:
            return value if isinstance(value, list) else [item.strip() for item in value.split(',')]
        elif data_type == type(None):
            return None
        else:
            return value

    # Main config getters
    def get(self, section: str, key: str) -> Any:
        """Read a value from the main configuration."""
        return self.read_key(section, key)

    def get_int(self, section: str, key: str) -> int:
        """Read an integer value from the main configuration."""
        return self.read_key(section, key, int)

    def get_float(self, section: str, key: str) -> float:
        """Read a float value from the main configuration."""
        return self.read_key(section, key, float)

    def get_bool(self, section: str, key: str) -> bool:
        """Read a boolean value from the main configuration."""
        return self.read_key(section, key, bool)

    def get_list(self, section: str, key: str) -> List[str]:
        """Read a list value from the main configuration."""
        return self.read_key(section, key, list)

    def get_dict(self, section: str, key: str) -> dict:
        """Read a dictionary value from the main configuration."""
        return self.read_key(section, key, dict)

    # Site config getters
    def get_site(self, section: str, key: str) -> Any:
        """Read a value from the site configuration."""
        return self.read_key(section, key, from_site=True)

    def get_site_int(self, section: str, key: str) -> int:
        """Read an integer value from the site configuration."""
        return self.read_key(section, key, int, from_site=True)

    def get_site_float(self, section: str, key: str) -> float:
        """Read a float value from the site configuration."""
        return self.read_key(section, key, float, from_site=True)

    def get_site_bool(self, section: str, key: str) -> bool:
        """Read a boolean value from the site configuration."""
        return self.read_key(section, key, bool, from_site=True)

    def get_site_list(self, section: str, key: str) -> List[str]:
        """Read a list value from the site configuration."""
        return self.read_key(section, key, list, from_site=True)

    def get_site_dict(self, section: str, key: str) -> dict:
        """Read a dictionary value from the site configuration."""
        return self.read_key(section, key, dict, from_site=True)

    def set_key(self, section: str, key: str, value: Any, to_site: bool = False) -> None:
        """Set a key in the configuration.

        Parameters:
            - section (str): The section in the configuration.
            - key (str): The key to be set.
            - value (Any): The value to be associated with the key.
            - to_site (bool, optional): Whether to set in site config. Default is False.
        """
        try:
            config_target = self.configSite if to_site else self.config
            
            if section not in config_target:
                config_target[section] = {}

            config_target[section][key] = value
            cache_key = f"{'site' if to_site else 'config'}.{section}.{key}"
            self.cache[cache_key] = value

        except Exception as e:
            print(f"Error setting key '{key}' in section '{section}' of {'site' if to_site else 'main'} config: {e}")

    def write_config(self) -> None:
        """Write the main configuration to the file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error writing configuration file: {e}")


config_manager = ConfigManager()
config_manager.read_config()