# 17.10.24

import os
import re
import time
import logging
import shutil
from typing import Any, Dict, List, Optional


# External libraries
import httpx
from rich.console import Console
from rich.panel import Panel


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.headers import get_userAgent
from StreamingCommunity.Util.os import compute_sha1_hash, os_manager, internet_manager
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from ...FFmpeg import (
    print_duration_table,
    join_video,
    join_audios,
    join_subtitle
)
from ...M3U8 import M3U8_Parser, M3U8_UrlFix
from .segments import M3U8_Segments


# Config
ENABLE_AUDIO = config_manager.get_bool('M3U8_DOWNLOAD', 'download_audio')
ENABLE_SUBTITLE = config_manager.get_bool('M3U8_DOWNLOAD', 'download_subtitle')
DOWNLOAD_SPECIFIC_AUDIO = config_manager.get_list('M3U8_DOWNLOAD', 'specific_list_audio')
DOWNLOAD_SPECIFIC_SUBTITLE = config_manager.get_list('M3U8_DOWNLOAD', 'specific_list_subtitles')
MERGE_AUDIO = config_manager.get_bool('M3U8_DOWNLOAD', 'merge_audio')
MERGE_SUBTITLE = config_manager.get_bool('M3U8_DOWNLOAD', 'merge_subs')
CLEANUP_TMP = config_manager.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')
FILTER_CUSTOM_REOLUTION = str(config_manager.get('M3U8_PARSER', 'force_resolution')).strip().lower()
GET_ONLY_LINK = config_manager.get_bool('M3U8_PARSER', 'get_only_link')
RETRY_LIMIT = config_manager.get_int('REQUESTS', 'max_retry')
MAX_TIMEOUT = config_manager.get_int("REQUESTS", "timeout")
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')

console = Console()


class HLSClient:
    """Client for making HTTP requests to HLS endpoints with retry mechanism."""
    def __init__(self):
        self.headers = {'User-Agent': get_userAgent()}

    def request(self, url: str, return_content: bool = False) -> Optional[httpx.Response]:
        """
        Makes HTTP GET requests with retry logic.

        Args:
            url: Target URL to request
            return_content: If True, returns response content instead of text

        Returns:
            Response content/text or None if all retries fail
        """
        client = httpx.Client(headers=self.headers, timeout=MAX_TIMEOUT, follow_redirects=True)
        for attempt in range(RETRY_LIMIT):
            try:
                response = client.get(url)
                response.raise_for_status()
                return response.content if return_content else response.text

            except Exception as e:
                logging.error(f"Attempt {attempt+1} failed: {str(e)}")
                time.sleep(1.5 ** attempt)
        return None


class PathManager:
    """Manages file paths and directories for downloaded content."""
    def __init__(self, m3u8_url: str, output_path: Optional[str]):
        """
        Args:
            m3u8_url: Source M3U8 playlist URL
            output_path: Desired output path for the final video file
        """
        self.m3u8_url = m3u8_url
        self.output_path = self._sanitize_output_path(output_path)
        base_name = os.path.basename(self.output_path).replace(".mp4", "")
        self.temp_dir = os.path.join(os.path.dirname(self.output_path), f"{base_name}_tmp")

    def _sanitize_output_path(self, path: Optional[str]) -> str:
        """
        Ensures output path is valid and follows expected format.
        Creates a hash-based filename if no path is provided.
        """
        if not path:
            root = config_manager.get('OUT_FOLDER', 'root_path')
            hash_name = compute_sha1_hash(self.m3u8_url) + ".mp4"
            return os.path.join(root, "undefined", hash_name)

        if not path.endswith(".mp4"):
            path += ".mp4"

        return os_manager.get_sanitize_path(path)

    def setup_directories(self):
        """Creates necessary directories for temporary files (video, audio, subtitles)."""
        os.makedirs(self.temp_dir, exist_ok=True)
        for subdir in ['video', 'audio', 'subs']:
            os.makedirs(os.path.join(self.temp_dir, subdir), exist_ok=True)

    def move_final_file(self, final_file: str):
        """Moves the final merged file to the desired output location."""
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
        shutil.move(final_file, self.output_path)

    def cleanup(self):
        """Removes temporary directories if configured to do so."""
        if CLEANUP_TMP:
            os_manager.remove_folder(self.temp_dir)


class M3U8Manager:
    """Handles M3U8 playlist parsing and stream selection."""
    def __init__(self, m3u8_url: str, client: HLSClient):
        self.m3u8_url = m3u8_url
        self.client = client
        self.parser = M3U8_Parser()
        self.url_fixer = M3U8_UrlFix()
        self.video_url = None
        self.video_res = None
        self.audio_streams = []
        self.sub_streams = []
        self.is_master = False

    def parse(self):
        """
        Fetches and parses the M3U8 playlist content.
        Determines if it's a master playlist (index) or media playlist.
        """
        content = self.client.request(self.m3u8_url)
        if not content:
            raise ValueError("Failed to fetch M3U8 content")

        self.parser.parse_data(uri=self.m3u8_url, raw_content=content)
        self.url_fixer.set_playlist(self.m3u8_url)
        self.is_master = self.parser.is_master_playlist

    def select_streams(self):
        """
        Selects video, audio, and subtitle streams based on configuration.
        If it's a master playlist, only selects video stream.
        """
        if not self.is_master:
            self.video_url, self.video_res = self.m3u8_url, "0p"
            self.audio_streams = []
            self.sub_streams = []

        else:
            if str(FILTER_CUSTOM_REOLUTION) == "best":
                self.video_url, self.video_res = self.parser._video.get_best_uri()
            elif str(FILTER_CUSTOM_REOLUTION) == "worst":
                self.video_url, self.video_res = self.parser._video.get_worst_uri()
            elif "p" in str(FILTER_CUSTOM_REOLUTION):
                self.video_url, self.video_res = self.parser._video.get_custom_uri(int(FILTER_CUSTOM_REOLUTION.replace("p", "")))
            else:
                logging.error("Resolution not recognized.")
                self.video_url, self.video_res = self.parser._video.get_best_uri()

            self.audio_streams = []
            if ENABLE_AUDIO:
                self.audio_streams = [
                    s for s in (self.parser._audio.get_all_uris_and_names() or [])
                    if s.get('language') in DOWNLOAD_SPECIFIC_AUDIO
                ]

            self.sub_streams = []
            if ENABLE_SUBTITLE:
                if "*" in DOWNLOAD_SPECIFIC_SUBTITLE:
                    self.sub_streams = self.parser._subtitle.get_all_uris_and_names() or []

                else:
                    self.sub_streams = [
                        s for s in (self.parser._subtitle.get_all_uris_and_names() or [])
                        if s.get('language') in DOWNLOAD_SPECIFIC_SUBTITLE
                    ]

    def log_selection(self):
        tuple_available_resolution = self.parser._video.get_list_resolution()
        list_available_resolution = [f"{r[0]}x{r[1]}" for r in tuple_available_resolution]

        console.print(
            f"[cyan bold]Video    [/cyan bold] [green]Available:[/green] [purple]{', '.join(list_available_resolution)}[/purple] | "
            f"[red]Set:[/red] [purple]{FILTER_CUSTOM_REOLUTION}[/purple] | "
            f"[yellow]Downloadable:[/yellow] [purple]{self.video_res[0]}x{self.video_res[1]}[/purple]"
        )

        if self.parser.codec is not None:
            available_codec_info = (
                f"[green]v[/green]: [yellow]{self.parser.codec.video_codec_name}[/yellow] "
                f"([green]b[/green]: [yellow]{self.parser.codec.video_bitrate // 1000}k[/yellow]), "
                f"[green]a[/green]: [yellow]{self.parser.codec.audio_codec_name}[/yellow] "
                f"([green]b[/green]: [yellow]{self.parser.codec.audio_bitrate // 1000}k[/yellow])"
            )
            set_codec_info = available_codec_info if config_manager.get_bool("M3U8_CONVERSION", "use_codec") else "[purple]copy[/purple]"

            console.print(
                f"[bold cyan]Codec    [/bold cyan] [green]Available:[/green] {available_codec_info} | "
                f"[red]Set:[/red] {set_codec_info}"
            )

        # Get available subtitles and their languages
        available_subtitles = self.parser._subtitle.get_all_uris_and_names() or []
        available_sub_languages = [sub.get('language') for sub in available_subtitles]
        
        # If "*" is in DOWNLOAD_SPECIFIC_SUBTITLE, all languages are downloadable
        downloadable_sub_languages = available_sub_languages if "*" in DOWNLOAD_SPECIFIC_SUBTITLE else list(set(available_sub_languages) & set(DOWNLOAD_SPECIFIC_SUBTITLE))
            
        if available_sub_languages:
            console.print(
                f"[cyan bold]Subtitle [/cyan bold] [green]Available:[/green] [purple]{', '.join(available_sub_languages)}[/purple] | "
                f"[red]Set:[/red] [purple]{', '.join(DOWNLOAD_SPECIFIC_SUBTITLE)}[/purple] | "
                f"[yellow]Downloadable:[/yellow] [purple]{', '.join(downloadable_sub_languages)}[/purple]"
            )

        available_audio = self.parser._audio.get_all_uris_and_names() or []
        available_audio_languages = [audio.get('language') for audio in available_audio]
        downloadable_audio_languages = list(set(available_audio_languages) & set(DOWNLOAD_SPECIFIC_AUDIO))
        if available_audio_languages:
            console.print(
                f"[cyan bold]Audio    [/cyan bold] [green]Available:[/green] [purple]{', '.join(available_audio_languages)}[/purple] | "
                f"[red]Set:[/red] [purple]{', '.join(DOWNLOAD_SPECIFIC_AUDIO)}[/purple] | "
                f"[yellow]Downloadable:[/yellow] [purple]{', '.join(downloadable_audio_languages)}[/purple]"
            )
        print("")


class DownloadManager:
    """Manages downloading of video, audio, and subtitle streams."""
    def __init__(self, temp_dir: str, client: HLSClient, url_fixer: M3U8_UrlFix):
        """
        Args:
            temp_dir: Directory for storing temporary files
            client: HLSClient instance for making requests
            url_fixer: URL fixer instance for generating complete URLs
        """
        self.temp_dir = temp_dir
        self.client = client
        self.url_fixer = url_fixer
        self.missing_segments = []
        self.stopped = False

    def download_video(self, video_url: str):
        """Downloads video segments from the M3U8 playlist."""
        video_full_url = self.url_fixer.generate_full_url(video_url)
        video_tmp_dir = os.path.join(self.temp_dir, 'video')

        downloader = M3U8_Segments(url=video_full_url, tmp_folder=video_tmp_dir)
        result = downloader.download_streams("Video", "video")
        self.missing_segments.append(result)

        if result.get('stopped', False):
            self.stopped = True
        
        return self.stopped

    def download_audio(self, audio: Dict):
        """Downloads audio segments for a specific language track."""
        #if self.stopped:
        #    return True

        audio_full_url = self.url_fixer.generate_full_url(audio['uri'])
        audio_tmp_dir = os.path.join(self.temp_dir, 'audio', audio['language'])

        downloader = M3U8_Segments(url=audio_full_url, tmp_folder=audio_tmp_dir)
        result = downloader.download_streams(f"Audio {audio['language']}", "audio")
        self.missing_segments.append(result)

        if result.get('stopped', False):
            self.stopped = True
        return self.stopped

    def download_subtitle(self, sub: Dict):
        """Downloads and saves subtitle file for a specific language."""
        #if self.stopped:
        #    return True

        raw_content = self.client.request(sub['uri'])
        if raw_content:
            sub_path = os.path.join(self.temp_dir, 'subs', f"{sub['language']}.vtt")

            subtitle_parser = M3U8_Parser()
            subtitle_parser.parse_data(sub['uri'], raw_content)

            with open(sub_path, 'wb') as f:
                vtt_url = subtitle_parser.subtitle[-1]
                vtt_content = self.client.request(vtt_url, True)
                f.write(vtt_content)

        return self.stopped

    def download_all(self, video_url: str, audio_streams: List[Dict], sub_streams: List[Dict]):
        """
        Downloads all selected streams (video, audio, subtitles).
        """
        return_stopped = False

        video_file = os.path.join(self.temp_dir, 'video', '0.ts')
        if not os.path.exists(video_file):
            if self.download_video(video_url):
                if not return_stopped:
                    return_stopped = True

        for audio in audio_streams:
            #if self.stopped:
            #    break

            audio_file = os.path.join(self.temp_dir, 'audio', audio['language'], '0.ts')
            if not os.path.exists(audio_file):
                if self.download_audio(audio):
                    if not return_stopped:
                        return_stopped = True

        for sub in sub_streams:
            #if self.stopped:
            #    break

            sub_file = os.path.join(self.temp_dir, 'subs', f"{sub['language']}.vtt")
            if not os.path.exists(sub_file):
                if self.download_subtitle(sub):
                    if not return_stopped:
                        return_stopped = True

        return return_stopped


class MergeManager:
    """Handles merging of video, audio, and subtitle streams."""
    def __init__(self, temp_dir: str, parser: M3U8_Parser, audio_streams: List[Dict], sub_streams: List[Dict]):
        """
        Args:
            temp_dir: Directory containing temporary files
            parser: M3U8 parser instance with codec information
            audio_streams: List of audio streams to merge
            sub_streams: List of subtitle streams to merge
        """
        self.temp_dir = temp_dir
        self.parser = parser
        self.audio_streams = audio_streams
        self.sub_streams = sub_streams

    def merge(self) -> str:
        """
        Merges downloaded streams into final video file.
        Returns path to the final merged file.

        Process:
        1. If no audio/subs, just process video
        2. If audio exists, merge with video
        3. If subtitles exist, add them to the video
        """
        video_file = os.path.join(self.temp_dir, 'video', '0.ts')
        merged_file = video_file

        if not self.audio_streams and not self.sub_streams:
            merged_file = join_video(
                video_path=video_file,
                out_path=os.path.join(self.temp_dir, 'video.mp4'),
                codec=self.parser.codec
            )

        else:
            if MERGE_AUDIO and self.audio_streams:
                audio_tracks = [{
                    'path': os.path.join(self.temp_dir, 'audio', a['language'], '0.ts'),
                    'name': a['language']
                } for a in self.audio_streams]

                merged_audio_path = os.path.join(self.temp_dir, 'merged_audio.mp4')
                merged_file = join_audios(
                    video_path=video_file,
                    audio_tracks=audio_tracks,
                    out_path=merged_audio_path,
                    codec=self.parser.codec
                )

            if MERGE_SUBTITLE and self.sub_streams:
                sub_tracks = [{
                    'path': os.path.join(self.temp_dir, 'subs', f"{s['language']}.vtt"),
                    'language': s['language']
                } for s in self.sub_streams]

                merged_subs_path = os.path.join(self.temp_dir, 'final.mp4')
                merged_file = join_subtitle(
                    video_path=merged_file,
                    subtitles_list=sub_tracks,
                    out_path=merged_subs_path
                )

        return merged_file


class HLS_Downloader:
    """Main class for HLS video download and processing."""
    def __init__(self, m3u8_url: str, output_path: Optional[str] = None):
        self.m3u8_url = m3u8_url
        self.path_manager = PathManager(m3u8_url, output_path)
        self.client = HLSClient()
        self.m3u8_manager = M3U8Manager(m3u8_url, self.client)
        self.download_manager: Optional[DownloadManager] = None
        self.merge_manager: Optional[MergeManager] = None

    def start(self) -> Dict[str, Any]:
        """
        Main execution flow with handling for both index and playlist M3U8s.

        Returns:
            Dict containing:
                - path: Output file path
                - url: Original M3U8 URL
                - is_master: Whether the M3U8 was a master playlist
            Or raises an exception if there's an error
        """
        console.print(f"[cyan]You can safely stop the download with [bold]Ctrl+c[bold] [cyan] \n")
        
        if TELEGRAM_BOT:
            bot = get_bot_instance()

        try:
            if os.path.exists(self.path_manager.output_path):
                console.print(f"[red]Output file {self.path_manager.output_path} already exists![/red]")
                response = {
                    'path': self.path_manager.output_path,
                    'url': self.m3u8_url,
                    'is_master': False,
                    'msg': 'File already exists',
                    'error': None,
                    'stopped': False
                }
                if TELEGRAM_BOT:
                    bot.send_message(f"Contenuto già scaricato!", None)
                return response
            
            if GET_ONLY_LINK:
                console.print(f"URL: [bold red]{self.m3u8_url}[/bold red]")
                return {
                    'path': None,
                    'url': self.m3u8_url,
                    'is_master': getattr(self.m3u8_manager, 'is_master', None),
                    'msg': None,
                    'error': None,
                    'stopped': True
                }


            self.path_manager.setup_directories()

            # Parse M3U8 and determine if it's a master playlist
            self.m3u8_manager.parse()
            self.m3u8_manager.select_streams()
            self.m3u8_manager.log_selection()

            self.download_manager = DownloadManager(
                temp_dir=self.path_manager.temp_dir,
                client=self.client,
                url_fixer=self.m3u8_manager.url_fixer
            )

            # Check if download was stopped
            download_stopped = self.download_manager.download_all(
                video_url=self.m3u8_manager.video_url,
                audio_streams=self.m3u8_manager.audio_streams,
                sub_streams=self.m3u8_manager.sub_streams
            )

            self.merge_manager = MergeManager(
                temp_dir=self.path_manager.temp_dir,
                parser=self.m3u8_manager.parser,
                audio_streams=self.m3u8_manager.audio_streams,
                sub_streams=self.m3u8_manager.sub_streams
            )

            final_file = self.merge_manager.merge()
            self.path_manager.move_final_file(final_file)
            self._print_summary()
            self.path_manager.cleanup()

            return {
                'path': self.path_manager.output_path,
                'url': self.m3u8_url,
                'is_master': self.m3u8_manager.is_master,
                'msg': None,
                'error': None,
                'stopped': download_stopped
            }

        except Exception as e:
            error_msg = str(e)
            console.print(f"[red]Download failed: {error_msg}[/red]")
            logging.error("Download error", exc_info=True)

            return {
                'path': None,
                'url': self.m3u8_url,
                'is_master': getattr(self.m3u8_manager, 'is_master', None),
                'msg': None,
                'error': error_msg,
                'stopped': False
            }

    def _print_summary(self):
        """Prints download summary including file size, duration, and any missing segments."""
        if TELEGRAM_BOT:
            bot = get_bot_instance()

        missing_ts = False
        missing_info = ""
        for item in self.download_manager.missing_segments:
            if int(item['nFailed']) >= 1:
                missing_ts = True
                missing_info += f"[red]TS Failed: {item['nFailed']} {item['type']} tracks[/red]"

        file_size = internet_manager.format_file_size(os.path.getsize(self.path_manager.output_path))
        duration = print_duration_table(self.path_manager.output_path, description=False, return_string=True)

        panel_content = (
            f"[cyan]File size: [bold red]{file_size}[/bold red]\n"
            f"[cyan]Duration: [bold]{duration}[/bold]\n"
            f"[cyan]Output: [bold]{os.path.abspath(self.path_manager.output_path)}[/bold]"
        )

        if TELEGRAM_BOT:
            message = f"Download completato\nDimensione: {file_size}\nDurata: {duration}\nPercorso: {os.path.abspath(self.path_manager.output_path)}"
            clean_message = re.sub(r'\[[a-zA-Z]+\]', '', message)
            bot.send_message(clean_message, None)

        if missing_ts:
            panel_content += f"\n{missing_info}"
            os.rename(self.path_manager.output_path, self.path_manager.output_path.replace(".mp4", "_failed.mp4"))

        console.print(Panel(
            panel_content,
            title=f"{os.path.basename(self.path_manager.output_path.replace('.mp4', ''))}",
            border_style="green"
        ))