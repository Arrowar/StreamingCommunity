# 29.01.24

import os
import sys
import json
import logging
import requests
from typing import Any, List


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.headers import get_userAgent


# Variable
console = Console()
download_site_data = True
validate_github_config = True


class ConfigManager:
    def __init__(self, file_name: str = 'config.json') -> None:
        """
        Initialize the ConfigManager.
        
        Args:
            file_name (str, optional): Configuration file name. Default: 'config.json'.
        """
        # Determine the base path - use the current working directory
        if getattr(sys, 'frozen', False):
            # If the application is frozen (e.g., PyInstaller)
            base_path = os.path.dirname(sys.executable)

        else:
          
            # Get the actual path of the module file
            current_file_path = os.path.abspath(__file__)
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
            
        # Initialize file paths
        self.file_path = os.path.join(base_path, file_name)
        self.domains_path = os.path.join(base_path, 'domains.json')
        
        # Display the actual file path for debugging
        console.print(f"[bold cyan]Configuration file path:[/bold cyan] [green]{self.file_path}[/green]")
        
        # Reference repository URL
        self.reference_config_url = 'https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/config.json'
        
        # Initialize data structures
        self.config = {}
        self.configSite = {}
        self.cache = {}

        self.use_api = False
        self.download_site_data = False
        self.validate_github_config = False
        
        console.print(f"[bold cyan]Initializing ConfigManager:[/bold cyan] [green]{self.file_path}[/green]")
        
        # Load the configuration
        self.load_config()
        
    def load_config(self) -> None:
        """Load the configuration and initialize all settings."""
        if not os.path.exists(self.file_path):
            console.print(f"[bold red]WARNING: Configuration file not found:[/bold red] {self.file_path}")
            console.print(f"[bold yellow]Attempting to download from reference repository...[/bold yellow]")
            self._download_reference_config()
        
        # Load the configuration file
        try:
            with open(self.file_path, 'r') as f:
                self.config = json.load(f)
            console.print(f"[bold green]Configuration loaded:[/bold green] {len(self.config)} keys")
            
            # Update settings from the configuration
            self._update_settings_from_config()
            
            # Validate and update the configuration if requested
            if self.validate_github_config:
                self._validate_and_update_config()
            else:
                console.print("[bold yellow]GitHub validation disabled[/bold yellow]")
                
            # Load site data if requested
            if self.download_site_data:
                self._load_site_data()
            else:
                console.print("[bold yellow]Site data download disabled[/bold yellow]")
                
        except json.JSONDecodeError as e:
            console.print(f"[bold red]Error parsing JSON:[/bold red] {str(e)}")
            self._handle_config_error()

        except Exception as e:
            console.print(f"[bold red]Error loading configuration:[/bold red] {str(e)}")
            self._handle_config_error()
    
    def _handle_config_error(self) -> None:
        """Handle configuration errors by downloading the reference version."""
        console.print("[bold yellow]Attempting to retrieve reference configuration...[/bold yellow]")
        self._download_reference_config()
        
        # Reload the configuration
        try:
            with open(self.file_path, 'r') as f:
                self.config = json.load(f)
            self._update_settings_from_config()
            console.print("[bold green]Reference configuration loaded successfully[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Critical configuration error:[/bold red] {str(e)}")
            console.print("[bold red]Unable to proceed. The application will terminate.[/bold red]")
            sys.exit(1)
    
    def _update_settings_from_config(self) -> None:
        """Update internal settings from loaded configurations."""
        default_section = self.config.get('DEFAULT', {})
        
        # Save local values in temporary variables
        temp_use_api = default_section.get('use_api', False)
        temp_download_site_data = default_section.get('download_site_data', False)
        temp_validate_github_config = default_section.get('validate_github_config', False)
        
        # Update settings with found values (False by default)
        self.use_api = temp_use_api
        self.download_site_data = temp_download_site_data
        self.validate_github_config = temp_validate_github_config
        
        console.print(f"[bold cyan]API Usage:[/bold cyan] [{'green' if self.use_api else 'yellow'}]{self.use_api}[/{'green' if self.use_api else 'yellow'}]")
        console.print(f"[bold cyan]Site data download:[/bold cyan] [{'green' if self.download_site_data else 'yellow'}]{self.download_site_data}[/{'green' if self.download_site_data else 'yellow'}]")
        console.print(f"[bold cyan]GitHub configuration validation:[/bold cyan] [{'green' if self.validate_github_config else 'yellow'}]{self.validate_github_config}[/{'green' if self.validate_github_config else 'yellow'}]")
    
    def _download_reference_config(self) -> None:
        """Download the reference configuration from GitHub."""
        console.print(f"[bold cyan]Downloading reference configuration:[/bold cyan] [green]{self.reference_config_url}[/green]")

        try:
            response = requests.get(self.reference_config_url, timeout=8, headers={'User-Agent': get_userAgent()})
            
            if response.status_code == 200:
                with open(self.file_path, 'wb') as f:
                    f.write(response.content)
                file_size = len(response.content) / 1024
                console.print(f"[bold green]Download complete:[/bold green] {os.path.basename(self.file_path)} ({file_size:.2f} KB)")
            else:

                error_msg = f"HTTP Error: {response.status_code}, Response: {response.text[:100]}"
                console.print(f"[bold red]Download failed:[/bold red] {error_msg}")
                raise Exception(error_msg)
            
        except Exception as e:
            console.print(f"[bold red]Download error:[/bold red] {str(e)}")
            raise
    
    def _validate_and_update_config(self) -> None:
        """Validate the local configuration against the reference one and update missing keys."""
        try:
            # Download the reference configuration
            console.print(f"[bold cyan]Validating configuration with GitHub...[/bold cyan]")
            response = requests.get(self.reference_config_url, timeout=8, headers={'User-Agent': get_userAgent()})
            
            if not response.ok:
                raise Exception(f"Error downloading reference configuration. Code: {response.status_code}")
            
            reference_config = response.json()
            
            # Compare and update missing keys
            merged_config = self._deep_merge_configs(self.config, reference_config)
            
            if merged_config != self.config:
                added_keys = self._get_added_keys(self.config, merged_config)
                
                # Save the merged configuration
                with open(self.file_path, 'w') as f:
                    json.dump(merged_config, f, indent=4)
                
                key_examples = ', '.join(added_keys[:5])
                if len(added_keys) > 5:
                    key_examples += ' and others...'
                    
                console.print(f"[bold green]Configuration updated with {len(added_keys)} new keys:[/bold green] {key_examples}")
                
                # Update the configuration in memory
                self.config = merged_config
                self._update_settings_from_config()
            else:
                console.print("[bold green]The configuration is up to date.[/bold green]")
                
        except Exception as e:
            console.print(f"[bold red]Error validating configuration:[/bold red] {str(e)}")
    
    def _get_added_keys(self, old_config: dict, new_config: dict, prefix="") -> list:
        """
        Get the list of keys added in the new configuration compared to the old one.
        
        Args:
            old_config (dict): Original configuration
            new_config (dict): New configuration
            prefix (str): Prefix for nested keys
            
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
        Recursively merge the reference configuration into the local one, preserving local values.
        
        Args:
            local_config (dict): Local configuration
            reference_config (dict): Reference configuration
            
        Returns:
            dict: Merged configuration
        """
        merged = local_config.copy()
        
        for key, value in reference_config.items():
            if key not in merged:

                # Create the key if it doesn't exist
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):

                # Handle the DEFAULT section specially
                if key == 'DEFAULT':

                    # Make sure control keys maintain local values
                    merged_section = self._deep_merge_configs(merged[key], value)
                    
                    # Preserve local values for the three critical settings
                    if 'use_api' in merged[key]:
                        merged_section['use_api'] = merged[key]['use_api']
                    if 'download_site_data' in merged[key]:
                        merged_section['download_site_data'] = merged[key]['download_site_data']
                    if 'validate_github_config' in merged[key]:
                        merged_section['validate_github_config'] = merged[key]['validate_github_config']
                    
                    merged[key] = merged_section
                else:

                    # Normal merge for other sections
                    merged[key] = self._deep_merge_configs(merged[key], value)
                
        return merged
    
    def _load_site_data(self) -> None:
        """Load site data from API or local file."""
        if self.use_api:
            self._load_site_data_from_api()
        else:
            self._load_site_data_from_file()
    
    def _load_site_data_from_api(self) -> None:
        """Load site data from GitHub."""
        domains_github_url = "https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/.github/.domain/domains.json"
        headers = {
            "User-Agent": get_userAgent()
        }
        
        try:
            console.print(f"[bold cyan]Retrieving site data from GitHub:[/bold cyan] [green]{domains_github_url}[/green]")
            response = requests.get(domains_github_url, timeout=8, headers=headers)

            if response.ok:
                self.configSite = response.json()
                
                site_count = len(self.configSite) if isinstance(self.configSite, dict) else 0
                console.print(f"[bold green]Site data loaded from GitHub:[/bold green] {site_count} streaming services found.")
                
            else:
                console.print(f"[bold red]GitHub request failed:[/bold red] HTTP {response.status_code}, {response.text[:100]}")
                self._handle_site_data_fallback()
        
        except json.JSONDecodeError as e:
            console.print(f"[bold red]Error parsing JSON from GitHub:[/bold red] {str(e)}")
            self._handle_site_data_fallback()
            
        except Exception as e:
            console.print(f"[bold red]GitHub connection error:[/bold red] {str(e)}")
            self._handle_site_data_fallback()
    
    def _load_site_data_from_file(self) -> None:
        """Load site data from local file."""
        try:
            if os.path.exists(self.domains_path):
                console.print(f"[bold cyan]Reading domains from:[/bold cyan] {self.domains_path}")
                with open(self.domains_path, 'r') as f:
                    self.configSite = json.load(f)
                
                site_count = len(self.configSite) if isinstance(self.configSite, dict) else 0
                console.print(f"[bold green]Site data loaded from file:[/bold green] {site_count} streaming services")

            else:
                error_msg = f"domains.json not found at {self.domains_path} and API usage is disabled"
                console.print(f"[bold red]Configuration error:[/bold red] {error_msg}")
                self._handle_site_data_fallback()
        
        except Exception as e:
            console.print(f"[bold red]Domain file error:[/bold red] {str(e)}")
            self._handle_site_data_fallback()
    
    def _handle_site_data_fallback(self) -> None:
        """Handle site data fallback in case of error."""
        if self.use_api and os.path.exists(self.domains_path):
            console.print("[bold yellow]Attempting fallback to local domains.json file...[/bold yellow]")

            try:
                with open(self.domains_path, 'r') as f:
                    self.configSite = json.load(f)
                console.print("[bold green]Fallback to local data successful[/bold green]")
            except Exception as fallback_error:
                console.print(f"[bold red]Fallback also failed:[/bold red] {str(fallback_error)}")
                self.configSite = {}
        else:

            # Initialize with an empty dictionary if there are no alternatives
            self.configSite = {}
    
    def download_file(self, url: str, filename: str) -> None:
        """
        Download a file from the specified URL.
        
        Args:
            url (str): URL to download from
            filename (str): Local filename to save to
        """
        try:
            logging.info(f"Downloading {filename} from {url}...")
            console.print(f"[bold cyan]File download:[/bold cyan] {os.path.basename(filename)}")
            response = requests.get(url, timeout=8, headers={'User-Agent': get_userAgent()})
            
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                file_size = len(response.content) / 1024
                console.print(f"[bold green]Download complete:[/bold green] {os.path.basename(filename)} ({file_size:.2f} KB)")

            else:
                error_msg = f"HTTP Status: {response.status_code}, Response: {response.text[:100]}"
                console.print(f"[bold red]Download failed:[/bold red] {error_msg}")
                logging.error(f"Download of {filename} failed. {error_msg}")
                raise Exception(error_msg)
        
        except Exception as e:
            console.print(f"[bold red]Download error:[/bold red] {str(e)}")
            logging.error(f"Download of {filename} failed: {e}")
            raise
    
    def get(self, section: str, key: str, data_type: type = str, from_site: bool = False) -> Any:
        """
        Read a value from the configuration.
        
        Args:
            section (str): Section in the configuration
            key (str): Key to read
            data_type (type, optional): Expected data type. Default: str
            from_site (bool, optional): Whether to read from the site configuration. Default: False
            
        Returns:
            Any: The key value converted to the specified data type
        """
        cache_key = f"{'site' if from_site else 'config'}.{section}.{key}"
        logging.info(f"Reading key: {cache_key}")
        
        # Check if the value is in the cache
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Choose the appropriate source
        config_source = self.configSite if from_site else self.config
        
        # Check if the section and key exist
        if section not in config_source:
            raise ValueError(f"Section '{section}' not found in {'site' if from_site else 'main'} configuration")
        
        if key not in config_source[section]:
            raise ValueError(f"Key '{key}' not found in section '{section}' of {'site' if from_site else 'main'} configuration")
        
        # Get and convert the value
        value = config_source[section][key]
        converted_value = self._convert_to_data_type(value, data_type)
        
        # Save in cache
        self.cache[cache_key] = converted_value
        
        return converted_value
    
    def _convert_to_data_type(self, value: Any, data_type: type) -> Any:
        """
        Convert the value to the specified data type.
        
        Args:
            value (Any): Value to convert
            data_type (type): Target data type
            
        Returns:
            Any: Converted value
        """
        try:
            if data_type == int:
                return int(value)
            elif data_type == float:
                return float(value)
            elif data_type == bool:
                if isinstance(value, str):
                    return value.lower() in ("yes", "true", "t", "1")
                return bool(value)
            elif data_type == list:
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    return [item.strip() for item in value.split(',')]
                return [value]
            elif data_type == dict:
                if isinstance(value, dict):
                    return value
                raise ValueError(f"Cannot convert {type(value).__name__} to dict")
            else:
                return value
        except Exception as e:
            logging.error(f"Error converting to {data_type.__name__}: {e}")
            raise ValueError(f"Cannot convert '{value}' to {data_type.__name__}: {str(e)}")
    
    # Getters for main configuration
    def get_string(self, section: str, key: str) -> str:
        """Read a string from the main configuration."""
        return self.get(section, key, str)
    
    def get_int(self, section: str, key: str) -> int:
        """Read an integer from the main configuration."""
        return self.get(section, key, int)
    
    def get_float(self, section: str, key: str) -> float:
        """Read a float from the main configuration."""
        return self.get(section, key, float)
    
    def get_bool(self, section: str, key: str) -> bool:
        """Read a boolean from the main configuration."""
        return self.get(section, key, bool)
    
    def get_list(self, section: str, key: str) -> List[str]:
        """Read a list from the main configuration."""
        return self.get(section, key, list)
    
    def get_dict(self, section: str, key: str) -> dict:
        """Read a dictionary from the main configuration."""
        return self.get(section, key, dict)
    
    # Getters for site configuration
    def get_site(self, section: str, key: str) -> Any:
        """Read a value from the site configuration."""
        return self.get(section, key, str, True)
    
    def get_site_string(self, section: str, key: str) -> str:
        """Read a string from the site configuration."""
        return self.get(section, key, str, True)
    
    def get_site_int(self, section: str, key: str) -> int:
        """Read an integer from the site configuration."""
        return self.get(section, key, int, True)
    
    def get_site_float(self, section: str, key: str) -> float:
        """Read a float from the site configuration."""
        return self.get(section, key, float, True)
    
    def get_site_bool(self, section: str, key: str) -> bool:
        """Read a boolean from the site configuration."""
        return self.get(section, key, bool, True)
    
    def get_site_list(self, section: str, key: str) -> List[str]:
        """Read a list from the site configuration."""
        return self.get(section, key, list, True)
    
    def get_site_dict(self, section: str, key: str) -> dict:
        """Read a dictionary from the site configuration."""
        return self.get(section, key, dict, True)
    
    def set_key(self, section: str, key: str, value: Any, to_site: bool = False) -> None:
        """
        Set a key in the configuration.
        
        Args:
            section (str): Section in the configuration
            key (str): Key to set
            value (Any): Value to associate with the key
            to_site (bool, optional): Whether to set in the site configuration. Default: False
        """
        try:
            config_target = self.configSite if to_site else self.config
            
            if section not in config_target:
                config_target[section] = {}
            
            config_target[section][key] = value
            
            # Update the cache
            cache_key = f"{'site' if to_site else 'config'}.{section}.{key}"
            self.cache[cache_key] = value
            
            logging.info(f"Key '{key}' set in section '{section}' of {'site' if to_site else 'main'} configuration")
        
        except Exception as e:
            error_msg = f"Error setting key '{key}' in section '{section}' of {'site' if to_site else 'main'} configuration: {e}"
            logging.error(error_msg)
            console.print(f"[bold red]{error_msg}[/bold red]")
    
    def save_config(self) -> None:
        """Save the main configuration to file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.config, f, indent=4)

            logging.info(f"Configuration saved to: {self.file_path}")

        except Exception as e:
            error_msg = f"Error saving configuration: {e}"
            console.print(f"[bold red]{error_msg}[/bold red]")
            logging.error(error_msg)
    
    def get_all_sites(self) -> List[str]:
        """
        Get the list of all available sites.
        
        Returns:
            List[str]: List of site names
        """
        return list(self.configSite.keys())
    
    def has_section(self, section: str, in_site: bool = False) -> bool:
        """
        Check if a section exists in the configuration.
        
        Args:
            section (str): Section name
            in_site (bool, optional): Whether to check in the site configuration. Default: False
            
        Returns:
            bool: True if the section exists, False otherwise
        """
        config_source = self.configSite if in_site else self.config
        return section in config_source


def get_use_large_bar():
    """
    Determine if the large bar feature should be enabled.
    
    Returns:
        bool: True if running on PC (Windows, macOS, Linux),
              False if running on Android or iOS.
    """
    return not any(platform in sys.platform for platform in ("android", "ios"))


# Initialize the ConfigManager when the module is imported
config_manager = ConfigManager()