# 25.07.25

import os
import sys
import shutil
import logging
from typing import Optional, Dict


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util import config_manager, os_manager, internet_manager
from StreamingCommunity.Util.os import get_wvd_path, get_prd_path
from StreamingCommunity.Util.http_client import create_client, get_userAgent


# Logic class
from ..MPD import MPD_Parser, DRMSystem
from .segments import MPD_Segments
from .decrypt import decrypt_with_mp4decrypt
from .extractor import get_widevine_keys, get_playready_keys, map_keys_to_representations


# FFmpeg functions
from StreamingCommunity.Lib.FFmpeg.util import print_duration_table
from StreamingCommunity.Lib.FFmpeg.merge import join_audios, join_video, join_subtitle


# Config
console = Console()
DOWNLOAD_SPECIFIC_SUBTITLE = config_manager.config.get_list('M3U8_DOWNLOAD', 'specific_list_subtitles')
MERGE_SUBTITLE = config_manager.config.get_bool('M3U8_DOWNLOAD', 'merge_subs')
CLEANUP_TMP = config_manager.config.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')
EXTENSION_OUTPUT = config_manager.config.get("M3U8_CONVERSION", "extension")


class DASH_Downloader:
    def __init__(self, license_url, mpd_url, mpd_sub_list: list = None, output_path: str = None, drm_preference: str = 'widevine'):
        """
        Initialize the DASH Downloader with necessary parameters.

        Parameters:
            - license_url (str): URL to obtain the license for decryption.
            - mpd_url (str): URL of the MPD manifest file.
            - mpd_sub_list (list): List of subtitle dicts with keys: 'language', 'url', 'format'.
            - output_path (str): Path to save the final output file.
        """
        self.cdm_device = get_wvd_path()
        self.prd_device = get_prd_path()
        self.license_url = str(license_url).strip() if license_url else None
        self.mpd_url = str(mpd_url).strip()
        self.mpd_sub_list = mpd_sub_list

        if drm_preference.lower() in [DRMSystem.WIDEVINE, DRMSystem.PLAYREADY]:
            self.PREFERRED_DRM = drm_preference.lower()
        else:
            sys.exit(f"Invalid DRM preference: {drm_preference}. Use 'widevine', 'playready'.")
        
        # Sanitize the output path to remove invalid characters
        sanitized_output_path = os_manager.get_sanitize_path(output_path)
        self.out_path = os.path.splitext(os.path.abspath(sanitized_output_path))[0]
        self.original_output_path = sanitized_output_path
        self.file_already_exists = os.path.exists(self.original_output_path)
        self.parser = None

        # Pre-selected representations (set by parse_manifest)
        self.selected_subs = []
        self.selected_video = None
        self.selected_audio = None

        self._setup_temp_dirs()

        self.error = None
        self.stopped = False
        self.output_file = None
        
        # For progress tracking
        self.current_downloader: Optional[MPD_Segments] = None
        self.current_download_type: Optional[str] = None

    def _setup_temp_dirs(self):
        """
        Create temporary folder structure under out_path\tmp
        """
        if self.file_already_exists:
            return

        self.tmp_dir = os.path.join(self.out_path, "tmp")
        self.encrypted_dir = os.path.join(self.tmp_dir, "encrypted")
        self.decrypted_dir = os.path.join(self.tmp_dir, "decrypted")
        self.subs_dir = os.path.join(self.tmp_dir, "subs")
        
        os.makedirs(self.encrypted_dir, exist_ok=True)
        os.makedirs(self.decrypted_dir, exist_ok=True)
        os.makedirs(self.subs_dir, exist_ok=True)

    def parse_manifest(self, custom_headers):
        """
        Parse the MPD manifest file and select representations based on configuration.
        """
        if self.file_already_exists:
            return

        # Initialize parser with tmp directory for auto-save and subtitle list
        self.parser = MPD_Parser(self.mpd_url, auto_save=True, save_dir=self.tmp_dir, mpd_sub_list=self.mpd_sub_list)
        self.parser.parse(custom_headers)

        # Select representations based on configuration
        self.selected_video, _, _, _ = self.parser.select_video()
        self.selected_audio, _, _, _ = self.parser.select_audio()

        # Auto-select subtitles based on selected audio language
        selected_audio_language = self.selected_audio.get('language') if self.selected_audio else None
        
        # Only process subtitles if mpd_sub_list is not None
        if self.mpd_sub_list is not None:
            if "*" in DOWNLOAD_SPECIFIC_SUBTITLE:
                self.selected_subs = self.mpd_sub_list
            elif selected_audio_language and selected_audio_language in DOWNLOAD_SPECIFIC_SUBTITLE:
                # If audio language is in the specific list, prioritize it
                self.selected_subs = [
                    sub for sub in self.mpd_sub_list 
                    if sub.get('language') == selected_audio_language
                ]
            else:
                # Fallback to configured languages
                self.selected_subs = [
                    sub for sub in self.mpd_sub_list 
                    if sub.get('language') in DOWNLOAD_SPECIFIC_SUBTITLE
                ]

            # If no subtitles match configuration but we have audio language, auto-select matching subtitle
            if not self.selected_subs and selected_audio_language:
                matching_subs = [
                    sub for sub in self.mpd_sub_list 
                    if sub.get('language') == selected_audio_language
                ]
                if matching_subs:
                    console.print(f"[yellow]Auto-selecting subtitle for audio language: {selected_audio_language}")
                    self.selected_subs = matching_subs
        else:
            self.selected_subs = []

        # Print table with selections (only once here)
        self.parser.print_tracks_table(self.selected_video, self.selected_audio, self.selected_subs)
        console.print("")

    def get_representation_by_type(self, typ):
        """
        Get the representation of the selected stream by type.
        """
        if typ == "video":
            return getattr(self, "selected_video", None)
        elif typ == "audio":
            return getattr(self, "selected_audio", None)
        return None

    def download_subtitles(self) -> bool:
        """
        Download subtitle files based on parser's selected subtitles.
        Returns True if successful or if no subtitles to download, False on critical error.
        """
        if not self.selected_subs or self.mpd_sub_list is None:
            return True
            
        client = create_client(headers={'User-Agent': get_userAgent()})
        
        for sub in self.selected_subs:
            try:
                language = sub.get('language')
                fmt = sub.get('format', 'vtt')
                
                console.log(f"[cyan]Downloading subtitle[white]: [red]{language} ({fmt})")
                
                # Get segment URLs (can be single or multiple)
                segment_urls = sub.get('segment_urls')
                single_url = sub.get('url')
                
                # Build list of URLs to download
                urls_to_download = []
                if segment_urls:
                    urls_to_download = segment_urls
                elif single_url:
                    urls_to_download = [single_url]
                else:
                    console.print(f"[yellow]Warning: No URL found for subtitle {language}")
                    continue
                
                # Download all segments
                all_content = []
                for seg_url in urls_to_download:
                    response = client.get(seg_url)
                    response.raise_for_status()
                    all_content.append(response.content)
                
                # Concatenate all segments
                final_content = b''.join(all_content)
                
                # Save to file
                sub_filename = f"{language}.{fmt}"
                sub_path = os.path.join(self.subs_dir, sub_filename)
                
                with open(sub_path, 'wb') as f:
                    f.write(final_content)
                    
            except Exception as e:
                console.print(f"[red]Error downloading subtitle {language}: {e}")
                return False
            
        return True

    def download_and_decrypt(self, custom_headers=None, query_params=None, key=None) -> bool:
        """
        Download and decrypt video/audio streams using automatic key mapping based on default_KID.

        Args:
            - custom_headers (dict): Optional HTTP headers for the license request.
            - query_params (dict): Optional query parameters to append to the license URL.
            - key (str): Optional raw license data to bypass HTTP request.
        """
        if self.file_already_exists:
            console.print(f"[red]File already exists: {self.original_output_path}")
            self.output_file = self.original_output_path
            return True
        
        self.error = None
        self.stopped = False

        # Check if any representation is protected
        has_protected_content = any(rep.get('protected', False) for rep in self.parser.representations)
        
        # If no protection found, download without decryption
        if not has_protected_content:
            console.log("[yellow]Warning: Content is not protected, downloading without decryption.")
            return self.download_segments(clear=True)
        
        # Determine which DRM to use
        drm_type = self._determine_drm_type()
        
        if not drm_type:
            console.print("[red]Content is protected but no DRM system found")
            return False

        # Fetch keys based on DRM type
        keys = self._fetch_drm_keys(drm_type, custom_headers, query_params, key)
        
        if not keys:
            console.print(f"[red]Failed to obtain keys for {drm_type}")
            return False

        # Map keys to representations based on default_KID
        key_mapping = map_keys_to_representations(keys, self.parser.representations)

        # Fallback: if only one key is available, use it even if mapping fails/partial
        single_key = keys[0] if keys and len(keys) == 1 else None

        if not key_mapping:
            if single_key:
                console.print("[yellow]Warning: key mapping failed, but only 1 CONTENT key is available. Falling back to the single key for video/audio.")
                key_mapping = {
                    "video": {"kid": single_key["kid"], "key": single_key["key"], "representation_id": None, "default_kid": None},
                    "audio": {"kid": single_key["kid"], "key": single_key["key"], "representation_id": None, "default_kid": None},
                }
            else:
                console.print("[red]Could not map any keys to representations.")
                console.print(f"[red]Available keys: {[k['kid'] for k in keys]}")
                console.print(f"[red]Representation KIDs: {[r.get('default_kid') for r in self.parser.representations if r.get('default_kid')]}")
                return False

        # Download subtitles
        self.download_subtitles()

        # Get encryption method from parser
        encryption_method = self.parser.encryption_method

        # Download and decrypt video
        video_rep = self.get_representation_by_type("video")
        if video_rep:
            video_downloader = MPD_Segments(tmp_folder=self.encrypted_dir, representation=video_rep, pssh=self._get_pssh_for_drm(drm_type), custom_headers=custom_headers)
            encrypted_path = video_downloader.get_concat_path(self.encrypted_dir)

            # If m4s file doesn't exist, start downloading
            if not os.path.exists(encrypted_path):
                self.current_downloader = video_downloader
                self.current_download_type = 'video'

                try:
                    result = video_downloader.download_streams(description="Video")
                
                    # Check for interruption or failure
                    if result.get("stopped"):
                        self.stopped = True
                        self.error = "Download interrupted"
                        return False
                    
                    if result.get("nFailed", 0) > 0:
                        self.error = f"Failed segments: {result['nFailed']}"
                        return False
                    
                except Exception as ex:
                    self.error = str(ex)
                    return False
                
                finally:
                    self.current_downloader = None
                    self.current_download_type = None

                # Decrypt video ONLY if it's protected
                decrypted_path = os.path.join(self.decrypted_dir, f"video.{EXTENSION_OUTPUT}")
                
                if video_rep.get('protected', False):
                    video_key_info = key_mapping.get("video")
                    if not video_key_info and single_key:
                        console.print("[yellow]Warning: no mapped key found for video; using the single available key.")
                        video_key_info = {"kid": single_key["kid"], "key": single_key["key"], "representation_id": None, "default_kid": None}
                    
                    if not video_key_info:
                        self.error = "No key found for video representation"
                        return False

                    console.log(f"[cyan]Using video key: [red]{video_key_info['kid']}[white]: [red]{video_key_info['key']} [cyan]for representation [yellow]{video_key_info.get('representation_id', 'N/A')}")
                    
                    # Use encryption method from video representation or parser
                    video_encryption = video_rep.get('encryption_method') or encryption_method
                    result_path = decrypt_with_mp4decrypt("Video", encrypted_path, video_key_info['kid'], video_key_info['key'],  output_path=decrypted_path, encryption_method=video_encryption)

                    if not result_path:
                        self.error = f"Video decryption failed with key {video_key_info['kid']}"
                        return False
                else:
                    console.log("[cyan]Video is not protected, copying without decryption")
                    shutil.copy2(encrypted_path, decrypted_path)

        else:
            self.error = "No video found"
            return False
            
        # Download and decrypt audio
        audio_rep = self.get_representation_by_type("audio")
        if audio_rep:
            audio_key_info = key_mapping.get("audio")
            if not audio_key_info and single_key:
                console.print("[yellow]Warning: no mapped key found for audio; using the single available key.")
                audio_key_info = {"kid": single_key["kid"], "key": single_key["key"], "representation_id": None, "default_kid": None}
            if not audio_key_info:
                self.error = "No key found for audio representation"
                return False

            console.log(f"[cyan]Using audio key: [red]{audio_key_info['kid']}[white]: [red]{audio_key_info['key']} [cyan]for representation [yellow]{audio_key_info.get('representation_id', 'N/A')}")
            audio_language = audio_rep.get('language', 'Unknown')
            audio_downloader = MPD_Segments(tmp_folder=self.encrypted_dir, representation=audio_rep, pssh=self._get_pssh_for_drm(drm_type), custom_headers=custom_headers)
            encrypted_path = audio_downloader.get_concat_path(self.encrypted_dir)

            # If m4s file doesn't exist, start downloading
            if not os.path.exists(encrypted_path):

                # Set current downloader for progress tracking
                self.current_downloader = audio_downloader
                self.current_download_type = f"audio_{audio_language}"

                try:
                    result = audio_downloader.download_streams(description=f"Audio {audio_language}")

                    # Check for interruption or failure
                    if result.get("stopped"):
                        self.stopped = True
                        self.error = "Download interrupted"
                        return False
                    
                    if result.get("nFailed", 0) > 0:
                        self.error = f"Failed segments: {result['nFailed']}"
                        return False
                    
                except Exception as ex:
                    self.error = str(ex)
                    return False
                
                finally:
                    self.current_downloader = None
                    self.current_download_type = None

                # Decrypt audio using the mapped key and encryption method
                decrypted_path = os.path.join(self.decrypted_dir, f"audio.{EXTENSION_OUTPUT}")
                
                # Use encryption method from audio representation or parser
                audio_encryption = audio_rep.get('encryption_method') or encryption_method
                result_path = decrypt_with_mp4decrypt(f"Audio {audio_language}", encrypted_path, audio_key_info['kid'], audio_key_info['key'], output_path=decrypted_path, encryption_method=audio_encryption)

                if not result_path:
                    self.error = f"Audio decryption failed with key {audio_key_info['kid']}"
                    return False

        else:
            self.error = "No audio found"
            return False

        return True
    
    def _determine_drm_type(self) -> Optional[str]:
        """
        Determine which DRM type to use based on available PSSH and preference.
        Returns: 'widevine', 'playready', or None
        """
        # Check if DRM types are available from parsed representations
        available_drm_types = self.parser.available_drm_types or []
        
        if not available_drm_types:
            return None
        
        # Check if preferred DRM is available
        if self.PREFERRED_DRM in available_drm_types:
            console.log(f"[cyan]Using {self.PREFERRED_DRM.upper()} DRM")
            return self.PREFERRED_DRM
        
        # Fallback to first available DRM type
        fallback_drm = available_drm_types[0]
        console.log(f"[yellow]Preferred DRM {self.PREFERRED_DRM.upper()} not available, using {fallback_drm.upper()}")
        return fallback_drm
    
    def _get_pssh_for_drm(self, drm_type: str) -> Optional[str]:
        """Get PSSH for specific DRM type"""
        if drm_type == DRMSystem.WIDEVINE:
            return self.parser.pssh_widevine
        elif drm_type == DRMSystem.PLAYREADY:
            return self.parser.pssh_playready
        return None
    
    def _fetch_drm_keys(self, drm_type: str, custom_headers: dict, query_params: dict, key: str) -> Optional[list]:
        """Fetch decryption keys for specific DRM type"""
        pssh = self._get_pssh_for_drm(drm_type)
        
        if not pssh:
            console.print(f"[red]No PSSH found for {drm_type}")
            return None
        
        if drm_type == DRMSystem.WIDEVINE:
            return get_widevine_keys(pssh=pssh, license_url=self.license_url, cdm_device_path=self.cdm_device, headers=custom_headers, query_params=query_params, key=key)
        elif drm_type == DRMSystem.PLAYREADY:
            return get_playready_keys(pssh=pssh, license_url=self.license_url, cdm_device_path=self.prd_device, headers=custom_headers, query_params=query_params, key=key)
        return None
    
    def download_segments(self, clear=False):
        """
        Download video/audio segments without decryption (for clear content).
        
        Parameters:
            clear (bool): If True, content is not encrypted and doesn't need decryption
        """
        if not clear:
            console.print("[yellow]Warning: download_segments called with clear=False")
            return False
        
        # Download subtitles
        self.download_subtitles()
        
        # Download video
        video_rep = self.get_representation_by_type("video")
        if video_rep:
            video_downloader = MPD_Segments(
                tmp_folder=self.encrypted_dir,
                representation=video_rep,
                pssh=self.parser.pssh
            )
            encrypted_path = video_downloader.get_concat_path(self.encrypted_dir)

            # If m4s file doesn't exist, start downloading
            if not os.path.exists(encrypted_path):
                self.current_downloader = video_downloader
                self.current_download_type = 'video'
                
                try:
                    result = video_downloader.download_streams(description="Video")
                    
                    # Check for interruption or failure
                    if result.get("stopped"):
                        self.stopped = True
                        self.error = "Download interrupted"
                        return False
                    
                    if result.get("nFailed", 0) > 0:
                        self.error = f"Failed segments: {result['nFailed']}"
                        return False
                    
                except Exception as ex:
                    self.error = str(ex)
                    console.print(f"[red]Error downloading video: {ex}")
                    return False
                
                finally:
                    self.current_downloader = None
                    self.current_download_type = None
            
            # NO DECRYPTION: just copy/move to decrypted folder
            decrypted_path = os.path.join(self.decrypted_dir, f"video.{EXTENSION_OUTPUT}")
            if os.path.exists(encrypted_path) and not os.path.exists(decrypted_path):
                shutil.copy2(encrypted_path, decrypted_path)

        else:
            self.error = "No video found"
            console.print(f"[red]{self.error}")
            return False
        
        # Download audio with segment limiting
        audio_rep = self.get_representation_by_type("audio")
        if audio_rep:
            audio_language = audio_rep.get('language', 'Unknown')
            audio_downloader = MPD_Segments(tmp_folder=self.encrypted_dir, representation=audio_rep, pssh=self.parser.pssh)
            encrypted_path = audio_downloader.get_concat_path(self.encrypted_dir)

            # If m4s file doesn't exist, start downloading
            if not os.path.exists(encrypted_path):
                self.current_downloader = audio_downloader
                self.current_download_type = f"audio_{audio_language}"
                
                try:
                    result = audio_downloader.download_streams(description=f"Audio {audio_language}")
                    
                    # Check for interruption or failure
                    if result.get("stopped"):
                        self.stopped = True
                        self.error = "Download interrupted"
                        return False
                    
                    if result.get("nFailed", 0) > 0:
                        self.error = f"Failed segments: {result['nFailed']}"
                        return False
                    
                except Exception as ex:
                    self.error = str(ex)
                    console.print(f"[red]Error downloading audio: {ex}")
                    return False
                
                finally:
                    self.current_downloader = None
                    self.current_download_type = None
            
            # NO DECRYPTION: just copy/move to decrypted folder
            decrypted_path = os.path.join(self.decrypted_dir, f"audio.{EXTENSION_OUTPUT}")
            if os.path.exists(encrypted_path) and not os.path.exists(decrypted_path):
                shutil.copy2(encrypted_path, decrypted_path)
                
        else:
            self.error = "No audio found"
            console.print(f"[red]{self.error}")
            return False
        
        return True

    def finalize_output(self):
        """
        Merge video, audio, and optionally subtitles into final output file.
        """
        if self.file_already_exists:
            output_file = self.original_output_path
            self.output_file = output_file
            return output_file
        
        # Definition of decrypted files
        video_file = os.path.join(self.decrypted_dir, f"video.{EXTENSION_OUTPUT}")
        audio_file = os.path.join(self.decrypted_dir, f"audio.{EXTENSION_OUTPUT}")
        output_file = self.original_output_path
        
        # Set the output file path for status tracking
        self.output_file = output_file
        use_shortest = False

        # Merge video and audio
        merged_file = None
        try:
            if os.path.exists(video_file) and os.path.exists(audio_file):
                audio_tracks = [{"path": audio_file}]
                merged_file, use_shortest = join_audios(video_file, audio_tracks, output_file)
                
            elif os.path.exists(video_file):
                merged_file = join_video(video_file, output_file, codec=None)
                
            else:
                console.print("[red]Video file missing, cannot export")
                self.error = "Video file missing, cannot export"
                return None
                
        except Exception as e:
            console.print(f"[red]Error during merge: {e}")
            self.error = f"Merge failed: {e}"
            return None
        
        # Merge subtitles if available
        if MERGE_SUBTITLE and self.selected_subs and self.mpd_sub_list is not None:

            # Check which subtitle files actually exist
            existing_sub_tracks = []
            for sub in self.selected_subs:
                language = sub.get('language', 'unknown')
                fmt = sub.get('format', 'vtt')
                sub_path = os.path.join(self.subs_dir, f"{language}.{fmt}")
                
                if os.path.exists(sub_path):
                    existing_sub_tracks.append({
                        'path': sub_path,
                        'language': language
                    })
            
            if existing_sub_tracks:

                # Create temporary file for subtitle merge
                temp_output = output_file.replace(f'.{EXTENSION_OUTPUT}', f'_temp.{EXTENSION_OUTPUT}')
                
                try:
                    final_file = join_subtitle(
                        video_path=merged_file,
                        subtitles_list=existing_sub_tracks,
                        out_path=temp_output
                    )
                    
                    # Replace original with subtitled version
                    if os.path.exists(final_file):
                        if os.path.exists(output_file):
                            os.remove(output_file)
                        os.rename(final_file, output_file)
                        merged_file = output_file
                        
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to merge subtitles: {e}")
        
        # Handle failed sync case
        if use_shortest:
            new_filename = output_file.replace(EXTENSION_OUTPUT, f"_failed_sync.{EXTENSION_OUTPUT}")
            if os.path.exists(output_file):
                os.rename(output_file, new_filename)
                output_file = new_filename
                self.output_file = new_filename

        # Display file information
        file_size = internet_manager.format_file_size(os.path.getsize(output_file))
        duration = print_duration_table(output_file, description=False, return_string=True)
        console.print(f"[yellow]Output[white]: [red]{os.path.abspath(output_file)} \n"
            f"  [cyan]with size[white]: [red]{file_size} \n"
            f"      [cyan]and duration[white]: [red]{duration}")

        if CLEANUP_TMP:
            
            # Clean up: delete only the tmp directory, not the main directory
            if os.path.exists(self.tmp_dir):
                shutil.rmtree(self.tmp_dir, ignore_errors=True)

            # Only remove the temp base directory if it was created specifically for this download
            # and if the final output is NOT inside this directory
            output_dir = os.path.dirname(self.original_output_path)
            
            # Check if out_path is different from the actual output directory
            # and if it's empty, then it's safe to remove
            if (self.out_path != output_dir and os.path.exists(self.out_path) and not os.listdir(self.out_path)):
                try:
                    os.rmdir(self.out_path)

                except Exception:
                    pass

        # Verify the final file exists before returning
        if os.path.exists(output_file):
            return output_file
        else:
            self.error = "Final output file was not created successfully"
            return None
    
    def get_status(self):
        """
        Returns a dict with 'path', 'error', and 'stopped' for external use.
        """
        return {
            "path": self.output_file,
            "error": self.error,
            "stopped": self.stopped
        }
    
    def get_progress_data(self) -> Optional[Dict]:
        """Get current download progress data."""
        if not self.current_downloader:
            return None

        try:
            progress = self.current_downloader.get_progress_data()
            if progress:
                progress['download_type'] = self.current_download_type
            return progress
            
        except Exception as e:
            logging.error(f"Error getting progress data: {e}")
            return None