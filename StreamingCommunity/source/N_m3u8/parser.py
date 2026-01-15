# 04.01.25

import os
import json
from typing import List, Tuple


# External 
from rich.console import Console


# Logic
from .object import StreamInfo 


# Variable
console = Console()


class LogParser:
    def __init__(self):
        self.warnings = []
        self.errors = []
    
    def parse_line(self, line: str) -> Tuple[bool, bool]:
        """Parse a log line, return (has_warning, has_error)"""
        line = line.strip()
        has_warning = False
        has_error = False
        
        if 'WARN' in line.upper():
            self.warnings.append(line)
            has_warning = True
            #console.print(f"[yellow]{line}[/yellow]")
            
        if 'ERROR' in line.upper():
            self.errors.append(line)
            has_error = True
            console.print(f"[red]{line}.")
            
        return has_warning, has_error


def create_video_key(stream):
    return f"VIDEO|{stream.get('Resolution', '')}|{stream.get('Bandwidth', 0)}|{stream.get('Codecs', '')}"

def create_audio_key(stream):
    return f"AUDIO|{stream.get('Language', '')}|{stream.get('Name', '')}|{stream.get('Bandwidth', 0)}|{stream.get('Codecs', '')}"

def create_subtitle_key(stream):
    return f"SUBTITLE|{stream.get('Language', '')}|{stream.get('Name', '')}"

def parse_meta_json(json_path: str, selected_json_path: str) -> List[StreamInfo]:
    """Parse meta.json and meta_selected.json to determine which streams are selected"""
    streams = []
    
    # 1) meta.json
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        metadata = json.load(f)

    # 2) meta_selected.json
    selected_streams = []
    if selected_json_path and os.path.isfile(selected_json_path):
        with open(selected_json_path, 'r', encoding='utf-8-sig') as f:
            selected_streams = json.load(f)
    
    # Create a map of selected streams for easy lookup
    selected_map = {}
    
    for sel_stream in selected_streams:
        total_duration = sel_stream.get("Playlist", {}).get("TotalDuration", 0)
        segment_count = sel_stream.get("SegmentsCount", 0)
        
        # Check if encrypted
        encrypted = False
        if "Playlist" in sel_stream and "MediaParts" in sel_stream["Playlist"]:
            for part in sel_stream["Playlist"]["MediaParts"]:
                for seg in part.get("MediaSegments", []):
                    if seg.get("EncryptInfo", {}).get("Method") not in ["NONE", None]:
                        encrypted = True
                        break
                if encrypted:
                    break

        # 1) Video
        if "Resolution" in sel_stream and sel_stream.get("Resolution"):
            key = create_video_key(sel_stream)
            selected_map[key] = {
                'encrypted': encrypted,
                'extension': sel_stream.get("Extension", ""),
                'total_duration': total_duration,
                'segment_count': segment_count
            }
        
        # 2) Audio
        elif sel_stream.get("MediaType") == "AUDIO":
            key = create_audio_key(sel_stream)
            selected_map[key] = {
                'encrypted': encrypted,
                'extension': sel_stream.get("Extension", ""),
                'total_duration': total_duration,
                'segment_count': segment_count
            }
        
        # 3) Subtitles
        elif sel_stream.get("MediaType") == "SUBTITLES":
            key = create_subtitle_key(sel_stream)
            selected_map[key] = {
                'encrypted': False,  # Subtitles are usually not encrypted
                'extension': sel_stream.get("Extension", ""),
                'total_duration': total_duration,
                'segment_count': segment_count
            }
    
    for stream in metadata:
        bandwidth = stream.get('Bandwidth', 0)
        
        # Format bandwidth
        if bandwidth >= 1000000:
            bandwidth_str = f"{bandwidth/1000000:.1f} Mbps"
        elif bandwidth >= 1000:
            bandwidth_str = f"{bandwidth/1000:.0f} Kbps"
        else:
            bandwidth_str = f"{bandwidth:.0f} bps"
        
        # Get duration and segment count - check BOTH sources
        total_duration = stream.get("Playlist", {}).get("TotalDuration", 0)
        segment_count = stream.get("SegmentsCount", 0)
        
        # 1) Video
        if "Resolution" in stream and stream.get("Resolution"):
            key = create_video_key(stream)
            is_selected = key in selected_map
            details = selected_map.get(key, {})
            
            # If stream is selected OR if we have data in meta.json (DASH case)
            if is_selected and details:
                final_total_duration = details.get('total_duration', total_duration)
                final_segment_count = details.get('segment_count', segment_count)
            else:
                final_total_duration = total_duration
                final_segment_count = segment_count
            
            streams.append(StreamInfo(
                type_="Video",
                resolution=stream["Resolution"],
                bandwidth=bandwidth_str,
                codec=stream.get("Codecs", ""),
                selected=is_selected,
                encrypted=details.get('encrypted', False),
                extension=details.get('extension', ''),
                total_duration=final_total_duration,
                segment_count=final_segment_count
            ))
        
        # 2) Audio
        elif stream.get("MediaType") == "AUDIO":
            key = create_audio_key(stream)
            is_selected = key in selected_map
            details = selected_map.get(key, {})
            
            # If stream is selected OR if we have data in meta.json (DASH case)
            if is_selected and details:
                final_total_duration = details.get('total_duration', total_duration)
                final_segment_count = details.get('segment_count', segment_count)
            else:
                final_total_duration = total_duration
                final_segment_count = segment_count
            
            streams.append(StreamInfo(
                type_="Audio",
                language=stream.get("Language", ""),
                name=stream.get("Name", ""),
                codec=stream.get("Codecs", ""),
                bandwidth=bandwidth_str,
                selected=is_selected,
                encrypted=details.get('encrypted', False),
                extension=details.get('extension', ''),
                total_duration=final_total_duration,
                segment_count=final_segment_count
            ))
        
        # 3) Subtitles
        elif stream.get("MediaType") == "SUBTITLES":
            key = create_subtitle_key(stream)
            is_selected = key in selected_map
            details = selected_map.get(key, {})
            
            # If stream is selected OR if we have data in meta.json (DASH case)
            if is_selected and details:
                final_total_duration = details.get('total_duration', total_duration)
                final_segment_count = details.get('segment_count', segment_count)
            else:
                final_total_duration = total_duration
                final_segment_count = segment_count
            
            streams.append(StreamInfo(
                type_="Subtitle",
                language=stream.get("Language", ""),
                name=stream.get("Name", ""),
                bandwidth="N/A",
                selected=is_selected,
                encrypted=details.get('encrypted', False),
                extension=details.get('extension', ''),
                total_duration=final_total_duration,
                segment_count=final_segment_count
            ))

        else:
            # Fallback: some meta.json entries (e.g. simple HLS playlists) don't include MediaType, treat as Video
            final_total_duration = total_duration
            final_segment_count = segment_count
            streams.append(StreamInfo(
                type_="Video",
                resolution="",
                bandwidth=bandwidth_str,
                codec=stream.get("Codecs", ""),
                selected=False,
                encrypted=False,
                extension=stream.get("Extension", ""),
                total_duration=final_total_duration,
                segment_count=final_segment_count
            ))
    
    return streams