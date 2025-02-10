# 09.06.24

import os
import re
import sys
import signal
import logging
from functools import partial


# External libraries
import httpx
from tqdm import tqdm


# Internal utilities
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.color import Colors
from StreamingCommunity.Util.console import console, Panel
from StreamingCommunity.Util._jsonConfig import config_manager
from StreamingCommunity.Util.os import internet_manager
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance


# Logic class
from ...FFmpeg import print_duration_table


# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Config
GET_ONLY_LINK = config_manager.get_bool('M3U8_PARSER', 'get_only_link')
REQUEST_TIMEOUT = config_manager.get_float('REQUESTS', 'timeout')

TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')



def signal_handler(signum, frame, kill_handler):
    """Signal handler for graceful interruption"""
    kill_handler[0] = True
    print("\nReceived interrupt signal. Completing current download...")


def MP4_downloader(url: str, path: str, referer: str = None, headers_: dict = None):
    """
    Downloads an MP4 video from a given URL with robust error handling and SSL bypass.

    Parameters:
        - url (str): The URL of the MP4 video to download.
        - path (str): The local path where the downloaded MP4 file will be saved.
        - referer (str, optional): The referer header value.
        - headers_ (dict, optional): Custom headers for the request.
    """
    if TELEGRAM_BOT:
        bot = get_bot_instance()
        console.log("####")

    if os.path.exists(path):
        console.log("[red]Output file already exists.")
        if TELEGRAM_BOT:
            bot.send_message(f"Contenuto già scaricato!", None)
        return 400

    # Early return for link-only mode
    if GET_ONLY_LINK:
        return {'path': path, 'url': url}

    # Validate URL
    if not (url.lower().startswith('http://') or url.lower().startswith('https://')):
        logging.error(f"Invalid URL: {url}")
        console.print(f"[bold red]Invalid URL: {url}[/bold red]")
        return None

    # Prepare headers
    try:
        headers = {}
        if referer:
            headers['Referer'] = referer
        
        # Use custom headers if provided, otherwise use default user agent
        if headers_:
            headers.update(headers_)
        else:
            headers['User-Agent'] = get_headers()

    except Exception as header_err:
        logging.error(f"Error preparing headers: {header_err}")
        console.print(f"[bold red]Error preparing headers: {header_err}[/bold red]")
        return None
    
    temp_path = f"{path}.temp"
    kill_handler = [False]  # Using list for mutable state
    original_handler = signal.signal(signal.SIGINT, partial(signal_handler, kill_handler=kill_handler))

    try:
        # Create a custom transport that bypasses SSL verification
        transport = httpx.HTTPTransport(
            verify=False, 
            http2=True
        )
        
        # Download with streaming and progress tracking
        with httpx.Client(transport=transport, timeout=httpx.Timeout(60)) as client:
            with client.stream("GET", url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                total = int(response.headers.get('content-length', 0))
                
                if total == 0:
                    console.print("[bold red]No video stream found.[/bold red]")
                    return None

                progress_bar = tqdm(
                    total=total,
                    ascii='░▒█',
                    bar_format=f"{Colors.YELLOW}[MP4]{Colors.WHITE}: "
                               f"{Colors.RED}{{percentage:.2f}}% {Colors.MAGENTA}{{bar}} {Colors.WHITE}[ "
                               f"{Colors.YELLOW}{{n_fmt}}{Colors.WHITE} / {Colors.RED}{{total_fmt}} {Colors.WHITE}] "
                               f"{Colors.YELLOW}{{elapsed}} {Colors.WHITE}< {Colors.CYAN}{{remaining}}{Colors.WHITE}, "
                               f"{Colors.YELLOW}{{rate_fmt}}{{postfix}} ",
                    unit='iB',
                    unit_scale=True,
                    desc='Downloading',
                    mininterval=0.05,
                    file=sys.stdout,                # Using file=sys.stdout to force in-place updates because sys.stderr may not support carriage returns in this environment.
                )

                downloaded = 0
                with open(temp_path, 'wb') as file, progress_bar as bar:
                    try:
                        for chunk in response.iter_bytes(chunk_size=1024):
                            if kill_handler[0]:
                                console.print("\n[bold yellow]Interrupting download...[/bold yellow]")
                                return None, True
                            
                            if chunk:
                                size = file.write(chunk)
                                downloaded += size
                                bar.update(size)

                    except KeyboardInterrupt:
                        console.print("\n[bold red]Download interrupted by user.[/bold red]")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        return None, True
                    
        # Rename temp file to final file
        if os.path.exists(temp_path):
            os.rename(temp_path, path)

        if os.path.exists(path):
            console.print(Panel(
                f"[bold green]Download completed![/bold green]\n"
                f"[cyan]File size: [bold red]{internet_manager.format_file_size(os.path.getsize(path))}[/bold red]\n"
                f"[cyan]Duration: [bold]{print_duration_table(path, description=False, return_string=True)}[/bold]", 
                title=f"{os.path.basename(path.replace('.mp4', ''))}", 
                border_style="green"
            ))

            if TELEGRAM_BOT:
                message = f"Download completato\nDimensione: {internet_manager.format_file_size(os.path.getsize(path))}\nDurata: {print_duration_table(path, description=False, return_string=True)}\nTitolo: {os.path.basename(path.replace('.mp4', ''))}"
                clean_message = re.sub(r'\[[a-zA-Z]+\]', '', message)
                bot.send_message(clean_message, None)

            return path, kill_handler[0]
        else:
            console.print("[bold red]Download failed or file is empty.[/bold red]")
            return None, kill_handler[0]

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        console.print(f"[bold red]Unexpected Error: {e}[/bold red]")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return None, kill_handler[0]
    
    finally:
        # Restore original signal handler
        signal.signal(signal.SIGINT, original_handler)