# 25.07.25

import os
import shutil


# External libraries
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Lib.FFmpeg.command import join_audios, join_video


# Logic class
from .parser import MPDParser
from .segments import MPD_Segments
from .decrypt import decrypt_with_mp4decrypt
from .cdm_helpher import get_widevine_keys


# Config
DOWNLOAD_SPECIFIC_AUDIO = config_manager.get_list('M3U8_DOWNLOAD', 'specific_list_audio')
FILTER_CUSTOM_REOLUTION = str(config_manager.get('M3U8_CONVERSION', 'force_resolution')).strip().lower()
CLEANUP_TMP = config_manager.get_bool('M3U8_DOWNLOAD', 'cleanup_tmp_folder')


# Variable
console = Console()


class DASH_Downloader:
    def __init__(self, cdm_device, license_url, mpd_url, output_path):
        self.cdm_device = cdm_device
        self.license_url = license_url
        self.mpd_url = mpd_url
        self.original_output_path = os.path.abspath(str(output_path))
        self.out_path = os.path.splitext(self.original_output_path)[0]
        self.parser = None
        self._setup_temp_dirs()

        self.error = None
        self.stopped = False
        self.output_file = None

    def _setup_temp_dirs(self):
        """
        Create temporary folder structure under out_path\tmp
        """
        self.tmp_dir = os.path.join(self.out_path, "tmp")
        self.encrypted_dir = os.path.join(self.tmp_dir, "encrypted")
        self.decrypted_dir = os.path.join(self.tmp_dir, "decrypted")
        self.optimize_dir = os.path.join(self.tmp_dir, "optimize")
        
        os.makedirs(self.encrypted_dir, exist_ok=True)
        os.makedirs(self.decrypted_dir, exist_ok=True)
        os.makedirs(self.optimize_dir, exist_ok=True)

    def parse_manifest(self, custom_headers):
        self.parser = MPDParser(self.mpd_url)
        self.parser.parse(custom_headers)

        # Video info
        selected_video, list_available_resolution, filter_custom_resolution, downloadable_video = self.parser.select_video(FILTER_CUSTOM_REOLUTION)
        console.print(
            f"[cyan bold]Video    [/cyan bold] [green]Available:[/green] [purple]{', '.join(list_available_resolution)}[/purple] | "
            f"[red]Set:[/red] [purple]{filter_custom_resolution}[/purple] | "
            f"[yellow]Downloadable:[/yellow] [purple]{downloadable_video}[/purple]"
        )
        self.selected_video = selected_video

        # Audio info 
        selected_audio, list_available_audio_langs, filter_custom_audio, downloadable_audio = self.parser.select_audio(DOWNLOAD_SPECIFIC_AUDIO)
        console.print(
            f"[cyan bold]Audio    [/cyan bold] [green]Available:[/green] [purple]{', '.join(list_available_audio_langs)}[/purple] | "
            f"[red]Set:[/red] [purple]{filter_custom_audio}[/purple] | "
            f"[yellow]Downloadable:[/yellow] [purple]{downloadable_audio}[/purple]"
        )
        self.selected_audio = selected_audio

    def get_representation_by_type(self, typ):
        if typ == "video":
            return getattr(self, "selected_video", None)
        elif typ == "audio":
            return getattr(self, "selected_audio", None)
        return None

    def download_and_decrypt(self, custom_headers=None, custom_payload=None):
        """
        Download and decrypt video/audio streams. Sets self.error, self.stopped, self.output_file.
        Returns True if successful, False otherwise.
        """
        self.error = None
        self.stopped = False

        for typ in ["video", "audio"]:
            rep = self.get_representation_by_type(typ)
            if rep:
                encrypted_path = os.path.join(self.encrypted_dir, f"{rep['id']}_encrypted.m4s")

                # If m4s file doesn't exist start downloading
                if not os.path.exists(encrypted_path):
                    downloader = MPD_Segments(
                        tmp_folder=self.encrypted_dir,
                        representation=rep,
                        pssh=self.parser.pssh
                    )

                    try:
                        result = downloader.download_streams()

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

                if not self.parser.pssh:
                    print("No PSSH found: segments are not encrypted, skipping decryption.")
                    self.download_segments(clear=True)
                    return True

                keys = get_widevine_keys(
                    pssh=self.parser.pssh,
                    license_url=self.license_url,
                    cdm_device_path=self.cdm_device,
                    headers=custom_headers,
                    payload=custom_payload
                )
                
                if not keys:
                    self.error = f"No key found, cannot decrypt {typ}"
                    print(self.error)
                    return False

                key = keys[0]
                KID = key['kid']
                KEY = key['key']

                decrypted_path = os.path.join(self.decrypted_dir, f"{typ}.mp4")
                result_path = decrypt_with_mp4decrypt(
                    encrypted_path, KID, KEY, output_path=decrypted_path
                )

                if not result_path:
                    self.error = f"Decryption of {typ} failed"
                    print(self.error)
                    return False

            else:
                self.error = f"No {typ} found"
                print(self.error)
                return False

        return True

    def download_segments(self, clear=False):
        # Download segments and concatenate them
        # clear=True: no decryption needed
        pass

    def finalize_output(self):
        video_file = os.path.join(self.decrypted_dir, "video.mp4")
        audio_file = os.path.join(self.decrypted_dir, "audio.mp4")

        # fallback: if one of the two is missing, look in encrypted
        if not os.path.exists(video_file):
            for f in os.listdir(self.encrypted_dir):
                if f.endswith("_encrypted.m4s") and ("video" in f or f.startswith("1_")):
                    video_file = os.path.join(self.encrypted_dir, f)
                    break
        if not os.path.exists(audio_file):
            for f in os.listdir(self.encrypted_dir):
                if f.endswith("_encrypted.m4s") and ("audio" in f or f.startswith("0_")):
                    audio_file = os.path.join(self.encrypted_dir, f)
                    break

        # Usa il nome file originale per il file finale
        output_file = self.original_output_path

        if os.path.exists(video_file) and os.path.exists(audio_file):
            audio_tracks = [{"path": audio_file}]
            join_audios(video_file, audio_tracks, output_file)
        elif os.path.exists(video_file):
            join_video(video_file, output_file, codec=None)
        else:
            print("Video file missing, cannot export")

        # Clean up: delete all tmp
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

        # Rimuovi la cartella principale se è vuota
        try:
            if os.path.exists(self.out_path) and not os.listdir(self.out_path):
                os.rmdir(self.out_path)
        except Exception as e:
            print(f"[WARN] Impossibile eliminare la cartella {self.out_path}: {e}")
        

        return self.output_file

    def get_status(self):
        """
        Returns a dict with 'path', 'error', and 'stopped' for external use.
        """
        return {
            "path": self.output_file,
            "error": self.error,
            "stopped": self.stopped
        }