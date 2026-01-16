# 17.01.25

import json
import os
import subprocess
import logging


# Internal utilities
from StreamingCommunity.setup import get_ffprobe_path


# External library
from rich.console import Console


# Variable
console = Console()


def get_ffprobe_info(file_path):
    """
    Get format and codec information for a media file using ffprobe.

    Parameters:
        - file_path (str): Path to the media file.
    
    Returns:
        dict: A dictionary containing the format name and a list of codec names.
              Returns None if file does not exist or ffprobe crashes.
    """
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return None

    try:
        cmd = [get_ffprobe_path(), '-v', 'error', '-show_format', '-show_streams', '-print_format', 'json', file_path]
        
        # Use subprocess.run instead of Popen for better error handling
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            logging.error(f"FFprobe failed with return code {result.returncode}")
            logging.error(f"FFprobe stderr: {result.stderr}")
            logging.error(f"FFprobe stdout: {result.stdout}")
            logging.error(f"Command: {' '.join(cmd)}")
            return None

        # Parse JSON output
        info = json.loads(result.stdout)
        return {
            'format_name': info.get('format', {}).get('format_name'),
            'codec_names': [stream.get('codec_name') for stream in info.get('streams', [])]
        }
    
    except Exception as e:
        logging.error(f"FFprobe execution failed: {e}")
        return None


def is_png_format_or_codec(file_info):
    """
    Check if the format is 'png_pipe' or if any codec is 'png'.

    Parameters:
        - file_info (dict): The dictionary containing file information.

    Returns:
        bool: True if the format is 'png_pipe' or any codec is 'png', otherwise False.
    """
    if not file_info:
        return False
    
    # Handle None values in format_name gracefully
    format_name = file_info.get('format_name')
    codec_names = file_info.get('codec_names', [])
    console.print(f"[yellow]FFMPEG [cyan]Format [green]{format_name} [cyan]codec[white]: [green]{codec_names}")
    return format_name == 'png_pipe' or 'png' in codec_names


def need_to_force_to_ts(file_path):
    """
    Get if a file to TS format if it is in PNG format or contains a PNG codec.

    Parameters:
        - file_path (str): Path to the input media file.
    """
    if is_png_format_or_codec(get_ffprobe_info(file_path)):
       return True
    
    return False