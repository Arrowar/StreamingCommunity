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
            # Use the current working directory where the script is executed
            base_path = os.getcwd()
            
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

        self.fetch_domain_online = True
        
        console.print(f"[bold cyan]Initializing ConfigManager:[/bold cyan] [green]{self.file_path}[/green]")
        
        # Load the configuration
        self.load_config()
        
    def load_config(self) -> None:
        """Load the configuration and initialize all settings."""
        if not os.path.exists(self.file_path):
            console.print(f"[bold red]WARNING: Configuration file not found:[/bold red] {self.file_path}")
            console.print("[bold yellow]Downloading from repository...[/bold yellow]")
            self._download_reference_config()
        
        # Load the configuration file
        try:
            with open(self.file_path, 'r') as f:
                self.config = json.load(f)
            console.print(f"[bold green]Configuration loaded:[/bold green] {len(self.config)} keys")
            
            # Update settings from the configuration
            self._update_settings_from_config()
                
            # Load site data based on fetch_domain_online setting
            self._load_site_data()
                
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
        
        # Get fetch_domain_online setting (True by default)
        self.fetch_domain_online = default_section.get('fetch_domain_online', True)
        
        console.print(f"[bold cyan]Fetch domains online:[/bold cyan] [{'green' if self.fetch_domain_online else 'yellow'}]{self.fetch_domain_online}[/{'green' if self.fetch_domain_online else 'yellow'}]")
    
    def _download_reference_config(self) -> None:
        """Download the reference configuration from GitHub."""
        console.print(f"[bold cyan]Downloading configuration:[/bold cyan] [green]{self.reference_config_url}[/green]")

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
    
    def _load_site_data(self) -> None:
        """Load site data based on fetch_domain_online setting."""
        if self.fetch_domain_online:
            self._load_site_data_online()
        else:
            self._load_site_data_from_file()
    
    def _load_site_data_online(self) -> None:
        """Load site data from GitHub and update local domains.json file."""
        domains_github_url = "https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/.github/.domain/domains.json"
        headers = {
            "User-Agent": get_userAgent()
        }
        
        try:
            response = requests.get(domains_github_url, timeout=8, headers=headers)

            if response.ok:
                self.configSite = response.json()
                
                # Determine which file to save to
                self._save_domains_to_appropriate_location()
                
            else:
                console.print(f"[bold red]GitHub request failed:[/bold red] HTTP {response.status_code}, {response.text[:100]}")
                self._handle_site_data_fallback()
        
        except json.JSONDecodeError as e:
            console.print(f"[bold red]Error parsing JSON from GitHub:[/bold red] {str(e)}")
            self._handle_site_data_fallback()
            
        except Exception as e:
            console.print(f"[bold red]GitHub connection error:[/bold red] {str(e)}")
            self._handle_site_data_fallback()
    
    def _save_domains_to_appropriate_location(self) -> None:
        """Save domains to the appropriate location based on existing files."""
        if getattr(sys, 'frozen', False):
            # If the application is frozen (e.g., PyInstaller)
            base_path = os.path.dirname(sys.executable)
        else:
            # Use the current working directory where the script is executed
            base_path = os.getcwd()
            
        # Check for GitHub structure first
        github_domains_path = os.path.join(base_path, '.github', '.domain', 'domains.json')
        
        try:
            if os.path.exists(github_domains_path):
                
                # Update existing GitHub structure file
                with open(github_domains_path, 'w', encoding='utf-8') as f:
                    json.dump(self.configSite, f, indent=4, ensure_ascii=False)
                
            elif not os.path.exists(self.domains_path):
                # Save to root only if it doesn't exist and GitHub structure doesn't exist
                with open(self.domains_path, 'w', encoding='utf-8') as f:
                    json.dump(self.configSite, f, indent=4, ensure_ascii=False)
                console.print(f"[bold green]Domains saved to:[/bold green] {self.domains_path}")
                
            else:
                # Root file exists, don't overwrite it
                console.print(f"[bold yellow]Local domains.json already exists, not overwriting:[/bold yellow] {self.domains_path}")
                console.print("[bold yellow]Tip: Delete the file if you want to recreate it from GitHub[/bold yellow]")
                
        except Exception as save_error:
            console.print(f"[bold yellow]Warning: Could not save domains to file:[/bold yellow] {str(save_error)}")

            # Try to save to root as fallback only if it doesn't exist
            if not os.path.exists(self.domains_path):
                try:
                    with open(self.domains_path, 'w', encoding='utf-8') as f:
                        json.dump(self.configSite, f, indent=4, ensure_ascii=False)
                    console.print(f"[bold green]Domains saved to fallback location:[/bold green] {self.domains_path}")
                except Exception as fallback_error:
                    console.print(f"[bold red]Failed to save to fallback location:[/bold red] {str(fallback_error)}")
    
    def _load_site_data_from_file(self) -> None:
        """Load site data from local domains.json file."""
        try:
            # Determine the base path
            if getattr(sys, 'frozen', False):

                # If the application is frozen (e.g., PyInstaller)
                base_path = os.path.dirname(sys.executable)
            else:

                # Use the current working directory where the script is executed
                base_path = os.getcwd()
            
            # Check for GitHub structure first
            github_domains_path = os.path.join(base_path, '.github', '.domain', 'domains.json')
            
            if os.path.exists(github_domains_path):
                console.print(f"[bold cyan]Reading domains from GitHub structure:[/bold cyan] {github_domains_path}")
                with open(github_domains_path, 'r', encoding='utf-8') as f:
                    self.configSite = json.load(f)
                
                site_count = len(self.configSite) if isinstance(self.configSite, dict) else 0
                console.print(f"[bold green]Domains loaded from GitHub structure:[/bold green] {site_count} streaming services")
                
            elif os.path.exists(self.domains_path):
                console.print(f"[bold cyan]Reading domains from root:[/bold cyan] {self.domains_path}")
                with open(self.domains_path, 'r', encoding='utf-8') as f:
                    self.configSite = json.load(f)
                
                site_count = len(self.configSite) if isinstance(self.configSite, dict) else 0
                console.print(f"[bold green]Domains loaded from root file:[/bold green] {site_count} streaming services")

            else:
                error_msg = f"domains.json not found in GitHub structure ({github_domains_path}) or root ({self.domains_path}) and fetch_domain_online is disabled"
                console.print(f"[bold red]Configuration error:[/bold red] {error_msg}")
                console.print("[bold yellow]Tip: Set 'fetch_domain_online' to true to download domains from GitHub[/bold yellow]")
                self.configSite = {}
        
        except Exception as e:
            console.print(f"[bold red]Local domain file error:[/bold red] {str(e)}")
            self.configSite = {}
    
    def _handle_site_data_fallback(self) -> None:
        """Handle site data fallback in case of error."""
        # Determine the base path
        if getattr(sys, 'frozen', False):
            
            # If the application is frozen (e.g., PyInstaller)
            base_path = os.path.dirname(sys.executable)
        else:
            # Use the current working directory where the script is executed
            base_path = os.getcwd()
        
        # Check for GitHub structure first
        github_domains_path = os.path.join(base_path, '.github', '.domain', 'domains.json')
        
        if os.path.exists(github_domains_path):
            console.print("[bold yellow]Attempting fallback to GitHub structure domains.json file...[/bold yellow]")
            try:
                with open(github_domains_path, 'r', encoding='utf-8') as f:
                    self.configSite = json.load(f)
                console.print("[bold green]Fallback to GitHub structure successful[/bold green]")
                return
            except Exception as fallback_error:
                console.print(f"[bold red]GitHub structure fallback failed:[/bold red] {str(fallback_error)}")
        
        if os.path.exists(self.domains_path):
            console.print("[bold yellow]Attempting fallback to root domains.json file...[/bold yellow]")
            try:
                with open(self.domains_path, 'r', encoding='utf-8') as f:
                    self.configSite = json.load(f)
                console.print("[bold green]Fallback to root domains successful[/bold green]")
                return
            except Exception as fallback_error:
                console.print(f"[bold red]Root domains fallback failed:[/bold red] {str(fallback_error)}")
        
        console.print("[bold red]No local domains.json file available for fallback[/bold red]")
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
            response = requests.get(url, timeout=8, headers={'User-Agent': get_userAgent()}, verify=self.get_bool('REQUESTS', 'verify'))
            
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
    
    def get(self, section: str, key: str, data_type: type = str, from_site: bool = False, default: Any = None) -> Any:
        """
        Read a value from the configuration.
        
        Args:
            section (str): Section in the configuration
            key (str): Key to read
            data_type (type, optional): Expected data type. Default: str
            from_site (bool, optional): Whether to read from the site configuration. Default: False
            default (Any, optional): Default value if key is not found. Default: None
            
        Returns:
            Any: The key value converted to the specified data type, or default if not found
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
            if default is not None:
                logging.info(f"Section '{section}' not found. Returning default value.")
                return default
            raise ValueError(f"Section '{section}' not found in {'site' if from_site else 'main'} configuration")
        
        if key not in config_source[section]:
            if default is not None:
                logging.info(f"Key '{key}' not found in section '{section}'. Returning default value.")
                return default
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
            if data_type is int:
                return int(value)
            
            elif data_type is float:
                return float(value)
            
            elif data_type is bool:
                if isinstance(value, str):
                    return value.lower() in ("yes", "true", "t", "1")
                return bool(value)
            
            elif data_type is list:
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    return [item.strip() for item in value.split(',')]
                return [value]

            elif data_type is dict:
                if isinstance(value, dict):
                    return value
                
                raise ValueError(f"Cannot convert {type(value).__name__} to dict")
            else:
                return value
        except Exception as e:
            logging.error(f"Error converting to {data_type.__name__}: {e}")
            raise ValueError(f"Cannot convert '{value}' to {data_type.__name__}: {str(e)}")
    
    # Getters for main configuration
    def get_string(self, section: str, key: str, default: str = None) -> str:
        """Read a string from the main configuration."""
        return self.get(section, key, str, default=default)

    def get_int(self, section: str, key: str, default: int = None) -> int:
        """Read an integer from the main configuration."""
        return self.get(section, key, int, default=default)

    def get_float(self, section: str, key: str, default: float = None) -> float:
        """Read a float from the main configuration."""
        return self.get(section, key, float, default=default)

    def get_bool(self, section: str, key: str, default: bool = None) -> bool:
        """Read a boolean from the main configuration."""
        return self.get(section, key, bool, default=default)

    def get_list(self, section: str, key: str, default: List[str] = None) -> List[str]:
        """Read a list from the main configuration."""
        return self.get(section, key, list, default=default)

    def get_dict(self, section: str, key: str, default: dict = None) -> dict:
        """Read a dictionary from the main configuration."""
        return self.get(section, key, dict, default=default)

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


# Initialize the ConfigManager when the module is imported
config_manager = ConfigManager()