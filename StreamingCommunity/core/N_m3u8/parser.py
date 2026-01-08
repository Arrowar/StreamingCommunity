# 10.01.26

import re
import json
from pathlib import Path
from typing import Optional


# Logic class
from .models import StreamInfo, Stream, DownloadProgress


class StreamParser:
    PROGRESS = re.compile(r"(Vid|Aud|Sub)\s+(.+?)\s+[-━\u2500\u2588\s]+\s+(\d+)/(\d+)\s+([\d.]+)%\s+(?:([\d.]+[KMGT]?B)/([\d.]+[KMGT]?B))?\s*(?:([\d.]+[KMGT]?Bps))?\s*([\d:]+)")
    _ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    
    @staticmethod
    def parse_stream_info_from_json(meta_file_path: Path, manifest_type_hint: str = None) -> StreamInfo:
        """Parse stream info directly from meta.json file instead of log parsing
        
        Args:
            meta_file_path: Path to meta.json file
            manifest_type_hint: Optional hint about manifest type ('HLS', 'DASH', or None for auto-detect)
        """
        # Ensure meta_file_path is a Path object
        if isinstance(meta_file_path, str):
            meta_file_path = Path(meta_file_path)
        
        if not meta_file_path.exists():
            return StreamInfo("UNKNOWN", [])
        
        try:
            with open(meta_file_path, 'r', encoding='utf-8-sig') as f:
                meta_data = json.load(f)
        except Exception as e:
            print(f"Error reading meta.json: {e}")
            return StreamInfo("UNKNOWN", [])
        
        streams = []
        manifest_type = manifest_type_hint if manifest_type_hint else "UNKNOWN"
        
        # Process each item in the meta.json array
        for item in meta_data:
            media_type = item.get("MediaType", "VIDEO").upper()
            
            # Only auto-detect if no hint was provided
            if not manifest_type_hint and manifest_type == "UNKNOWN":
                if "Codecs" in item and "Resolution" in item:
                    manifest_type = "DASH"
            
            # 1) Parse VIDEO streams
            if media_type == "VIDEO" or (media_type not in ["AUDIO", "SUBTITLES"] and "Resolution" in item):
                resolution = item.get("Resolution", "Unknown")
                bandwidth = item.get("Bandwidth", 0)
                codecs = item.get("Codecs", "unknown")
                segments_count = item.get("SegmentsCount", 0)
                
                # Convert bandwidth to Kbps
                bitrate = f"{bandwidth // 1000} Kbps" if bandwidth else "-"
                
                # Check if encrypted
                is_encrypted = False
                if "Playlist" in item and "MediaInit" in item["Playlist"]:
                    encrypt_info = item["Playlist"]["MediaInit"].get("EncryptInfo", {})
                    is_encrypted = encrypt_info.get("Method") is not None
                
                # Get duration
                duration = "-"
                if "Playlist" in item and "TotalDuration" in item["Playlist"]:
                    total_duration = item["Playlist"]["TotalDuration"]
                    
                    # Format duration as ~XXmXXs
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    duration = f"~{minutes}m{seconds}s"
                
                stream = Stream(
                    type="Video",
                    resolution=resolution,
                    bitrate=bitrate,
                    codec=codecs,
                    language="-",
                    lang_code="-",
                    language_long="-",
                    encrypted=is_encrypted,
                    duration=duration,
                    segments_count=segments_count
                )
                streams.append(stream)
            
            # 2) Parse AUDIO streams
            elif media_type == "AUDIO":
                language = item.get("Language", "unknown")
                name = item.get("Name", language)
                bandwidth = item.get("Bandwidth", 0)
                codecs = item.get("Codecs", "unknown")
                segments_count = item.get("SegmentsCount", 0)
                
                # Convert bandwidth to Kbps
                bitrate = f"{bandwidth // 1000} Kbps" if bandwidth else "-"
                
                # Check if encrypted
                is_encrypted = False
                if "Playlist" in item and "MediaInit" in item["Playlist"]:
                    encrypt_info = item["Playlist"]["MediaInit"].get("EncryptInfo", {})
                    is_encrypted = encrypt_info.get("Method") is not None
                
                # Get duration
                duration = "-"
                if "Playlist" in item and "TotalDuration" in item["Playlist"]:
                    total_duration = item["Playlist"]["TotalDuration"]
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    duration = f"~{minutes}m{seconds}s"
                
                stream = Stream(
                    type="Audio",
                    resolution="-",
                    bitrate=bitrate,
                    codec=codecs,
                    language=language,
                    lang_code=language,
                    language_long=name,
                    encrypted=is_encrypted,
                    duration=duration,
                    segments_count=segments_count
                )
                streams.append(stream)
            
            # 3) Parse SUBTITLE streams
            elif media_type == "SUBTITLES":
                language = item.get("Language", "unknown")
                name = item.get("Name", language)
                segments_count = item.get("SegmentsCount", 0)
                
                # Check if encrypted
                is_encrypted = False
                if "Playlist" in item and "MediaInit" in item["Playlist"]:
                    encrypt_info = item["Playlist"]["MediaInit"].get("EncryptInfo", {})
                    is_encrypted = encrypt_info.get("Method") is not None
                
                # Get duration
                duration = "-"
                if "Playlist" in item and "TotalDuration" in item["Playlist"]:
                    total_duration = item["Playlist"]["TotalDuration"]
                    minutes = int(total_duration // 60)
                    seconds = int(total_duration % 60)
                    duration = f"~{minutes}m{seconds}s"
                
                stream = Stream(
                    type="Subtitle",
                    resolution="-",
                    bitrate="-",
                    codec="-",
                    language=language,
                    lang_code=language,
                    language_long=name,
                    encrypted=is_encrypted,
                    duration=duration,
                    segments_count=segments_count
                )
                streams.append(stream)
        return StreamInfo(manifest_type, streams)
    
    @staticmethod
    def parse_progress(line: str) -> Optional[DownloadProgress]:
        clean = StreamParser._ANSI_RE.sub('', line)
        if match := StreamParser.PROGRESS.search(clean):
            return DownloadProgress(
                stream_type=match.group(1),
                description=match.group(2).strip(),
                current=int(match.group(3)),
                total=int(match.group(4)),
                percent=float(match.group(5)),
                downloaded_size=match.group(6) or "-",
                total_size=match.group(7) or "-",
                speed=match.group(8) or "-",
                time=match.group(9)
            )
        return None
