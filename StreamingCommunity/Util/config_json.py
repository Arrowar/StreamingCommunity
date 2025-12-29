# 29.01.24

import os
import sys
import json
import logging
import requests
from typing import Any, List, Dict


# External library
from rich.console import Console


# Variable
console = Console()
CONFIG_FILENAME = 'config.json'
LOGIN_FILENAME = 'login.json'
DOMAINS_FILENAME = 'domains.json'
GITHUB_DOMAINS_PATH = '.github/script/domains.json'
CONFIG_DOWNLOAD_URL = 'https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/config.json'
CONFIG_LOGIN_DOWNLOAD_URL = 'https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/login.json'
DOMAINS_DOWNLOAD_URL = 'https://raw.githubusercontent.com/Arrowar/SC_Domains/refs/heads/main/domains.json'


class ConfigAccessor:
    def __init__(self, config_dict: Dict, cache: Dict, cache_prefix: str, cache_enabled: bool = True):
        self._config_dict = config_dict
        self._cache = cache
        self._cache_prefix = cache_prefix
        self._cache_enabled = cache_enabled
    
    def get(self, section: str, key: str, data_type: type = str, default: Any = None) -> Any:
        """
        Read a value from the configuration with caching.
        
        Args:
            section (str): Section in the configuration
            key (str): Key to read
            data_type (type, optional): Expected data type. Default: str
            default (Any, optional): Default value if key is not found. Default: None
            
        Returns:
            Any: The key value converted to the specified data type, or default if not found
        """
        cache_key = f"{self._cache_prefix}.{section}.{key}"
        
        # Check if the value is in the cache
        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Log only if not in cache
        logging.info(f"Reading key: {cache_key}")
        
        # Check if the section and key exist
        if section not in self._config_dict:
            if default is not None:
                logging.info(f"Section '{section}' not found. Returning default value.")
                return default
            raise ValueError(f"Section '{section}' not found in {self._cache_prefix} configuration")
        
        if key not in self._config_dict[section]:
            if default is not None:
                logging.info(f"Key '{key}' not found in section '{section}'. Returning default value.")
                return default
            raise ValueError(f"Key '{key}' not found in section '{section}' of {self._cache_prefix} configuration")
        
        # Get and convert the value
        value = self._config_dict[section][key]
        converted_value = self._convert_to_data_type(value, data_type)
        
        # Save in cache
        if self._cache_enabled:
            self._cache[cache_key] = converted_value
        
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
            error_msg = f"Error converting: {data_type.__name__} to value '{value}' with error: {e}"
            console.print(f"[red]{error_msg}")
            raise ValueError(f"Error converting: {data_type.__name__} to value '{value}' with error: {e}")
    
    def get_int(self, section: str, key: str, default: int = None) -> int:
        """Read an integer from the configuration."""
        return self.get(section, key, int, default=default)

    def get_float(self, section: str, key: str, default: float = None) -> float:
        """Read a float from the configuration."""
        return self.get(section, key, float, default=default)

    def get_bool(self, section: str, key: str, default: bool = None) -> bool:
        """Read a boolean from the configuration."""
        return self.get(section, key, bool, default=default)

    def get_list(self, section: str, key: str, default: List[str] = None) -> List[str]:
        """Read a list from the configuration."""
        return self.get(section, key, list, default=default)

    def get_dict(self, section: str, key: str, default: dict = None) -> dict:
        """Read a dictionary from the configuration."""
        return self.get(section, key, dict, default=default)
    
    def set_key(self, section: str, key: str, value: Any) -> None:
        """
        Set a key in the configuration and update cache.
        
        Args:
            section (str): Section in the configuration
            key (str): Key to set
            value (Any): Value to associate with the key
        """
        try:
            if section not in self._config_dict:
                self._config_dict[section] = {}
            
            self._config_dict[section][key] = value
            
            # Update the cache
            cache_key = f"{self._cache_prefix}.{section}.{key}"
            self._cache[cache_key] = value
            
            logging.info(f"Key '{key}' set in section '{section}' of {self._cache_prefix} configuration")
        
        except Exception as e:
            error_msg = f"Error setting key '{key}' in section '{section}' of {self._cache_prefix} configuration: {e}"
            console.print(f"[red]{error_msg}")


class ConfigManager:
    def __init__(self) -> None:
        """Initialize the ConfigManager with caching."""
        
        self.base_path = None
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)  # PyInstaller
        else:
            self.base_path = os.getcwd()
            
        # Initialize file paths using static variables
        self.config_file_path = os.path.join(self.base_path, CONFIG_FILENAME)
        self.login_file_path = os.path.join(self.base_path, LOGIN_FILENAME)
        self.domains_path = os.path.join(self.base_path, DOMAINS_FILENAME)
        self.github_domains_path = os.path.join(self.base_path, GITHUB_DOMAINS_PATH)
        
        # Display the actual file paths for debugging
        console.print(f"[cyan]Config path: [green]{self.config_file_path}")
        console.print(f"[cyan]Login path: [green]{self.login_file_path}")
        
        # Initialize data structures
        self._config_data = {}
        self._login_data = {}
        self._domains_data = {}
        
        # Enhanced caching system
        self.cache: Dict[str, Any] = {}
        self._cache_enabled = True
        
        # Create accessors
        self.config = ConfigAccessor(self._config_data, self.cache, "config", self._cache_enabled)
        self.login = ConfigAccessor(self._login_data, self.cache, "login", self._cache_enabled)
        self.domain = ConfigAccessor(self._domains_data, self.cache, "domain", self._cache_enabled)
        
        # Load the configuration
        self.fetch_domain_online = True
        self.load_all_configs()
        
    def load_all_configs(self) -> None:
        """Load all configuration files."""
        self._load_config()
        self._load_login()
        self._update_settings_from_config()
        self._load_site_data()
    
    def _load_config(self) -> None:
        """Load the main configuration file."""
        if not os.path.exists(self.config_file_path):
            console.print(f"[red]WARNING: Configuration file not found: {self.config_file_path}")
            console.print("[yellow]Downloading from repository...")
            self._download_file(CONFIG_DOWNLOAD_URL, self.config_file_path, "config.json")
        
        try:
            with open(self.config_file_path, 'r') as f:
                self._config_data.clear()
                self._config_data.update(json.load(f))
            
            # Pre-cache commonly used configuration values
            self._precache_config_values()
                
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing config JSON: {str(e)}")
            self._handle_config_error()

        except Exception as e:
            console.print(f"[red]Error loading configuration: {str(e)}")
            self._handle_config_error()
    
    def _load_login(self) -> None:
        """Load the login configuration file."""
        if not os.path.exists(self.login_file_path):
            console.print(f"[yellow]WARNING: Login file not found: {self.login_file_path}")
            console.print("[yellow]Downloading from repository...")
            try:
                self._download_file(CONFIG_LOGIN_DOWNLOAD_URL, self.login_file_path, "login.json")
            except Exception as e:
                console.print(f"[yellow]Could not download login.json: {str(e)}")
                console.print("[yellow]Creating empty login configuration...")
                self._login_data.clear()
                return
        
        try:
            with open(self.login_file_path, 'r') as f:
                self._login_data.clear()
                self._login_data.update(json.load(f))
            
            console.print("[green]Login configuration loaded successfully")
                
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing login JSON: {str(e)}")
            self._login_data.clear()

        except Exception as e:
            console.print(f"[red]Error loading login configuration: {str(e)}")
            self._login_data.clear()
    
    def _precache_config_values(self) -> None:
        """Pre-cache commonly used configuration values."""
        common_keys = [
            ('DEFAULT', 'debug', bool),
            ('M3U8_CONVERSION', 'use_gpu', bool),
            ('M3U8_CONVERSION', 'param_video', str),
            ('M3U8_CONVERSION', 'param_audio', str),
            ('M3U8_CONVERSION', 'param_final', str),
            ('M3U8_DOWNLOAD', 'cleanup_tmp_folder', bool),
            ('M3U8_DOWNLOAD', 'default_video_workers', int),
            ('M3U8_DOWNLOAD', 'default_audio_workers', int),
            ('M3U8_DOWNLOAD', 'segment_timeout', int),
            ('M3U8_DOWNLOAD', 'enable_retry', bool),
            ('M3U8_DOWNLOAD', 'merge_subs', bool),
            ('REQUESTS', 'verify', bool),
            ('REQUESTS', 'timeout', int),
            ('REQUESTS', 'max_retry', int)
        ]
        
        cached_count = 0
        for section, key, data_type in common_keys:
            try:
                cache_key = f"config.{section}.{key}"
                
                if section in self._config_data and key in self._config_data[section]:
                    value = self._config_data[section][key]
                    converted_value = self.config._convert_to_data_type(value, data_type)
                    self.cache[cache_key] = converted_value
                    cached_count += 1
                    
            except Exception as e:
                logging.warning(f"Failed to precache {section}.{key}: {e}")
    
    def _handle_config_error(self) -> None:
        """Handle configuration errors by downloading the reference version."""
        console.print("[yellow]Attempting to retrieve reference configuration...")
        self._download_file(CONFIG_DOWNLOAD_URL, self.config_file_path, "config.json")
        
        # Reload the configuration
        try:
            with open(self.config_file_path, 'r') as f:
                self._config_data.clear()
                self._config_data.update(json.load(f))
            
            # Pre-cache after reload
            self._precache_config_values()
            self._update_settings_from_config()
            console.print("[green]Reference configuration loaded successfully")
            
        except Exception as e:
            console.print(f"[red]Critical configuration error: {str(e)}")
            console.print("[red]Unable to proceed. The application will terminate.")
            sys.exit(1)
    
    def _update_settings_from_config(self) -> None:
        """Update internal settings from loaded configurations."""
        default_section = self._config_data.get('DEFAULT', {})
        
        # Get fetch_domain_online setting (True by default)
        self.fetch_domain_online = default_section.get('fetch_domain_online', True)
    
    def _download_file(self, url: str, file_path: str, file_name: str) -> None:
        """Download a file from a URL."""
        try:
            response = requests.get(url, timeout=8, headers={'User-Agent': "Mozilla/5.0"})
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                file_size = len(response.content) / 1024
                console.print(f"[green]Download complete: {file_name} ({file_size:.2f} KB)")
            else:
                error_msg = f"HTTP Error: {response.status_code}, Response: {response.text[:100]}"
                console.print(f"[red]Download failed: {error_msg}")
                raise Exception(error_msg)
            
        except Exception as e:
            console.print(f"[red]Download error: {str(e)} for url: {url}")
            raise
    
    def _load_site_data(self) -> None:
        """Load site data based on fetch_domain_online setting."""
        if self.fetch_domain_online:
            self._load_site_data_online()
        else:
            self._load_site_data_from_file()
    
    def _load_site_data_online(self) -> None:
        """Load site data from GitHub and update local domains.json file."""
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        try:
            response = requests.get(DOMAINS_DOWNLOAD_URL, timeout=8, headers=headers)

            if response.ok:
                self._domains_data.clear()
                self._domains_data.update(response.json())
                
                # Determine which file to save to
                self._save_domains_to_appropriate_location()
                
            else:
                console.print(f"[red]GitHub request failed: HTTP {response.status_code}, {response.text[:100]}")
                self._handle_site_data_fallback()
        
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing JSON from GitHub: {str(e)}")
            self._handle_site_data_fallback()
            
        except Exception as e:
            console.print(f"[red]GitHub connection error: {str(e)}")
            self._handle_site_data_fallback()
    
    def _save_domains_to_appropriate_location(self) -> None:
        """Save domains to the appropriate location based on existing files."""
        script_dir = os.path.join(self.base_path, ".github", "script")
        if os.path.isdir(script_dir):
            target_path = os.path.join(script_dir, DOMAINS_FILENAME)
            console.print(f"[cyan]Domain path: [green]{target_path}")
        else:
            target_path = self.domains_path
            console.print(f"[cyan]Domain path: [green]{target_path}")

        try:
            if not os.path.exists(target_path):
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(self._domains_data, f, indent=4, ensure_ascii=False)
                
        except Exception as save_error:
            console.print(f"[yellow]Warning: Could not save domains to file: {str(save_error)}")
            if target_path != self.domains_path and not os.path.exists(self.domains_path):
                try:
                    with open(self.domains_path, 'w', encoding='utf-8') as f:
                        json.dump(self._domains_data, f, indent=4, ensure_ascii=False)
                    console.print(f"[green]Domains saved to fallback location: {self.domains_path}")
                except Exception as fallback_error:
                    console.print(f"[red]Failed to save to fallback location: {str(fallback_error)}")

    def _load_site_data_from_file(self) -> None:
        """Load site data from local domains.json file."""
        try:
            if os.path.exists(self.github_domains_path):
                console.print(f"[cyan]Domain path: [green]{self.github_domains_path}")
                with open(self.github_domains_path, 'r', encoding='utf-8') as f:
                    self._domains_data.clear()
                    self._domains_data.update(json.load(f))
                
                site_count = len(self._domains_data) if isinstance(self._domains_data, dict) else 0
                
            elif os.path.exists(self.domains_path):
                console.print(f"[cyan]Reading domains from root: {self.domains_path}")
                with open(self.domains_path, 'r', encoding='utf-8') as f:
                    self._domains_data.clear()
                    self._domains_data.update(json.load(f))
                
                site_count = len(self._domains_data) if isinstance(self._domains_data, dict) else 0
                console.print(f"[green]Domains loaded from root file: {site_count} streaming services")

            else:
                console.print("[cyan]Domain path: [red]Disabled")
                self._domains_data.clear()
        
        except Exception as e:
            console.print(f"[red]Local domain file error: {str(e)}")
            self._domains_data.clear()
    
    def _handle_site_data_fallback(self) -> None:
        """Handle site data fallback in case of error."""
        if os.path.exists(self.github_domains_path):
            console.print("[yellow]Attempting fallback to GitHub structure domains.json file...")
            try:
                with open(self.github_domains_path, 'r', encoding='utf-8') as f:
                    self._domains_data.clear()
                    self._domains_data.update(json.load(f))
                console.print("[green]Fallback to GitHub structure successful")
                return
            except Exception as fallback_error:
                console.print(f"[red]GitHub structure fallback failed: {str(fallback_error)}")
        
        if os.path.exists(self.domains_path):
            console.print("[yellow]Attempting fallback to root domains.json file...")
            try:
                with open(self.domains_path, 'r', encoding='utf-8') as f:
                    self._domains_data.clear()
                    self._domains_data.update(json.load(f))
                console.print("[green]Fallback to root domains successful")
                return
            except Exception as fallback_error:
                console.print(f"[red]Root domains fallback failed: {str(fallback_error)}")
        
        console.print("[red]No local domains.json file available for fallback")
        self._domains_data.clear()
    
    def save_config(self) -> None:
        """Save the main configuration to file."""
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(self._config_data, f, indent=4)

            logging.info(f"Configuration saved to: {self.config_file_path}")

        except Exception as e:
            console.print(f"[red]Error saving configuration: {e}")
    
    def save_login(self) -> None:
        """Save the login configuration to file."""
        try:
            with open(self.login_file_path, 'w') as f:
                json.dump(self._login_data, f, indent=4)

            logging.info(f"Login configuration saved to: {self.login_file_path}")

        except Exception as e:
            console.print(f"[red]Error saving login configuration: {e}")
    
    def save_domains(self) -> None:
        """Save the domains configuration to file."""
        try:
            script_dir = os.path.join(self.base_path, ".github", "script")
            if os.path.isdir(script_dir):
                target_path = os.path.join(script_dir, DOMAINS_FILENAME)
            else:
                target_path = self.domains_path
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(self._domains_data, f, indent=4, ensure_ascii=False)

            logging.info(f"Domains configuration saved to: {target_path}")

        except Exception as e:
            console.print(f"[red]Error saving domains configuration: {e}")


# Initialize the ConfigManager when the module is imported
config_manager = ConfigManager()