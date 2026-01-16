# 05.01.26

import os
import time
import glob
import shutil
import logging
from typing import Optional, Dict, Any


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils.http_client import get_headers
from StreamingCommunity.core.processors import join_video, join_audios, join_subtitles
from StreamingCommunity.utils import config_manager, os_manager, internet_manager
from StreamingCommunity.setup import get_wvd_path, get_prd_path


# Logic class
from ..extractors import MPDParser, DRMSystem, get_widevine_keys, get_playready_keys
from StreamingCommunity.source.N_m3u8 import MediaDownloader


# Config
console = Console()
CLEANUP_TMP = config_manager.config.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')
EXTENSION_OUTPUT = config_manager.config.get("M3U8_CONVERSION", "extension")


class DASH_Downloader:
    def __init__(self, license_url: str, license_headers: Dict[str, str] = None, mpd_url: str = None, mpd_headers: Dict[str, str] = None, mpd_sub_list: list = None, output_path: str = None, drm_preference: str = 'widevine', decrypt_preference : str = "shaka", query_params: Dict[str, str] = None, key: str = None, cookies: Dict[str, str] = None):
        """
        Initialize DASH Downloader.
        
        Parameters:
            license_url: URL to obtain DRM license
            mpd_url: URL of the MPD manifest
            mpd_sub_list: List of subtitle dicts (unused with MediaDownloader)
            output_path: Full path including filename and extension (e.g., /path/to/video.mp4)
            drm_preference: Preferred DRM system ('widevine', 'playready', 'auto')
        """
        self.mpd_url = str(mpd_url).strip() if mpd_url else None
        self.license_url = str(license_url).strip() if license_url else None
        self.mpd_headers = mpd_headers
        self.license_headers = license_headers
        self.query_params = query_params or {}
        self.mpd_sub_list = mpd_sub_list or []
        self.drm_preference = drm_preference.lower()
        self.key = key
        self.cookies = cookies or {}
        self.decrypt_preference = decrypt_preference.lower()
        
        if self.mpd_headers is None:
            self.mpd_headers = get_headers()
        if self.mpd_headers is None:
            self.mpd_headers = get_headers()

        self.raw_mpd_path = None
        
        # Sanitize and validate output path
        self.output_path = os_manager.get_sanitize_path(output_path)
        if not self.output_path.endswith(f'.{EXTENSION_OUTPUT}'):
            self.output_path += f'.{EXTENSION_OUTPUT}'
        
        # Extract directory and filename components ONCE
        self.output_dir = os.path.dirname(self.output_path)
        self.filename_base = os.path.splitext(os.path.basename(self.output_path))[0]
        
        # Check if file already exists
        self.file_already_exists = os.path.exists(self.output_path)
        
        # DRM info
        self.drm_info = None
        self.decryption_keys = []
        
        # MediaDownloader instance
        self.media_downloader = None
        self.meta_json, self.meta_selected, self.raw_mpd = None, None, None
        
        # Status tracking
        self.error = None
        self.last_merge_result = None
    
    def _fetch_drm_info(self) -> bool:
        """Parse MPD and extract DRM information from raw.mpd file if available, otherwise fetch from URL"""
        try:
            parser = MPDParser(self.mpd_url, headers=self.mpd_headers)
            parser.parse_from_file(self.raw_mpd)
            self.drm_info = parser.get_drm_info(self.drm_preference)
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error parsing MPD for DRM info: {e}")
            return False
    
    def _fetch_decryption_keys(self) -> bool:
        """Fetch decryption keys based on DRM type"""
        if not self.license_url or not self.drm_info or not self.drm_info['pssh']:
            console.print("[yellow]No DRM protection or missing license info")
            return True
        
        drm_type = self.drm_info['selected_drm_type']
        pssh = self.drm_info['pssh']
        
        try:
            time.sleep(0.25)
            if drm_type == DRMSystem.WIDEVINE:
                keys = get_widevine_keys(
                    pssh=pssh,
                    license_url=self.license_url,
                    cdm_device_path=get_wvd_path(),
                    headers=self.license_headers,
                    query_params=self.query_params,
                    key=self.key
                )

            elif drm_type == DRMSystem.PLAYREADY:
                keys = get_playready_keys(
                    pssh=pssh,
                    license_url=self.license_url,
                    cdm_device_path=get_prd_path(),
                    headers=self.license_headers,
                    query_params=self.query_params,
                    key=self.key
                )

            else:
                console.print(f"[red]Unsupported DRM type: {drm_type}")
                self.error = f"Unsupported DRM type: {drm_type}"
                return False
            
            if keys:
                self.decryption_keys = keys
                return True
            
            else:
                console.print("[red]Failed to fetch decryption keys")
                self.error = "Failed to fetch decryption keys"
                return False
                
        except Exception as e:
            console.print(f"[red]Error fetching keys: {e}")
            self.error = f"Key fetch error: {e}"
            return False
    
    def start(self) -> Dict[str, Any]:
        """Main execution flow for downloading DASH content"""
        if self.file_already_exists:
            console.log(f"[yellow]File already exists: [red]{self.output_path}")
            return self.output_path, False
        
        # Create output directory
        os_manager.create_path(self.output_dir)
        
        # Initialize MediaDownloader
        self.media_downloader = MediaDownloader(
            url=self.mpd_url,
            output_dir=self.output_dir,
            filename=self.filename_base,
            headers=self.mpd_headers,
            cookies=self.cookies,
            decrypt_preference=self.decrypt_preference
        )
        if self.mpd_sub_list:
            self.media_downloader.external_subtitles = self.mpd_sub_list
        self.media_downloader.parser_stream()
        
        # Parse MPD for DRM info (uses raw.mpd if available, falls back to URL)
        console.print("\n[cyan]Starting fetching decryption keys...")
        self.meta_json, self.meta_selected, _, self.raw_mpd = self.media_downloader.get_metadata()
        self._fetch_drm_info()
        
        # Fetch decryption keys if DRM protected
        if self.drm_info and self.drm_info['available_drm_types']:
            if not self._fetch_decryption_keys():
                logging.error(f"Failed to fetch decryption keys: {self.error}")
                return None, True
        
        # Set decryption keys on the existing MediaDownloader instance
        self.media_downloader.set_key(self.decryption_keys if self.decryption_keys else None)
        status = self.media_downloader.start_download()    
    
        # Merge files using FFmpeg
        final_file = self._merge_files(status)
        
        if not final_file or not os.path.exists(final_file):
            logging.error("Merge operation failed")
            return None, True
        
        # Move to final location if needed
        if os.path.abspath(final_file) != os.path.abspath(self.output_path):
            try:
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                os.rename(final_file, self.output_path)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not move file: {e}")
                self.output_path = final_file
        
        # Print summary and cleanup
        self._print_summary()
        if CLEANUP_TMP:
            self._cleanup_temp_files(status)
        return self.output_path, False

    def _merge_files(self, status) -> Optional[str]:
        """Merge downloaded files using FFmpeg"""
        video_path = status['video'].get('path')
        
        if not os.path.exists(video_path):
            console.print(f"[red]Video file not found: {video_path}")
            self.error = "Video file missing"
            return None
        
        # If no additional tracks, mux video using join_video
        if not status['audios'] and not status['subtitles']:
            console.print("[cyan]\nNo additional tracks to merge, muxing video...")
            merged_file, result_json = join_video(
                video_path=video_path,
                out_path=self.output_path
            )
            self.last_merge_result = result_json
            if os.path.exists(merged_file):
                return merged_file
            else:
                self.error = "Video mux failed"
                return None
        
        current_file = video_path
        
        # Merge audio tracks if present
        if status['audios']:
            console.print(f"[cyan]\nMerging [red]{len(status['audios'])} [cyan]audio track(s)...")
            audio_output = os.path.join(self.output_dir, f"{self.filename_base}_with_audio.{EXTENSION_OUTPUT}")
            
            merged_file, use_shortest, result_json = join_audios(
                video_path=current_file,
                audio_tracks=status['audios'],
                out_path=audio_output
            )
            self.last_merge_result = result_json
            
            if os.path.exists(merged_file):
                current_file = merged_file
            else:
                console.print("[yellow]Audio merge failed, continuing with video only")
        
        # Merge subtitles if enabled and present
        if status['subtitles']:
            console.print(f"[cyan]\nMerging [red]{len(status['subtitles'])} [cyan]subtitle track(s)...")
            sub_output = os.path.join(self.output_dir, f"{self.filename_base}_final.{EXTENSION_OUTPUT}")
            
            merged_file, result_json = join_subtitles(
                video_path=current_file,
                subtitles_list=status['subtitles'],
                out_path=sub_output
            )
            self.last_merge_result = result_json
            
            if os.path.exists(merged_file):
                if current_file != video_path and os.path.exists(current_file):
                    try:
                        os.remove(current_file)
                    except Exception:
                        pass
                current_file = merged_file
            else:
                console.print("[yellow]Subtitle merge failed, continuing without subtitles")
    
        return current_file

    def _cleanup_temp_files(self, status):
        """Clean up temporary files"""
        files_to_remove = []
        
        # Add original downloaded files
        if status['video'] and os.path.abspath(status['video'].get('path')) != os.path.abspath(self.output_path):
            files_to_remove.append(status['video'].get('path'))
        
        for audio in status['audios']:
            if os.path.abspath(audio.get('path')) != os.path.abspath(self.output_path):
                files_to_remove.append(audio.get('path'))
        
        for sub in status['subtitles']:
            if os.path.abspath(sub.get('path')) != os.path.abspath(self.output_path):
                files_to_remove.append(sub.get('path'))

        for ext_sub in status['external_subtitles']:
            if os.path.abspath(ext_sub.get('path')) != os.path.abspath(self.output_path):
                files_to_remove.append(ext_sub.get('path'))
        
        # Remove intermediate merge files
        intermediate_patterns = [
            f"{self.filename_base}_with_audio.{EXTENSION_OUTPUT}",
            f"{self.filename_base}_final.{EXTENSION_OUTPUT}"
        ]
        
        for pattern in intermediate_patterns:
            file_path = os.path.join(self.output_dir, pattern)
            if os.path.exists(file_path) and os.path.abspath(file_path) != os.path.abspath(self.output_path):
                files_to_remove.append(file_path)
        
        # Remove files
        for file_path in files_to_remove:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logging.warning(f"Could not remove temp file {file_path}: {e}")

        for log_file in glob.glob(os.path.join(self.output_dir, "*.log")):
            os.remove(log_file)
        shutil.rmtree(os.path.join(self.output_dir, "analysis_temp"), ignore_errors=True)
    
    def _print_summary(self):
        """Print download summary"""
        if not os.path.exists(self.output_path):
            return
        
        file_size = internet_manager.format_file_size(os.path.getsize(self.output_path))
        duration = 'N/A'
        
        if self.last_merge_result and isinstance(self.last_merge_result, dict):
            duration = self.last_merge_result.get('time', 'N/A')
        
        console.print("\n[green]Output:")
        console.print(f"  [cyan]Path: [red]{os.path.abspath(self.output_path)}")
        console.print(f"  [cyan]Size: [red]{file_size}")
        console.print(f"  [cyan]Duration: [red]{duration}")