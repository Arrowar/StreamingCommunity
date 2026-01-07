# 10.01.26

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import get_bento4_decrypt_path, get_n_m3u8dl_re_path


# Variable
THREAD_COUNT = config_manager.config.get_int("M3U8_DOWNLOAD", "thread_count")
RETRY_COUNT = config_manager.config.get_int("M3U8_DOWNLOAD", "retry_count")
SET_RESOLUTION = config_manager.config.get("M3U8_CONVERSION", "force_resolution")
CONCURRENT_DOWNLOAD = config_manager.config.get_bool("M3U8_DOWNLOAD", "concurrent_download")
MAX_SPEED = config_manager.config.get("M3U8_DOWNLOAD", "max_speed")


@dataclass
class Stream:
    type: str  # "Video", "Audio", "Subtitle"
    resolution: str
    bitrate: str
    codec: str
    language: str
    lang_code: str
    language_long: str = ""
    encrypted: bool = False
    duration: str = "-"
    segments_count: int = 0


@dataclass
class StreamInfo:
    manifest_type: str  # "HLS", "DASH", "UNKNOWN"
    streams: List[Stream]
    
    @property
    def video_streams(self) -> List[Stream]:
        return [s for s in self.streams if s.type == "Video"]
    
    @property
    def audio_streams(self) -> List[Stream]:
        return [s for s in self.streams if s.type == "Audio"]
    
    @property
    def subtitle_streams(self) -> List[Stream]:
        return [s for s in self.streams if s.type == "Subtitle"]


@dataclass
class DownloadProgress:
    stream_type: str  # "Vid", "Aud", "Sub"
    description: str
    current: int
    total: int
    percent: float
    downloaded_size: str
    total_size: str
    speed: str
    time: str


@dataclass
class MediaTrack:
    path: str
    language: str
    format: str = ""


@dataclass
class DownloadResult:
    video_path: Optional[str] = None
    audio_tracks: List[MediaTrack] = field(default_factory=list)
    subtitle_tracks: List[MediaTrack] = field(default_factory=list)


class DownloadStatus(Enum):
    NOT_STARTED = "not_started"
    PARSING = "parsing"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadConfig:
    select_audio_lang: Optional[List[str] | str] = None
    select_subtitle_lang: Optional[List[str] | str] = None
    select_forced_subtitles: bool = False
    set_resolution: str = SET_RESOLUTION  # "best", "worst", o numero (es: "1080")
    auto_merge_tracks: bool = True
    concurrent_download: bool = CONCURRENT_DOWNLOAD
    thread_count: int = THREAD_COUNT
    retry_count: int = RETRY_COUNT
    mp4decrypt_path: str = get_bento4_decrypt_path()
    n_m3u8dl_path: str = get_n_m3u8dl_re_path()
    max_speed: str = MAX_SPEED
    enable_logging: bool = True
    use_raw_forDownload: bool = False  # If True: use raw file + base-url, if False: use original URL directly


@dataclass
class DownloadStatusInfo:
    status: DownloadStatus = DownloadStatus.NOT_STARTED
    is_completed: bool = False
    video_path: Optional[str] = None
    audios_paths: List[dict] = field(default_factory=list)
    subtitle_paths: List[dict] = field(default_factory=list)
    error_message: Optional[str] = None