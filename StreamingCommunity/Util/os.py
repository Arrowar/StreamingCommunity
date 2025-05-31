# 24.01.24

import io
import os
import glob
import sys
import shutil
import hashlib
import logging
import platform
import inspect
import subprocess
import contextlib
import importlib.metadata
import socket

# External library
from unidecode import unidecode
from rich.console import Console
from rich.prompt import Prompt
from pathvalidate import sanitize_filename, sanitize_filepath
from dns.resolver import dns


# Internal utilities
from .ffmpeg_installer import check_ffmpeg


# Variable
msg = Prompt()
console = Console()


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

        # Decode unicode characters and perform basic sanitization
        decoded = unidecode(path)
        sanitized = sanitize_filepath(decoded)

        if self.system == 'windows':
            # Handle network paths (UNC or IP-based)
            if sanitized.startswith('\\\\') or sanitized.startswith('//'):
                parts = sanitized.replace('/', '\\').split('\\')
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
            elif len(sanitized) >= 2 and sanitized[1] == ':':
                drive = sanitized[:2]
                rest = sanitized[2:].lstrip('\\').lstrip('/')
                path_parts = [drive] + [
                    self.get_sanitize_file(part)
                    for part in rest.replace('/', '\\').split('\\')
                    if part
                ]
                return '\\'.join(path_parts)

            # Regular path
            else:
                parts = sanitized.replace('/', '\\').split('\\')
                return '\\'.join(p for p in parts if p)
        else:
            # Handle Unix-like paths (Linux and macOS)
            is_absolute = sanitized.startswith('/')
            parts = sanitized.replace('\\', '/').split('/')
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
            # First, try to make all files writable
            for root, dirs, files in os.walk(self.temp_dir):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    os.chmod(dir_path, 0o755)  # rwxr-xr-x
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    os.chmod(file_path, 0o644)  # rw-r--r--
            
            # Then remove the directory tree
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            # If directory still exists after rmtree, try force remove
            if os.path.exists(self.temp_dir):
                import subprocess
                subprocess.run(['rm', '-rf', self.temp_dir], check=True)
                
        except Exception as e:
            logging.error(f"Failed to cleanup temporary directory: {str(e)}")
            pass

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

    # def check_dns_provider(self):
    #     """
    #     Check if the system's current DNS server matches any known DNS providers.
        
    #     Returns:
    #         bool: True if the current DNS server matches a known provider,
    #               False if no match is found or in case of errors
    #     """
    #     dns_providers = {
    #         "Cloudflare": ["1.1.1.1", "1.0.0.1"],
    #         "Google": ["8.8.8.8", "8.8.4.4"],
    #         "OpenDNS": ["208.67.222.222", "208.67.220.220"],
    #         "Quad9": ["9.9.9.9", "149.112.112.112"],
    #         "AdGuard": ["94.140.14.14", "94.140.15.15"],
    #         "Comodo": ["8.26.56.26", "8.20.247.20"],
    #         "Level3": ["209.244.0.3", "209.244.0.4"],
    #         "Norton": ["199.85.126.10", "199.85.127.10"],
    #         "CleanBrowsing": ["185.228.168.9", "185.228.169.9"],
    #         "Yandex": ["77.88.8.8", "77.88.8.1"]
    #     }
        
    #     try:
    #         resolver = dns.resolver.Resolver()
    #         nameservers = resolver.nameservers
            
    #         if not nameservers:
    #             return False
                
    #         for server in nameservers:
    #             for provider, ips in dns_providers.items():
    #                 if server in ips:
    #                     return True
    #         return False
            
    #     except Exception:
    #         return False

    def check_dns_resolve(self):
        """
        Check if the system's current DNS server can resolve a domain name.
        Works on both Windows and Unix-like systems.
        
        Returns:
            bool: True if the current DNS server can resolve a domain name,
                    False if can't resolve or in case of errors
        """
        test_domains = ["github.com", "google.com", "microsoft.com", "amazon.com"]
        
        try:
            for domain in test_domains:
                # socket.gethostbyname() works consistently across all platforms
                socket.gethostbyname(domain)
            return True
        except (socket.gaierror, socket.error):
            return False

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
        python_version = platform.python_version()

        if python_implementation != "CPython":
            console.print(f"[bold red]Warning: You are using a non-official Python distribution: {python_implementation}.[/bold red]")
            console.print("Please install the official Python from [bold blue]https://www.python.org[/bold blue] and try again.", style="bold yellow")
            sys.exit(0)

        console.print(f"[cyan]Python version: [bold red]{python_version}[/bold red]")

    def get_system_summary(self):
        self.check_python_version()

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

        console.print(f"[cyan]Path: [red]ffmpeg [bold yellow]'{self.ffmpeg_path}'[/bold yellow][white], [red]ffprobe '[bold yellow]{self.ffprobe_path}'[/bold yellow]")


os_manager = OsManager()
internet_manager = InternManager()
os_summary = OsSummary()


@contextlib.contextmanager
def suppress_output():
    with contextlib.redirect_stdout(io.StringIO()):
        yield

def compute_sha1_hash(input_string: str) -> str:
    """Computes the SHA-1 hash of the input string."""
    return hashlib.sha1(input_string.encode()).hexdigest()

def get_call_stack():
    """Retrieves the current call stack with details about each call."""
    stack = inspect.stack()
    call_stack = []

    for frame_info in stack:
        function_name = frame_info.function
        filename = frame_info.filename
        lineno = frame_info.lineno
        folder_name = os.path.dirname(filename)
        folder_base = os.path.basename(folder_name)
        script_name = os.path.basename(filename)

        call_stack.append({
            "function": function_name,
            "folder": folder_name,
            "folder_base": folder_base,
            "script": script_name,
            "line": lineno
        })
        
    return call_stack

def get_ffmpeg_path():
    """Returns the path of FFmpeg."""
    return os_summary.ffmpeg_path

def get_ffprobe_path():
    """Returns the path of FFprobe."""
    return os_summary.ffprobe_path
