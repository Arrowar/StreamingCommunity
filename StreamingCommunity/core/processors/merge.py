# 31.01.24

import os
import subprocess
from typing import List, Dict


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager
from StreamingCommunity.setup import binary_paths, get_ffmpeg_path


# Logic class
from .helper.ex_video import need_to_force_to_ts
from .helper.ex_audio import check_duration_v_a
from .helper.ex_sub import fix_subtitle_extension
from .capture import capture_ffmpeg_real_time


# Config
console = Console()
os_type = binary_paths._detect_system()
USE_GPU = config_manager.config.get_bool("M3U8_CONVERSION", "use_gpu")
PARAM_VIDEO = config_manager.config.get_list("M3U8_CONVERSION", "param_video")
PARAM_AUDIO = config_manager.config.get_list("M3U8_CONVERSION", "param_audio")
PARAM_FINAL = config_manager.config.get_list("M3U8_CONVERSION", "param_final")
SUBTITLE_DISPOSITION = config_manager.config.get_bool("M3U8_CONVERSION", "subtitle_disposition")
SUBTITLE_DISPOSITION_LANGUAGE = config_manager.config.get_list("M3U8_CONVERSION", "subtitle_disposition_language")


def add_encoding_params(ffmpeg_cmd: List[str]):
    """
    Add encoding parameters to the ffmpeg command.
    
    Parameters:
        ffmpeg_cmd (List[str]): List of the FFmpeg command to modify
    """
    if PARAM_FINAL:
        ffmpeg_cmd.extend(PARAM_FINAL)
    else:
        ffmpeg_cmd.extend(PARAM_VIDEO)
        ffmpeg_cmd.extend(PARAM_AUDIO)


def detect_gpu_device_type() -> str:
    """
    Detects the GPU device type available on the system.
    
    Returns:
        str: The type of GPU device detected ('cuda', 'vaapi', 'qsv', or 'none').
    """
    try:
        if os_type == 'linux':
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            output = result.stdout.lower()
        elif os_type == 'windows':
            try:
                result = subprocess.run(['wmic', 'path', 'win32_videocontroller', 'get', 'name'], capture_output=True, text=True, check=True)
                output = result.stdout.lower()

            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to PowerShell if wmic is not available
                try:
                    result = subprocess.run(['powershell', '-Command', 'Get-WmiObject win32_videocontroller | Select-Object -ExpandProperty Name'], capture_output=True, text=True, check=True)
                    output = result.stdout.lower()
                except (subprocess.CalledProcessError, FileNotFoundError):
                    return 'none'
                
        elif os_type == 'darwin':  # macOS
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True, check=True)
            output = result.stdout.lower()

        else:
            return 'none'
        
        if 'nvidia' in output:
            return 'cuda'
        elif 'intel' in output:
            return 'vaapi'
        elif 'amd' in output or 'ati' in output:
            return 'vaapi'
        else:
            return 'none'
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 'none'


def join_video(video_path: str, out_path: str):
    """
    Mux video file using FFmpeg.
    
    Parameters:
        - video_path (str): The path to the video file.
        - out_path (str): The path to save the output file.
    """
    ffmpeg_cmd = [get_ffmpeg_path()]

    # Enabled the use of gpu
    if USE_GPU:
        gpu_type_hwaccel = detect_gpu_device_type()
        console.print(f"[yellow]FFMPEG [cyan]Detected GPU for video join: [red]{gpu_type_hwaccel}")
        ffmpeg_cmd.extend(['-hwaccel', gpu_type_hwaccel])

    # Add mpegts to force to detect input file as ts file
    if need_to_force_to_ts(video_path):
        ffmpeg_cmd.extend(['-f', 'mpegts'])

    # Insert input video path
    ffmpeg_cmd.extend(['-i', video_path])

    # Add encoding parameters (prima dell'output)
    add_encoding_params(ffmpeg_cmd)

    # Output file and overwrite
    ffmpeg_cmd.extend([out_path, '-y'])

    # Run join
    result_json = capture_ffmpeg_real_time(ffmpeg_cmd, "[yellow]FFMPEG [cyan]Join video")
    print()

    return out_path, result_json


def join_audios(video_path: str, audio_tracks: List[Dict[str, str]], out_path: str, limit_duration_diff: float = 3):
    """
    Joins audio tracks with a video file using FFmpeg.
    
    Parameters:
        - video_path (str): The path to the video file.
        - audio_tracks (list[dict[str, str]]): A list of dictionaries containing information about audio tracks.
            Each dictionary should contain the 'path' and 'name' keys.
        - out_path (str): The path to save the output file.
        - limit_duration_diff (float): Maximum duration difference in seconds.
    """
    use_shortest = False
    
    for audio_track in audio_tracks:
        audio_path = audio_track.get('path')
        audio_lang = audio_track.get('name', 'unknown')
        _, diff, video_duration, audio_duration = check_duration_v_a(video_path, audio_path)
        console.print(f"[yellow]    - [cyan]Audio lang [red]{audio_lang}, [cyan]Path: [red]{audio_path}, [cyan]Video duration: [red]{video_duration:.2f}s, [cyan]Audio duration: [red]{audio_duration:.2f}s, [cyan]Diff: [red]{diff:.2f}s")
        
        # If any audio track has a significant duration difference, use -shortest
        if diff > limit_duration_diff:
            console.print(f"[yellow]    WARN [cyan]Audio lang: [red]'{audio_lang}' [cyan]has a duration difference of [red]{diff:.2f}s [cyan]which exceeds the limit of [red]{limit_duration_diff}s.")
            use_shortest = True

    # Start command with locate ffmpeg
    ffmpeg_cmd = [get_ffmpeg_path()]

    # Enabled the use of gpu
    if USE_GPU:
        ffmpeg_cmd.extend(['-hwaccel', detect_gpu_device_type()])

    # Insert input video path
    ffmpeg_cmd.extend(['-i', video_path])

    # Add audio tracks as input
    for i, audio_track in enumerate(audio_tracks):
        ffmpeg_cmd.extend(['-i', audio_track.get('path')])

    # Map the video and audio streams
    ffmpeg_cmd.extend(['-map', '0:v'])
    
    for i in range(1, len(audio_tracks) + 1):
        ffmpeg_cmd.extend(['-map', f'{i}:a'])

    # Add language metadata for each audio track
    for i, audio_track in enumerate(audio_tracks):
        lang_code = audio_track.get('name', 'unknown')
        
        # Extract language code (e.g., "ita" from "ita - Italian")
        ffmpeg_cmd.extend([f'-metadata:s:a:{i}', f'language={lang_code}'])
        ffmpeg_cmd.extend([f'-metadata:s:a:{i}', f'title={audio_track.get("name", "unknown")}'])

    # Add encoding parameters (prima di -shortest e output)
    add_encoding_params(ffmpeg_cmd)

    # Use shortest input path if any audio track has significant difference
    if use_shortest:
        ffmpeg_cmd.extend(['-shortest', '-strict', 'experimental'])

    # Output file and overwrite
    ffmpeg_cmd.extend([out_path, '-y'])

    # Run join
    result_json = capture_ffmpeg_real_time(ffmpeg_cmd, "[yellow]FFMPEG [cyan]Join audio")
    print()

    return out_path, use_shortest, result_json


def join_subtitles(video_path: str, subtitles_list: List[Dict[str, str]], out_path: str):
    """
    Joins subtitles with a video file using FFmpeg.

    Parameters:
        - video_path (str): The path to the video file.
        - subtitles_list (list[dict[str, str]]): A list of dictionaries containing information about subtitles.
            Each dictionary should contain the 'path' key with the path to the subtitle file and the 'name' key with the name of the subtitle.
        - out_path (str): The path to save the output file.
    """
    # First, detect and fix subtitle extensions
    for subtitle in subtitles_list:
        original_path = subtitle['path']
        corrected_path = fix_subtitle_extension(original_path)
        subtitle['path'] = corrected_path
    
    ffmpeg_cmd = [get_ffmpeg_path(), "-i", video_path]
    output_ext = os.path.splitext(out_path)[1].lower()
    
    # Determine subtitle codec based on output format
    if output_ext == '.mp4':
        subtitle_codec = 'mov_text'
    elif output_ext == '.mkv':
        subtitle_codec = 'copy'
    else:
        subtitle_codec = 'copy'
    
    # Add subtitle input files first
    for subtitle in subtitles_list:
        ffmpeg_cmd += ["-i", subtitle['path']]
    
    # Add maps for video and audio streams
    ffmpeg_cmd += ["-map", "0:v", "-map", "0:a"]
    
    # Add subtitle maps and metadata
    for idx, subtitle in enumerate(subtitles_list):
        lang_display = subtitle.get('lang', subtitle.get('language', 'unknown'))
        console.print(f"[yellow]    - [cyan]Subtitle lang [red]{lang_display}, [cyan]Path: [red]{subtitle.get('path', 'unknown')}")
        ffmpeg_cmd += ["-map", f"{idx + 1}:s"]
        ffmpeg_cmd += ["-metadata:s:s:{}".format(idx), "title={}".format(lang_display)]
    
    # For subtitles, we always use copy for video/audio
    ffmpeg_cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', subtitle_codec])
    
    # Handle disposition: set all subtitles to 0 (disabled) by default
    for idx in range(len(subtitles_list)):
        ffmpeg_cmd.extend([f'-disposition:s:{idx}', '0'])
    
    # Set disposition ONLY if SUBTITLE_DISPOSITION is enabled
    if SUBTITLE_DISPOSITION and len(subtitles_list) > 0:
        disposition_idx = None
        
        # Find subtitle matching the configured language
        for idx, subtitle in enumerate(subtitles_list):
            subtitle_lang = subtitle.get('language', '').lower()
            for lang in SUBTITLE_DISPOSITION_LANGUAGE:
                config_lang = lang.lower().strip()
                
                if subtitle_lang == config_lang or subtitle_lang.startswith(config_lang):
                    console.print(f"[yellow]    Setting disposition for subtitle: [red]{subtitle.get('language')}")
                    disposition_idx = idx
                    break
                    
            if disposition_idx is not None:
                break
            
        # If matching subtitle found, set it as default
        if disposition_idx is not None:
            ffmpeg_cmd.extend([f'-disposition:s:{disposition_idx}', 'default'])
    
    # Overwrite
    ffmpeg_cmd += [out_path, "-y"]
    
    # Run join
    result_json = capture_ffmpeg_real_time(ffmpeg_cmd, "[yellow]FFMPEG [cyan]Join subtitle")
    print()
    
    return out_path, result_json