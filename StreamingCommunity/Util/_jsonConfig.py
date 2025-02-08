# 29.01.24

import os
import sys
import json
import logging
from pathlib import Path
from typing import Any, List


class ConfigManager:
    def __init__(self, file_name: str = 'config.json') -> None:
        """Initialize the ConfigManager.

        Parameters:
            - file_path (str, optional): The path to the configuration file. Default is 'config.json'.
        """
        self.file_path = Path(__file__).parent.parent.parent / file_name
        self.config = {}
        self.cache = {}

    def read_config(self) -> None:
        """Read the configuration file."""
        try:
            logging.info(f"Reading file: {self.file_path}")

            # Check if file exists
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    self.config = json.load(f)
                logging.info("Configuration file loaded successfully.")

            # Download config.json if it doesn't exist locally
            else:
                logging.info("Configuration file does not exist. Downloading...")
                self.download_requirements(
                    'https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/config.json',
                    self.file_path
                )

                # Load the downloaded config.json into the config attribute
                with open(self.file_path, 'r') as f:
                    self.config = json.load(f)
                logging.info("Configuration file downloaded and saved.")

            logging.info("Configuration file processed successfully.")

        except Exception as e:
            logging.error(f"Error reading configuration file: {e}")

    def download_requirements(self, url: str, filename: str):
        """
        Download the requirements.txt file from the specified URL if not found locally using requests.

        Args:
            url (str): The URL to download the requirements file from.
            filename (str): The local filename to save the requirements file as.
        """
        try:
            import requests

            logging.info(f"{filename} not found locally. Downloading from {url}...")
            response = requests.get(url)

            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)

            else:
                logging.error(f"Failed to download {filename}. HTTP Status code: {response.status_code}")
                sys.exit(0)

        except Exception as e:
            logging.error(f"Failed to download {filename}: {e}")
            sys.exit(0)

    def read_key(self, section: str, key: str, data_type: type = str) -> Any:
        """Read a key from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.
            - data_type (type, optional): The expected data type of the key's value. Default is str.

        Returns:
            The value of the key converted to the specified data type.
        """
        cache_key = f"{section}.{key}"
        logging.info(f"Read key: {cache_key}")

        if cache_key in self.cache:
            return self.cache[cache_key]

        if section in self.config and key in self.config[section]:
            value = self.config[section][key]
        else:
            raise ValueError(f"Key '{key}' not found in section '{section}'")

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

    def get(self, section: str, key: str) -> Any:
        """Read a value from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.

        Returns:
            The value associated with the key.
        """
        return self.read_key(section, key)

    def get_int(self, section: str, key: str) -> int:
        """Read an integer value from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.

        Returns:
            int: The integer value.
        """
        return self.read_key(section, key, int)

    def get_float(self, section: str, key: str) -> int:
        """Read an float value from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.

        Returns:
            float: The float value.
        """
        return self.read_key(section, key, float)

    def get_bool(self, section: str, key: str) -> bool:
        """Read a boolean value from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.

        Returns:
            bool: The boolean value.
        """
        return self.read_key(section, key, bool)

    def get_list(self, section: str, key: str) -> List[str]:
        """Read a list value from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.

        Returns:
            list: The list value.
        """
        return self.read_key(section, key, list)

    def get_dict(self, section: str, key: str) -> dict:
        """Read a dictionary value from the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be read.

        Returns:
            dict: The dictionary value.
        """
        return self.read_key(section, key, dict)

    def set_key(self, section: str, key: str, value: Any) -> None:
        """Set a key in the configuration file.

        Parameters:
            - section (str): The section in the configuration file.
            - key (str): The key to be set.
            - value (Any): The value to be associated with the key.
        """
        try:
            if section not in self.config:
                self.config[section] = {}

            self.config[section][key] = value
            cache_key = f"{section}.{key}"
            self.cache[cache_key] = value
            self.write_config()

        except Exception as e:
            print(f"Error setting key '{key}' in section '{section}': {e}")

    def write_config(self) -> None:
        """Write the configuration to the file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error writing configuration file: {e}")


# Initialize
config_manager = ConfigManager()
config_manager.read_config()
