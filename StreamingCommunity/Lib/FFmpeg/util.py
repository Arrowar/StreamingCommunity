# 16.04.24

import os
import sys
import json
import subprocess
import logging
from typing import Tuple


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.os import get_ffprobe_path


# Variable
console = Console()


def has_audio_stream(video_path: str) -> bool:
    """
    Check if the input video has an audio stream.

    Parameters:
        - video_path (str): Path to the input video file.

    Returns:
        has_audio (bool): True if the input video has an audio stream, False otherwise.
    """
    try:
        ffprobe_cmd = [get_ffprobe_path(), '-v', 'error', '-print_format', 'json', '-select_streams', 'a', '-show_streams', video_path]
        logging.info(f"FFmpeg command: {ffprobe_cmd}")

        with subprocess.Popen(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            stdout, stderr = proc.communicate()
            if stderr:
                logging.error(f"Error: {stderr}")
            else:
                probe_result = json.loads(stdout)
                return bool(probe_result.get('streams', []))
            
    except Exception as e:
        logging.error(f"Error: {e}")
        return False


def get_video_duration(file_path: str) -> float:
    """
    Get the duration of a video file.

    Parameters:
        - file_path (str): The path to the video file.

    Returns:
        (float): The duration of the video in seconds if successful, None if there's an error.
    """

    try:
        ffprobe_cmd = [get_ffprobe_path(), '-v', 'error', '-show_format', '-print_format', 'json', file_path]
        logging.info(f"FFmpeg command: {ffprobe_cmd}")

        # Use a with statement to ensure the subprocess is cleaned up properly
        with subprocess.Popen(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0:
                logging.error(f"Error: {stderr}")
                return None
            
            # Parse JSON output
            probe_result = json.loads(stdout)

            # Extract duration from the video information
            try:
                return float(probe_result['format']['duration'])
            
            except:
                return 1

    except Exception as e:
        logging.error(f"Get video duration error: {e}")
        sys.exit(0)


def format_duration(seconds: float) -> Tuple[int, int, int]:
    """
    Format duration in seconds into hours, minutes, and seconds.

    Parameters:
        - seconds (float): Duration in seconds.

    Returns:
        list[int, int, int]: List containing hours, minutes, and seconds.
    """

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return int(hours), int(minutes), int(seconds)


def print_duration_table(file_path: str, description: str = "Duration", return_string: bool = False):
    """
    Print the duration of a video file in hours, minutes, and seconds, or return it as a formatted string.

    Parameters:
        - file_path (str): The path to the video file.
        - description (str): Optional description to be included in the output. Defaults to "Duration". If not provided, the duration will not be printed.
        - return_string (bool): If True, returns the formatted duration string. If False, returns a dictionary with hours, minutes, and seconds.

    Returns:
        - str: The formatted duration string if return_string is True.
        - dict: A dictionary with keys 'h', 'm', 's' representing hours, minutes, and seconds if return_string is False.
    """
    video_duration = get_video_duration(file_path)

    if video_duration is not None:
        hours, minutes, seconds = format_duration(video_duration)
        formatted_duration = f"[yellow]{int(hours)}[red]h [yellow]{int(minutes)}[red]m [yellow]{int(seconds)}[red]s"
        duration_dict = {'h': hours, 'm': minutes, 's': seconds}

        if description:
            console.print(f"[cyan]{description} for [white]([green]{os.path.basename(file_path)}[white]): {formatted_duration}")
        else:
            if return_string:
                return formatted_duration
            else:
                return duration_dict


def get_ffprobe_info(file_path):
    """
    Get format and codec information for a media file using ffprobe.

    Parameters:
        - file_path (str): Path to the media file.

    Returns:
        dict: A dictionary containing the format name and a list of codec names.
    """
    try:
        result = subprocess.run(
            [get_ffprobe_path(), '-v', 'error', '-show_format', '-show_streams', '-print_format', 'json', file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        output = result.stdout
        info = json.loads(output)
        
        format_name = info['format']['format_name'] if 'format' in info else None
        codec_names = [stream['codec_name'] for stream in info['streams']] if 'streams' in info else []
        
        return {
            'format_name': format_name,
            'codec_names': codec_names
        }
    
    except subprocess.CalledProcessError as e:
        logging.error(f"ffprobe failed for file {file_path}: {e}")
        return None
    
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON output from ffprobe for file {file_path}: {e}")
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
    
    #console.print(f"[yellow][FFmpeg] [cyan]Avaiable codec[white]: [red]{file_info['codec_names']}")
    return file_info['format_name'] == 'png_pipe' or 'png' in file_info['codec_names']


def need_to_force_to_ts(file_path):
    """
    Get if a file to TS format if it is in PNG format or contains a PNG codec.

    Parameters:
        - file_path (str): Path to the input media file.
    """
    logging.info(f"Processing file: {file_path}")
    file_info = get_ffprobe_info(file_path)

    if is_png_format_or_codec(file_info):
       return True
    return False


def check_duration_v_a(video_path, audio_path):
    """
    Check if the duration of the video and audio matches.

    Parameters:
        - video_path (str): Path to the video file.
        - audio_path (str): Path to the audio file.

    Returns:
        - bool: True if the duration of the video and audio matches, False otherwise.
    """
    
    # Ottieni la durata del video
    video_duration = get_video_duration(video_path)
    
    # Ottieni la durata dell'audio
    audio_duration = get_video_duration(audio_path)

    # Verifica se le durate corrispondono
    return video_duration == audio_duration