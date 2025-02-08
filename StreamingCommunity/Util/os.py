# 24.01.24

import io
import os
import glob
import sys
import time
import shutil
import hashlib
import logging
import platform
import subprocess
import contextlib
import urllib.request
import importlib.metadata
from pathlib import Path


# External library
import httpx
from unidecode import unidecode
from pathvalidate import sanitize_filename, sanitize_filepath


# Internal utilities
from .ffmpeg_installer import check_ffmpeg
from StreamingCommunity.Util.console import console, msg



class OsManager:
    def __init__(self):
        self.system = self._detect_system()
        self.max_length = self._get_max_length()

    def _detect_system(self) -> str:
        """Detect and normalize operating system name."""
        system = platform.system().lower()
        if system not in ['windows', 'darwin', 'linux']:
            raise ValueError(f"Unsupported operating system: {system}")
        return system

    def _get_max_length(self) -> int:
        """Get max filename length based on OS."""
        return 255 if self.system == 'windows' else 4096

    def _normalize_windows_path(self, path: str) -> str:
        """Normalize Windows paths."""
        if not path or self.system != 'windows':
            return path

        # Preserve network paths (UNC and IP-based)
        if path.startswith('\\\\') or path.startswith('//'):
            return path.replace('/', '\\')

        # Handle drive letters
        if len(path) >= 2 and path[1] == ':':
            drive = path[0:2]
            rest = path[2:].replace('/', '\\').lstrip('\\')
            return f"{drive}\\{rest}"

        return path.replace('/', '\\')

    def _normalize_mac_path(self, path: str) -> str:
        """Normalize macOS paths."""
        if not path or self.system != 'darwin':
            return path

        # Convert Windows separators to Unix
        normalized = path.replace('\\', '/')

        # Ensure absolute paths start with /
        if normalized.startswith('/'):
            return os.path.normpath(normalized)

        return normalized

    def get_sanitize_file(self, filename: str) -> str:
        """Sanitize filename."""
        if not filename:
            return filename

        # Decode and sanitize
        decoded = unidecode(filename)
        sanitized = sanitize_filename(decoded)

        # Split name and extension
        name, ext = os.path.splitext(sanitized)

        # Calculate available length for name considering the '...' and extension
        max_name_length = self.max_length - len('...') - len(ext)

        # Truncate name if it exceeds the max name length
        if len(name) > max_name_length:
            name = name[:max_name_length] + '...'

        # Ensure the final file name includes the extension
        return name + ext

    def get_sanitize_path(self, path: str) -> str:
        """Sanitize complete path."""
        if not path:
            return path

        # Decode unicode characters
        decoded = unidecode(path)

        # Basic path sanitization
        sanitized = sanitize_filepath(decoded)

        if self.system == 'windows':
            # Handle network paths (UNC or IP-based)
            if path.startswith('\\\\') or path.startswith('//'):
                parts = path.replace('/', '\\').split('\\')
                # Keep server/IP and share name as is
                sanitized_parts = parts[:4]
                # Sanitize remaining parts
                if len(parts) > 4:
                    sanitized_parts.extend([
                        self.get_sanitize_file(part)
                        for part in parts[4:]
                        if part
                    ])
                return '\\'.join(sanitized_parts)

            # Handle drive letters
            elif len(path) >= 2 and path[1] == ':':
                drive = path[:2]
                rest = path[2:].lstrip('\\').lstrip('/')
                path_parts = [drive] + [
                    self.get_sanitize_file(part)
                    for part in rest.replace('/', '\\').split('\\')
                    if part
                ]
                return '\\'.join(path_parts)

            # Regular path
            else:
                parts = path.replace('/', '\\').split('\\')
                return '\\'.join(p for p in parts if p)
        else:
            # Handle Unix-like paths (Linux and macOS)
            is_absolute = path.startswith('/')
            parts = path.replace('\\', '/').split('/')
            sanitized_parts = [
                self.get_sanitize_file(part)
                for part in parts
                if part
            ]

            result = '/'.join(sanitized_parts)
            if is_absolute:
                result = '/' + result

            return result

    def create_path(self, path: str, mode: int = 0o755) -> bool:
        """
        Create directory path with specified permissions.

        Args:
            path (str): Path to create.
            mode (int, optional): Directory permissions. Defaults to 0o755.

        Returns:
            bool: True if path created successfully, False otherwise.
        """
        try:
            sanitized_path = self.get_sanitize_path(path)
            os.makedirs(sanitized_path, mode=mode, exist_ok=True)
            return True

        except Exception as e:
            logging.error(f"Path creation error: {e}")
            return False

    def remove_folder(self, folder_path: str) -> bool:
        """
        Safely remove a folder.

        Args:
            folder_path (str): Path of directory to remove.

        Returns:
            bool: Removal status.
        """
        try:
            shutil.rmtree(folder_path)
            return True

        except OSError as e:
            logging.error(f"Folder removal error: {e}")
            return False

    def remove_files_except_one(self, folder_path: str, keep_file: str) -> None:
        """
        Delete all files in a folder except for one specified file.

        Parameters:
            - folder_path (str): The path to the folder containing the files.
            - keep_file (str): The filename to keep in the folder.
        """

        try:
            # List all files in the folder
            files_in_folder = os.listdir(folder_path)

            # Iterate over each file in the folder
            for file_name in files_in_folder:
                file_path = os.path.join(folder_path, file_name)

                # Check if the file is not the one to keep and is a regular file
                if file_name != keep_file and os.path.isfile(file_path):
                    os.remove(file_path)  # Delete the file

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise

    def check_file(self, file_path: str) -> bool:
        """
        Check if a file exists at the given file path.

        Parameters:
            file_path (str): The path to the file.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        try:
            logging.info(f"Check if file exists: {file_path}")
            return os.path.exists(file_path)

        except Exception as e:
            logging.error(f"An error occurred while checking file existence: {e}")
            return False


class InternManager():

    def format_file_size(self, size_bytes: float) -> str:
        """
        Formats a file size from bytes into a human-readable string representation.

        Parameters:
            size_bytes (float): Size in bytes to be formatted.

        Returns:
            str: Formatted string representing the file size with appropriate unit (B, KB, MB, GB, TB).
        """
        if size_bytes <= 0:
            return "0B"

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0

        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes /= 1024
            unit_index += 1

        return f"{size_bytes:.2f} {units[unit_index]}"

    def format_transfer_speed(self, bytes: float) -> str:
        """
        Formats a transfer speed from bytes per second into a human-readable string representation.

        Parameters:
            bytes (float): Speed in bytes per second to be formatted.

        Returns:
            str: Formatted string representing the transfer speed with appropriate unit (Bytes/s, KB/s, MB/s).
        """
        if bytes < 1024:
            return f"{bytes:.2f} Bytes/s"
        elif bytes < 1024 * 1024:
            return f"{bytes / 1024:.2f} KB/s"
        else:
            return f"{bytes / (1024 * 1024):.2f} MB/s"

    @staticmethod
    def check_internet():
        while True:
            try:
                httpx.get("https://www.google.com", timeout=15)
                break

            except urllib.error.URLError:
                console.log("[bold red]Internet is not available. Waiting...[/bold red]")
                time.sleep(5)


class OsSummary:

    def __init__(self):
        self.ffmpeg_path = None
        self.ffprobe_path = None
        self.ffplay_path = None

    def get_binary_directory(self):
        """Get the binary directory based on OS."""
        system = platform.system().lower()
        home = os.path.expanduser('~')

        if system == 'windows':
            return os.path.join(os.path.splitdrive(home)[0] + os.path.sep, 'binary')
        elif system == 'darwin':
            return os.path.join(home, 'Applications', 'binary')
        else:  # linux
            return os.path.join(home, '.local', 'bin', 'binary')

    def check_ffmpeg_location(self, command: list) -> str:
        """
        Check if a specific executable (ffmpeg or ffprobe) is located using the given command.
        Returns the path of the executable or None if not found.
        """
        try:
            result = subprocess.check_output(command, text=True).strip()
            return result.split('\n')[0] if result else None

        except subprocess.CalledProcessError:
            return None

    def get_library_version(self, lib_name: str):
        """
        Retrieve the version of a Python library.

        Args:
            lib_name (str): The name of the Python library.

        Returns:
            str: The library name followed by its version, or `-not installed` if not found.
        """
        try:
            version = importlib.metadata.version(lib_name)
            return f"{lib_name}-{version}"

        except importlib.metadata.PackageNotFoundError:
            return f"{lib_name}-not installed"

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

    def install_library(self, lib_name: str):
        """
        Install a Python library using pip.

        Args:
            lib_name (str): The name of the library to install.
        """
        try:
            console.print(f"Installing {lib_name}...", style="bold yellow")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib_name])
            console.print(f"{lib_name} installed successfully!", style="bold green")

        except subprocess.CalledProcessError as e:
            console.print(f"Failed to install {lib_name}: {e}", style="bold red")
            sys.exit(1)

    def check_python_version(self):
        """
        Check if the installed Python is the official CPython distribution.
        Exits with a message if not the official version.
        """
        python_implementation = platform.python_implementation()

        if python_implementation != "CPython":
            console.print(f"[bold red]Warning: You are using a non-official Python distribution: {python_implementation}.[/bold red]")
            console.print("Please install the official Python from [bold blue]https://www.python.org[/bold blue] and try again.", style="bold yellow")
            sys.exit(0)

    def get_system_summary(self):
        self.check_python_version()
        InternManager().check_internet()

        # Python info
        python_version = sys.version.split()[0]
        python_implementation = platform.python_implementation()
        arch = platform.machine()
        os_info = platform.platform()
        glibc_version = 'glibc ' + '.'.join(map(str, platform.libc_ver()[1]))

        console.print(f"[cyan]Python[white]: [bold red]{python_version} ({python_implementation} {arch}) - {os_info} ({glibc_version})[/bold red]")
        logging.info(f"Python: {python_version} ({python_implementation} {arch}) - {os_info} ({glibc_version})")

        # FFmpeg detection
        binary_dir = self.get_binary_directory()
        system = platform.system().lower()
        arch = platform.machine().lower()

        # Map architecture names
        arch_map = {
            'amd64': 'x64',
            'x86_64': 'x64',
            'x64': 'x64',
            'arm64': 'arm64',
            'aarch64': 'arm64',
            'armv7l': 'arm',
            'i386': 'ia32',
            'i686': 'ia32'
        }
        arch = arch_map.get(arch, arch)

        # Check binary directory
        if os.path.exists(binary_dir):

            # Search for any file containing 'ffmpeg' and the architecture
            ffmpeg_files = glob.glob(os.path.join(binary_dir, f'*ffmpeg*{arch}*'))
            ffprobe_files = glob.glob(os.path.join(binary_dir, f'*ffprobe*{arch}*'))

            if ffmpeg_files and ffprobe_files:
                self.ffmpeg_path = ffmpeg_files[0]
                self.ffprobe_path = ffprobe_files[0]

                # Set executable permissions if needed
                if system != 'windows':
                    os.chmod(self.ffmpeg_path, 0o755)
                    os.chmod(self.ffprobe_path, 0o755)
            else:
                self.ffmpeg_path, self.ffprobe_path, self.ffplay_path = check_ffmpeg()
        else:
            self.ffmpeg_path, self.ffprobe_path, self.ffplay_path = check_ffmpeg()

        if not self.ffmpeg_path or not self.ffprobe_path:
            console.log("[red]Can't locate ffmpeg or ffprobe")
            sys.exit(0)

        console.print(f"[cyan]Path[white]: [red]ffmpeg [bold yellow]'{self.ffmpeg_path}'[/bold yellow][white], [red]ffprobe '[bold yellow]{self.ffprobe_path}'[/bold yellow]")

        # Handle requirements.txt
        if not getattr(sys, 'frozen', False):
            requirements_file = 'requirements.txt'

            requirements_file = Path(__file__).parent.parent.parent / requirements_file

            if not os.path.exists(requirements_file):
                self.download_requirements(
                    'https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/requirements.txt',
                    requirements_file
                )

            optional_libraries = [line.strip().split("=")[0] for line in open(requirements_file, 'r', encoding='utf-8-sig')]

            for lib in optional_libraries:
                installed_version = self.get_library_version(lib.split("<")[0])
                if 'not installed' in installed_version:
                    user_response = msg.ask(f"{lib} is not installed. Do you want to install it? (yes/no)", default="y")
                    if user_response.lower().strip() in ["yes", "y"]:
                        self.install_library(lib)
                else:
                    logging.info(f"Library: {installed_version}")

            #console.print(f"[cyan]Libraries[white]: [bold red]{', '.join([self.get_library_version(lib) for lib in optional_libraries])}[/bold red]\n")
            logging.info(f"Libraries: {', '.join([self.get_library_version(lib) for lib in optional_libraries])}")


os_manager = OsManager()
internet_manager = InternManager()
os_summary = OsSummary()


@contextlib.contextmanager
def suppress_output():
    with contextlib.redirect_stdout(io.StringIO()):
        yield

def compute_sha1_hash(input_string: str) -> str:
    """
    Computes the SHA-1 hash of the input string.

    Parameters:
        - input_string (str): The string to be hashed.

    Returns:
        str: The SHA-1 hash of the input string.
    """
    # Compute the SHA-1 hash
    hashed_string = hashlib.sha1(input_string.encode()).hexdigest()

    # Return the hashed string
    return hashed_string
