# 17.01.25

import json
import subprocess


# Internal utilities
from StreamingCommunity.setup import get_ffprobe_path, get_ffmpeg_path


# External library
from rich.console import Console


# Variable
console = Console()


def detect_ts_timestamp_issues(file_path):
    """
    Detect if a TS file has timestamp issues by checking for unset timestamps.

    Parameters:
        - file_path (str): Path to the TS file.

    Returns:
        bool: True if timestamp issues are detected, False otherwise.
    """
    cmd = [get_ffprobe_path(), '-v', 'error', '-show_packets', '-select_streams', 'v:0', '-read_intervals', '0%+#1', '-print_format', 'json', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode != 0 or 'pts_time' not in result.stdout:
        return True  # Assume issues if probe fails or no pts_time
    
    # Parse JSON and check for packets without pts
    try:
        info = json.loads(result.stdout)
        packets = info.get('packets', [])
        for packet in packets:
            if packet.get('pts') is None or packet.get('pts') == 'N/A':
                return True
    except json.JSONDecodeError:
        return True
    
    return False


def convert_ts_to_mp4(input_path, output_path):
    """
    Convert a TS file to MP4 to regenerate timestamps.

    Parameters:
        - input_path (str): Path to the input TS file.
        - output_path (str): Path to the output MP4 file.

    Returns:
        bool: True if conversion succeeded, False otherwise.
    """
    cmd = [
        get_ffmpeg_path(),
        '-fflags', '+genpts+igndts+discardcorrupt',
        '-avoid_negative_ts', 'make_zero',
        '-i', input_path,
        '-c', 'copy',
        '-y', output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode == 0