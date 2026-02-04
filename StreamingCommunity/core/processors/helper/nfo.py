# 02.02.26

import json
import subprocess
import logging
from pathlib import Path


# Internal utilities
from StreamingCommunity.setup import get_ffprobe_path


def run_ffprobe(file_path):
    """Run ffprobe on the given file and return the JSON output."""
    cmd = [
        get_ffprobe_path(),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        logging.error(f"Error running ffprobe for NFO: {e}")
        return None


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS."""
    try:
        seconds = float(seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}:{m:02}:{s:02}"
    except (ValueError, TypeError):
        return "00:00:00"


def get_language(stream):
    """Extract language from stream tags."""
    tags = stream.get("tags", {})
    return tags.get("language") or tags.get("title") or "und"


def parse_fps(rate):
    """Parse frame rate string (e.g., '24/1') to a simple string."""
    if rate and "/" in rate:
        try:
            num, den = rate.split("/")
            if int(den) > 0:
                return f"{int(num) // int(den)}"
        except (ValueError, ZeroDivisionError):
            pass
    return rate or "N/A"


def create_nfo(file_path: str):
    """
    Generate a .nfo file for the given media file.
    
    Parameters:
        - file_path (str): The path to the media file.
    """
    if not file_path or not Path(file_path).exists():
        return

    data = run_ffprobe(file_path)
    if not data:
        return

    file_path_obj = Path(file_path)
    nfo_path = file_path_obj.with_suffix(".nfo")

    try:
        format_info = data.get("format", {})
        streams = data.get("streams", [])

        container = format_info.get("format_name", "unknown")
        duration = format_duration(format_info.get("duration", 0))
        bitrate = int(format_info.get("bit_rate", 0)) // 1000 if format_info.get("bit_rate") else 0

        lines = []
        lines.append(f"File: {file_path_obj.name}")
        lines.append(f"Container: {container}")
        lines.append(f"Duration: {duration}")
        lines.append(f"Bitrate: {bitrate} kb/s\n")

        # VIDEO
        for s in streams:
            if s.get("codec_type") == "video":
                lines.append("VIDEO")
                lines.append(f"  Codec: {s.get('codec_name', 'UNKNOWN').upper()} ({s.get('profile', '')})")
                lines.append(f"  Resolution: {s.get('width', '?')}x{s.get('height', '?')}")
                lines.append(f"  FPS: {parse_fps(s.get('r_frame_rate'))}")
                lines.append(f"  Scan: {s.get('field_order', 'progressive')}\n")
                break

        # AUDIO
        lines.append("AUDIO")
        for s in streams:
            if s.get("codec_type") == "audio":
                lines.append(f"  Language: {get_language(s)}")
                lines.append(f"  Codec: {s.get('codec_name', 'UNKNOWN').upper()} ({s.get('profile', '')})")
                lines.append(f"  Channels: {s.get('channels', '?')}")
                lines.append(f"  Sample Rate: {s.get('sample_rate', '?')} Hz\n")

        # SUBTITLES
        subs = [s for s in streams if s.get("codec_type") == "subtitle"]
        if subs:
            lines.append("SUBTITLES")
            for s in subs:
                lines.append(f"  Language: {get_language(s)}")
                lines.append(f"  Codec: {s.get('codec_name', 'UNKNOWN')}")

        nfo_path.write_text("\n".join(lines), encoding="utf-8")

    except Exception as e:
        logging.error(f"Error creating NFO for {file_path}: {e}")