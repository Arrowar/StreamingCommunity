# 15.06.24

import os
import shutil
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime


# External library
import httpx
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table


# Variable
max_timeout = 15
console = Console()
local_path = os.path.join(".")
from StreamingCommunity.Upload.version import __author__, __title__


def move_content(source: str, destination: str):
    """
    Move all content from the source folder to the destination folder.

    Parameters:
        - source (str): The path to the source folder.
        - destination (str): The path to the destination folder.
    """
    os.makedirs(destination, exist_ok=True)

    # Iterate through all elements in the source folder
    for element in os.listdir(source):
        source_path = os.path.join(source, element)
        destination_path = os.path.join(destination, element)

        # If it's a directory, recursively call the function
        if os.path.isdir(source_path):
            move_content(source_path, destination_path)
        else:
            shutil.move(source_path, destination_path)


def keep_specific_items(directory: str, keep_folder: str, keep_file: str):
    """
    Deletes all items in the given directory except for the specified folder, 
    the specified file, and the '.git' directory.

    Parameters:
        - directory (str): The path to the directory.
        - keep_folder (str): The name of the folder to keep.
        - keep_file (str): The name of the file to keep.
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        console.print(f"[red]Error: '{directory}' is not a valid directory.")
        return

    # Define folders and files to skip
    skip_folders = {keep_folder, ".git"}
    skip_files = {keep_file}

    # Iterate through items in the directory
    for item in os.listdir(directory):
        if item in skip_folders or item in skip_files:
            continue

        item_path = os.path.join(directory, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                console.log(f"[green]Removed directory: {item_path}")
            elif os.path.isfile(item_path):
                os.remove(item_path)
                console.log(f"[green]Removed file: {item_path}")
        except Exception as e:
            console.log(f"[yellow]Skipping {item_path} due to error: {e}")


def print_commit_info(commit_info: dict):
    """
    Print detailed information about the commit in a formatted table.
    
    Parameters:
        - commit_info (dict): The commit information from GitHub API
    """

    # Create a table for commit information
    table = Table(title=f"[bold green]Latest Commit Information - {__title__}", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="yellow")

    # Basic commit info
    commit = commit_info['commit']
    commit_date = datetime.strptime(commit['author']['date'], "%Y-%m-%dT%H:%M:%SZ")
    formatted_date = commit_date.strftime("%Y-%m-%d %H:%M:%S")

    # Add rows to the table
    table.add_row("Repository", f"{__author__}/{__title__}")
    table.add_row("Commit SHA", commit_info['sha'][:8])
    table.add_row("Author", f"{commit['author']['name']} <{commit['author']['email']}>")
    table.add_row("Date", formatted_date)
    table.add_row("Committer", f"{commit['committer']['name']} <{commit['committer']['email']}>")
    table.add_row("Message", commit['message'])
    
    # Add stats if available
    if 'stats' in commit_info:
        stats = commit_info['stats']
        table.add_row("Changes", f"+{stats['additions']} -[red]{stats['deletions']}[/red] ({stats['total']} total)")

    # Add URL info
    table.add_row("HTML URL", commit_info['html_url'])
    
    # Print the table in a panel
    console.print(Panel.fit(table))


def download_and_extract_latest_commit():
    """
    Download and extract the latest commit from a GitHub repository.
    """
    try:

        # Get the latest commit information using GitHub API
        api_url = f'https://api.github.com/repos/{__author__}/{__title__}/commits?per_page=1'
        console.log("[green]Requesting latest commit from GitHub repository...")
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'{__title__}-updater'
        }
        response = httpx.get(api_url, headers=headers, timeout=max_timeout, follow_redirects=True)

        if response.status_code == 200:
            commit_info = response.json()[0]
            commit_sha = commit_info['sha']
            
            # Print detailed commit information
            print_commit_info(commit_info)

            zipball_url = f'https://github.com/{__author__}/{__title__}/archive/{commit_sha}.zip'
            console.log("[green]Downloading latest commit zip file...")

            # Download the zipball
            response = httpx.get(zipball_url, follow_redirects=True, timeout=max_timeout)
            temp_path = os.path.join(os.path.dirname(os.getcwd()), 'temp_extracted')

            # Extract the content of the zipball into a temporary folder
            with ZipFile(BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(temp_path)
            console.log("[green]Extracting files...")

            # Move files from the temporary folder to the current folder
            for item in os.listdir(temp_path):
                item_path = os.path.join(temp_path, item)
                destination_path = os.path.join(local_path, item)
                shutil.move(item_path, destination_path)

            # Remove the temporary folder
            shutil.rmtree(temp_path)

            # Move all folder to main folder
            new_folder_name = f"{__title__}-{commit_sha}"
            move_content(new_folder_name, ".")
            shutil.rmtree(new_folder_name)
            
            console.log("[cyan]Latest commit downloaded and extracted successfully.")
        else:
            console.log(f"[red]Failed to fetch commit information. Status code: {response.status_code}")

    except httpx.RequestError as e:
        console.print(f"[red]Request failed: {e}")

    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}")


def main_upload():
    """
    Main function to upload the latest commit of a GitHub repository.
    """
    cmd_insert = Prompt.ask(
        "[bold red]Are you sure you want to delete all files? (Only 'Video' folder and 'update.py' will remain)",
        choices=['y', 'n'],
        default='y',
        show_choices=True
    )

    if cmd_insert.lower().strip() == 'y' or cmd_insert.lower().strip() == 'yes':
        console.print("[red]Deleting all files except 'Video' folder and 'update.py'...")
        keep_specific_items(".", "Video", "upload.py")
        download_and_extract_latest_commit()
    else:
        console.print("[red]Operation cancelled.")


if __name__ == "__main__":
    main_upload()