# 18.07.25

import os
import struct
from typing import Optional


# External library
import httpx
from rich.console import Console


# Internal utilities
from .binary_paths import binary_paths


# Variable
console = Console()


class DeviceSearcher:
    def __init__(self):
        self.base_dir = binary_paths.ensure_binary_directory()

    def _check_existing(self, ext: str) -> Optional[str]:
        """Check for existing files with given extension in binary directory."""
        try:
            for file in os.listdir(self.base_dir):
                if file.lower().endswith(ext):
                    path = os.path.join(self.base_dir, file)
                    return path
                
            return None
        
        except Exception as e:
            console.print(f"[red]Error checking existing {ext} files: {e}")
            return None

    def _find_recursively(self, ext: str = None, start_dir: str = ".", filename: str = None) -> Optional[str]:
        """
        Find file recursively by extension or exact filename starting from start_dir.
        If filename is provided, search for that filename. Otherwise, search by extension.
        """
        try:
            for root, dirs, files in os.walk(start_dir):
                for file in files:
                    if filename:
                        if file == filename:
                            path = os.path.join(root, file)
                            return path
                        
                    elif ext:
                        if file.lower().endswith(ext):
                            path = os.path.join(root, file)
                            return path
                        
            return None
        except Exception as e:
            console.print(f"[red]Error during recursive search for filename {filename}: {e}")
            return None

    def search(self, ext: str = None, filename: str = None) -> Optional[str]:
        """
        Search for file with given extension or exact filename in binary directory or recursively.
        If filename is provided, search for that filename. Otherwise, search by extension.
        """
        if filename:
            try:
                target_path = os.path.join(self.base_dir, filename)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                    return target_path
                
            except Exception as e:
                console.print(f"[red]Error checking for existing file {filename}: {e}")
                return None

            return self._find_recursively(filename=filename)
        
        else:
            path = self._check_existing(ext)
            if path:
                return path
            return self._find_recursively(ext=ext)


class DeviceDownloader:
    def __init__(self):
        self.base_dir = binary_paths.ensure_binary_directory()
        self.github_png_url = "https://github.com/Arrowar/StreamingCommunity/raw/main/.github/doc/img/crunchyroll_etp_rt.png"

    def extract_png_chunk(self, png_with_wvd: str, out_wvd_path: str) -> bool:
        """Extract WVD data"""
        with open(png_with_wvd, "rb") as f: 
            data = f.read()
        pos = 8
        
        while pos < len(data):
            length = struct.unpack(">I", data[pos:pos+4])[0]
            chunk_type = data[pos+4:pos+8]
            chunk_data = data[pos+8:pos+8+length]

            if chunk_type == b"stEg":
                with open(out_wvd_path, "wb") as f: 
                    f.write(chunk_data)
                return True
            
            pos += 12 + length
        
        return False
        
    def _download_png_from_github(self, output_path: str) -> bool:
        """Download PNG file from GitHub repository."""
        try: 
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(self.github_png_url)
                response.raise_for_status()
                
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                return True
                
        except Exception as e:
            console.print(f"[red]Error downloading PNG from GitHub: {e}")
            return False

    def download(self) -> Optional[str]:
        """
        Main method to extract WVD file from PNG.
        Downloads PNG from GitHub if not found locally.
        """
        try:
            searcher = DeviceSearcher()
            target_filename = "crunchyroll_etp_rt.png"
            png_path = searcher.search(filename=target_filename)
            temp_png_path = None

            if not png_path:
                temp_png_path = os.path.join(self.base_dir, target_filename)
                if not self._download_png_from_github(temp_png_path):
                    return None
                
                png_path = temp_png_path

            device_wvd_path = os.path.join(self.base_dir, 'device.wvd')
            extraction_success = self.extract_png_chunk(png_path, device_wvd_path)

            if temp_png_path and os.path.exists(temp_png_path):
                os.remove(temp_png_path)

            if extraction_success:
                if os.path.exists(device_wvd_path) and os.path.getsize(device_wvd_path) > 0:
                    return device_wvd_path

        except Exception:
            return None


def check_device_wvd_path() -> Optional[str]:
    """Check for device.wvd file in binary directory and extract from PNG if not found."""
    try:
        searcher = DeviceSearcher()
        existing_wvd = searcher.search('.wvd')
        if existing_wvd:
            return existing_wvd

        downloader = DeviceDownloader()
        return downloader.download()

    except Exception:
        return None

def check_device_prd_path() -> Optional[str]:
    """Check for device.prd file in binary directory and search recursively if not found."""
    try:
        searcher = DeviceSearcher()
        return searcher.search('.prd')

    except Exception:
        return None