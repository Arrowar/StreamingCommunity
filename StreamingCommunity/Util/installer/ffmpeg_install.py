# 24.01.2024

import os
import glob
import gzip
import shutil
import logging
import subprocess
from typing import Optional, Tuple


# External library
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn


# Internal utilities
from .binary_paths import binary_paths


# Variable
console = Console()


FFMPEG_CONFIGURATION = {
    'windows': {
        'download_url': 'https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-win32-{arch}.gz',
        'file_extension': '.gz',
        'executables': ['ffmpeg-win32-{arch}', 'ffprobe-win32-{arch}']
    },
    'darwin': {
        'download_url': 'https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-darwin-{arch}.gz',
        'file_extension': '.gz',
        'executables': ['ffmpeg-darwin-{arch}', 'ffprobe-darwin-{arch}']
    },
    'linux': {
        'download_url': 'https://github.com/eugeneware/ffmpeg-static/releases/latest/download/ffmpeg-linux-{arch}.gz',
        'file_extension': '.gz',
        'executables': ['ffmpeg-linux-{arch}', 'ffprobe-linux-{arch}']
    }
}


class FFMPEGDownloader:
    def __init__(self):
        self.os_name = binary_paths.system
        self.arch = binary_paths.arch
        self.home_dir = binary_paths.home_dir
        self.base_dir = binary_paths.ensure_binary_directory()

    def _check_existing_binaries(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Check if FFmpeg binaries already exist in the base directory.
        Enhanced to check both the binary directory and system paths on macOS.
        """
        config = FFMPEG_CONFIGURATION[self.os_name]
        executables = config['executables']
        found_executables = []

        # For macOS, check both binary directory and system paths
        if self.os_name == 'darwin':
            potential_paths = [
                '/usr/local/bin',
                '/opt/homebrew/bin',
                '/usr/bin',
                self.base_dir
            ]
            
            for executable in executables:
                found = None
                for path in potential_paths:
                    full_path = os.path.join(path, executable)
                    if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                        found = full_path
                        break
                found_executables.append(found)
        else:

            # Original behavior for other operating systems
            for executable in executables:
                exe_paths = glob.glob(os.path.join(self.base_dir, executable))
                found_executables.append(exe_paths[0] if exe_paths else None)

        return tuple(found_executables) if len(found_executables) == 3 else (None, None, None)

    def _get_latest_version(self, repo: str) -> Optional[str]:
        """
        Get the latest FFmpeg version from the GitHub releases page.

        Returns:
            Optional[str]: The latest version string, or None if retrieval fails.
        """
        try:
            # Use GitHub API to fetch the latest release
            response = requests.get(f'https://api.github.com/repos/{repo}/releases/latest')
            response.raise_for_status()
            latest_release = response.json()

            # Extract the tag name or version from the release
            return latest_release.get('tag_name')
        
        except Exception as e:
            logging.error(f"Unable to get version from GitHub: {e}")
            return None

    def _download_file(self, url: str, destination: str) -> bool:
        """
        Download a file from URL with a Rich progress bar display.

        Parameters:
            url (str): The URL to download the file from. Should be a direct download link.
            destination (str): Local file path where the downloaded file will be saved.

        Returns:
            bool: True if download was successful, False otherwise.
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(destination, 'wb') as file, \
                Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn()
                ) as progress:
                
                download_task = progress.add_task("[green]Downloading FFmpeg", total=total_size)
                for chunk in response.iter_content(chunk_size=8192):
                    size = file.write(chunk)
                    progress.update(download_task, advance=size)
            return True
        
        except Exception as e:
            logging.error(f"Download error: {e}")
            return False

    def _extract_file(self, gz_path: str, final_path: str) -> bool:
        """
        Extract a gzipped file and set proper permissions.

        Parameters:
            gz_path (str): Path to the gzipped file
            final_path (str): Path where the extracted file should be saved

        Returns:
            bool: True if extraction was successful, False otherwise
        """
        try:
            logging.info(f"Attempting to extract {gz_path} to {final_path}")
            
            # Check if source file exists and is readable
            if not os.path.exists(gz_path):
                logging.error(f"Source file {gz_path} does not exist")
                return False
                
            if not os.access(gz_path, os.R_OK):
                logging.error(f"Source file {gz_path} is not readable")
                return False

            # Extract the file
            with gzip.open(gz_path, 'rb') as f_in:
                # Test if the gzip file is valid
                try:
                    f_in.read(1)
                    f_in.seek(0)
                except Exception as e:
                    logging.error(f"Invalid gzip file {gz_path}: {e}")
                    return False

                # Extract the file
                with open(final_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Set executable permissions
            os.chmod(final_path, 0o755)
            logging.info(f"Successfully extracted {gz_path} to {final_path}")
            
            # Remove the gzip file
            os.remove(gz_path)
            return True

        except Exception as e:
            logging.error(f"Extraction error for {gz_path}: {e}")
            return False

    def download(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Main method to download and set up FFmpeg executables.

        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]: Paths to ffmpeg, ffprobe, and ffplay executables.
        """
        if self.os_name == 'linux':
            try:
                # Attempt to install FFmpeg using apt
                console.print("[bold blue]Trying to install FFmpeg using 'sudo apt install ffmpeg'[/]")
                result = subprocess.run(
                    ['sudo', 'apt', 'install', '-y', 'ffmpeg'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0:
                    ffmpeg_path = shutil.which('ffmpeg')
                    ffprobe_path = shutil.which('ffprobe')

                    if ffmpeg_path and ffprobe_path:
                        console.print("[bold green]FFmpeg successfully installed via apt[/]")
                        return ffmpeg_path, ffprobe_path, None
                else:
                    console.print("[bold yellow]Failed to install FFmpeg via apt. Proceeding with static download.[/]")
                    
            except Exception as e:
                logging.error(f"Error during 'sudo apt install ffmpeg': {e}")
                console.print("[bold red]Error during 'sudo apt install ffmpeg'. Proceeding with static download.[/]")

        # Proceed with static download if apt installation fails or is not applicable
        config = FFMPEG_CONFIGURATION[self.os_name]
        executables = [exe.format(arch=self.arch) for exe in config['executables']]
        successful_extractions = []

        for executable in executables:
            try:
                download_url = f"https://github.com/eugeneware/ffmpeg-static/releases/latest/download/{executable}.gz"
                download_path = os.path.join(self.base_dir, f"{executable}.gz")
                final_path = os.path.join(self.base_dir, executable)
                
                # Log the current operation
                logging.info(f"Processing {executable}")
                console.print(f"[bold blue]Downloading {executable} from GitHub[/]")
                
                # Download the file
                if not self._download_file(download_url, download_path):
                    console.print(f"[bold red]Failed to download {executable}[/]")
                    continue

                # Extract the file
                if self._extract_file(download_path, final_path):
                    successful_extractions.append(final_path)
                    console.print(f"[bold green]Successfully installed {executable}[/]")
                else:
                    console.print(f"[bold red]Failed to extract {executable}[/]")

            except Exception as e:
                logging.error(f"Error processing {executable}: {e}")
                console.print(f"[bold red]Error processing {executable}: {str(e)}[/]")
                continue

        # Return the results based on successful extractions
        return (
            successful_extractions[0] if len(successful_extractions) > 0 else None,
            successful_extractions[1] if len(successful_extractions) > 1 else None,
            None  # ffplay is not included in the current implementation
        )

def check_ffmpeg() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Check for FFmpeg executables in the system and download them if not found.
    Enhanced detection for macOS systems.

    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: Paths to ffmpeg, ffprobe, and ffplay executables.
    """
    try:
        system_platform = binary_paths.system
        
        # Special handling for macOS
        if system_platform == 'darwin':

            # Common installation paths on macOS
            potential_paths = [
                '/usr/local/bin',                               # Homebrew default
                '/opt/homebrew/bin',                            # Apple Silicon Homebrew
                '/usr/bin',                                     # System default
                binary_paths.get_binary_directory(),            # Custom installation
                '/Applications/binary'                          # Custom installation
            ]
            
            for path in potential_paths:
                ffmpeg_path = os.path.join(path, 'ffmpeg')
                ffprobe_path = os.path.join(path, 'ffprobe')
                ffplay_path = os.path.join(path, 'ffplay')
                
                if (os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path) and 
                    os.access(ffmpeg_path, os.X_OK) and os.access(ffprobe_path, os.X_OK)):
                    
                    # Return found executables, with ffplay being optional
                    ffplay_path = ffplay_path if os.path.exists(ffplay_path) else None
                    return ffmpeg_path, ffprobe_path, ffplay_path

        # Windows detection
        elif system_platform == 'windows':
            try:
                ffmpeg_path = subprocess.check_output(
                    ['where', 'ffmpeg'], stderr=subprocess.DEVNULL, text=True
                ).strip().split('\n')[0]
                
                ffprobe_path = subprocess.check_output(
                    ['where', 'ffprobe'], stderr=subprocess.DEVNULL, text=True
                ).strip().split('\n')[0]
                
                ffplay_path = subprocess.check_output(
                    ['where', 'ffplay'], stderr=subprocess.DEVNULL, text=True
                ).strip().split('\n')[0]

                return ffmpeg_path, ffprobe_path, ffplay_path
            
            except subprocess.CalledProcessError:
                logging.warning("One or more FFmpeg binaries were not found with command where")

        # Linux detection
        else:
            ffmpeg_path = shutil.which('ffmpeg')
            ffprobe_path = shutil.which('ffprobe')
            ffplay_path = shutil.which('ffplay')
            
            if ffmpeg_path and ffprobe_path:
                return ffmpeg_path, ffprobe_path, ffplay_path

        # If executables were not found, attempt to download FFmpeg
        downloader = FFMPEGDownloader()
        return downloader.download()

    except Exception as e:
        logging.error(f"Error checking or downloading FFmpeg executables: {e}")
        return None, None, None