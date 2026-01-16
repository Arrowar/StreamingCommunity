# 3.12.23


# External library
from rich.console import Console


# Internal utilities
from StreamingCommunity.utils import config_manager


# Variable
console = Console()
CLEAN = config_manager.config.get_bool('DEFAULT', 'show_message')
SHOW = config_manager.config.get_bool('DEFAULT', 'show_message')


def start_message(clean: bool=True):
    """Display a stylized start message in the console."""
    msg = r'''
[green]→[purple]     ___                                         ______                     _           
[green]→[purple]    / _ | ___________ _    _____ _____[yellow]  __ __[purple]   / __/ /________ ___ ___ _  (_)__  ___ _ 
[green]→[purple]   / __ |/ __/ __/ _ \ |/|/ / _ `/ __/[yellow]  \ \ /[purple]  _\ \/ __/ __/ -_) _ `/  ' \/ / _ \/ _ `/ 
[green]→[purple]  /_/ |_/_/ /_/  \___/__,__/\_,_/_/   [yellow] /_\_\ [purple] /___/\__/_/  \__/\_,_/_/_/_/_/_//_/\_, /  
[green]→[purple]                                                                                /___/   
    '''

    if CLEAN and clean: 
        console.clear()
    
    if SHOW:
        console.print(f"[purple]{msg}")