# 25.07.25

import os
import shutil


# External libraries
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import internet_manager
from ...FFmpeg import print_duration_table, join_audios, join_video


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
        self.out_path = os.path.splitext(os.path.abspath(str(output_path)))[0]
        self.original_output_path = output_path
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

        def calculate_column_widths():
            """Calculate optimal column widths based on content."""
            data_rows = []
            
            # Video info
            selected_video, list_available_resolution, filter_custom_resolution, downloadable_video = self.parser.select_video(FILTER_CUSTOM_REOLUTION)
            self.selected_video = selected_video
            
            available_video = ', '.join(list_available_resolution) if list_available_resolution else "Nothing"
            set_video = str(filter_custom_resolution) if filter_custom_resolution else "Nothing"
            downloadable_video_str = str(downloadable_video) if downloadable_video else "Nothing"
            
            data_rows.append(["Video", available_video, set_video, downloadable_video_str])

            # Audio info 
            selected_audio, list_available_audio_langs, filter_custom_audio, downloadable_audio = self.parser.select_audio(DOWNLOAD_SPECIFIC_AUDIO)
            self.selected_audio = selected_audio
            
            available_audio = ', '.join(list_available_audio_langs) if list_available_audio_langs else "Nothing"
            set_audio = str(filter_custom_audio) if filter_custom_audio else "Nothing"
            downloadable_audio_str = str(downloadable_audio) if downloadable_audio else "Nothing"
            
            data_rows.append(["Audio", available_audio, set_audio, downloadable_audio_str])
            
            # Calculate max width for each column
            headers = ["Type", "Available", "Set", "Downloadable"]
            max_widths = [len(header) for header in headers]
            
            for row in data_rows:
                for i, cell in enumerate(row):
                    max_widths[i] = max(max_widths[i], len(str(cell)))
            
            # Add some padding
            max_widths = [w + 2 for w in max_widths]
            
            return data_rows, max_widths
        
        data_rows, column_widths = calculate_column_widths()
        
        # Create table with dynamic widths
        table = Table(show_header=True, header_style="bold cyan", border_style="blue")
        table.add_column("Type", style="cyan bold", width=column_widths[0])
        table.add_column("Available", style="green", width=column_widths[1])
        table.add_column("Set", style="red", width=column_widths[2])
        table.add_column("Downloadable", style="yellow", width=column_widths[3])
        
        # Add all rows to the table
        for row in data_rows:
            table.add_row(*row)

        console.print("[cyan]You can safely stop the download with [bold]Ctrl+c[bold] [cyan]")
        console.print(table)
        console.print("")

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

        # Fetch keys immediately after obtaining PSSH
        if not self.parser.pssh:
            console.print("[red]No PSSH found: segments are not encrypted, skipping decryption.")
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
            console.print("[red]No keys found, cannot proceed with download.[/red]")
            return False

        # Extract the first key for decryption
        key = keys[0]
        KID = key['kid']
        KEY = key['key']

        for typ in ["video", "audio"]:
            rep = self.get_representation_by_type(typ)
            if rep:
                encrypted_path = os.path.join(self.encrypted_dir, f"{rep['id']}_encrypted.m4s")

                # If m4s file doesn't exist, start downloading
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

        # Definenition of decrypted files
        video_file = os.path.join(self.decrypted_dir, "video.mp4")
        audio_file = os.path.join(self.decrypted_dir, "audio.mp4")
        output_file = self.original_output_path
        
        # Set the output file path for status tracking
        self.output_file = output_file
        use_shortest = False

        if os.path.exists(video_file) and os.path.exists(audio_file):
            audio_tracks = [{"path": audio_file}]
            _, use_shortest = join_audios(video_file, audio_tracks, output_file)

        elif os.path.exists(video_file):
            _ = join_video(video_file, output_file, codec=None)

        else:
            console.print("[red]Video file missing, cannot export[/red]")
            return None
        
        # Handle failed sync case
        if use_shortest:
            new_filename = output_file.replace(".mp4", "_failed_sync.mp4")
            os.rename(output_file, new_filename)
            output_file = new_filename
            self.output_file = new_filename

        # Display file information
        if os.path.exists(output_file):
            file_size = internet_manager.format_file_size(os.path.getsize(output_file))
            duration = print_duration_table(output_file, description=False, return_string=True)

            panel_content = (
                f"[cyan]File size: [bold red]{file_size}[/bold red]\n"
                f"[cyan]Duration: [bold]{duration}[/bold]\n"
                f"[cyan]Output: [bold]{os.path.abspath(output_file)}[/bold]"
            )

            print("")
            console.print(Panel(
                panel_content,
                title=f"{os.path.basename(output_file.replace('.mp4', ''))}",
                border_style="green"
            ))

        else:
            console.print(f"[red]Output file not found: {output_file}")

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

            except Exception as e:
                console.print(f"[red]Cannot remove directory {self.out_path}: {e}")

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
