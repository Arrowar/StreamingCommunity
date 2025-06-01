<p align="center">
  <img src="https://i.ibb.co/v6RnT0wY/s2.jpg" alt="Project Logo" width="450"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/streamingcommunity">
    <img src="https://img.shields.io/pypi/v/streamingcommunity?logo=pypi&labelColor=555555&style=for-the-badge" alt="PyPI"/>
  </a>
  <a href="https://www.paypal.com/donate/?hosted_button_id=UXTWMT8P6HE2C">
    <img src="https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge" alt="Donate"/>
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/commits">
    <img src="https://img.shields.io/github/commit-activity/m/Arrowar/StreamingCommunity?label=commits&style=for-the-badge" alt="Commits"/>
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/commits">
    <img src="https://img.shields.io/github/last-commit/Arrowar/StreamingCommunity/main?label=&style=for-the-badge&display_timestamp=committer" alt="Last Commit"/>
  </a>
</p>

<p align="center">
  <a href="https://github.com/Arrowar/StreamingCommunity/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-GPL_3.0-blue.svg?style=for-the-badge" alt="License"/>
  </a>
  <a href="https://pypi.org/project/streamingcommunity">
    <img src="https://img.shields.io/pypi/dm/streamingcommunity?style=for-the-badge" alt="PyPI Downloads"/>
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Arrowar/StreamingCommunity/main/.github/media/loc-badge.json&style=for-the-badge" alt="Lines of Code"/>
  </a>
</p>

# 📋 Table of Contents

<details>
<summary>📦 Installation</summary>

- 🔄 [Update Domains](#update-domains)
- 🌐 [Available Sites](https://arrowar.github.io/StreamingCommunity/)
- 🛠️ [Installation](#installation)
    - 📦 [PyPI Installation](#1-pypi-installation)
    - 🔄 [Automatic Installation](#2-automatic-installation)
    - 🔧 [Binary Location](#binary-location)
    - 📝 [Manual Installation](#3-manual-installation)
        - 💻 [Win 7](https://github.com/Ghost6446/StreamingCommunity_api/wiki/Installation#win-7)
        - 📱 [Termux](https://github.com/Ghost6446/StreamingCommunity_api/wiki/Termux)
</details>

<details>
<summary>⚙️ Configuration & Usage</summary>

- ⚙️ [Configuration](#configuration)
    - 🔧 [Default](#default-settings)
    - 📩 [Request](#requests-settings)
    - 📥 [Download](#m3u8_download-settings)
    - 🔍 [Parser](#m3u8_parser-settings)
- 📝 [Command](#command)
- 🔍 [Global search](#global-search)
- 💻 [Examples of terminal](#examples-of-terminal-usage)
</details>

<details>
<summary>🔧 Advanced Features</summary>

- 🔧 [Manual domain configuration](#update-domains)
- 🐳 [Docker](#docker)
- 📝 [Telegram Usage](#telegram-usage)
</details>

<details>
<summary>ℹ️ Help & Support</summary>

- 🎓 [Tutorial](#tutorials)
- 📝 [To do](#to-do)
- ⚠️ [Disclaimer](#disclaimer)
</details>

# Installation

<p align="center">
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_win.exe">
    <img src="https://img.shields.io/badge/-Windows-blue.svg?style=for-the-badge&logo=windows" alt="Windows">
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_mac">
    <img src="https://img.shields.io/badge/-macOS-black.svg?style=for-the-badge&logo=apple" alt="macOS">
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux">
    <img src="https://img.shields.io/badge/-Linux-orange.svg?style=for-the-badge&logo=linux" alt="Linux">
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux_previous">
    <img src="https://img.shields.io/badge/-Linux Previous-gray.svg?style=for-the-badge&logo=linux" alt="Linux Previous">
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/releases">
    <img src="https://img.shields.io/badge/-All Versions-lightgrey.svg?style=for-the-badge&logo=github" alt="All Versions">
  </a>
</p>

## 1. PyPI Installation

Install directly from PyPI:

```bash
pip install StreamingCommunity
```

Update to the latest version:

```bash
pip install --upgrade StreamingCommunity
```

## Quick Start

Create a simple script (`run_streaming.py`) to launch the main application:

```python
from StreamingCommunity.run import main

if __name__ == "__main__":
    main()
```

Run the script:

```bash
python run_streaming.py
```

## Modules

<details>
<summary>📥 HLS Downloader</summary>

Download HTTP Live Streaming (HLS) content from m3u8 URLs.

```python
from StreamingCommunity.Download import HLS_Downloader

# Initialize with m3u8 URL and optional output path
downloader = HLS_Downloader(
    m3u8_url="https://example.com/stream.m3u8",
    output_path="/downloads/video.mp4"  # Optional
)

# Start the download
downloader.download()
```

See [HLS example](./Test/Download/HLS.py) for complete usage.
</details>

<details>
<summary>📽️ MP4 Downloader</summary>

Direct MP4 file downloader with support for custom headers and referrer.

```python
from StreamingCommunity.Download import MP4_downloader

# Basic usage
downloader = MP4_downloader(
    url="https://example.com/video.mp4",
    path="/downloads/saved_video.mp4"
)

# Advanced usage with custom headers and referrer
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
downloader = MP4_downloader(
    url="https://example.com/video.mp4",
    path="/downloads/saved_video.mp4",
    referer="https://example.com",
    headers_=headers
)

# Start download
downloader.download()
```

See [MP4 example](./Test/Download/MP4.py) for complete usage.
</details>

<details>
<summary>🧲 Torrent Client</summary>

Download content via torrent magnet links.

```python
from StreamingCommunity.Download import TOR_downloader

# Initialize torrent client
client = TOR_downloader()

# Add magnet link
client.add_magnet_link("magnet:?xt=urn:btih:example_hash&dn=example_name", save_path=".")

# Start download
client.start_download()
```

See [Torrent example](./Test/Download/TOR.py) for complete usage.
</details>

## Binary Location

<details>
<summary>📂 Default Locations</summary>

- **Windows**: `C:\binary`
- **MacOS**: `~/Applications/binary`
- **Linux**: `~/.local/bin/binary`
</details>

<details>
<summary>🪟 Windows Configuration</summary>

1. Move the binary folder from `C:\binary` to your desired location
2. Add the new path to Windows environment variables:
   - Open Start menu and search for "Environment Variables"
   - Click "Edit the system environment variables"
   - Click "Environment Variables" button
   - Under "System Variables", find and select "Path"
   - Click "Edit"
   - Add the new binary folder path
   - Click "OK" to save changes

For detailed Windows PATH instructions, see the [Windows PATH guide](https://www.eukhost.com/kb/how-to-add-to-the-path-on-windows-10-and-windows-11/).
</details>

<details>
<summary>🍎 MacOS Configuration</summary>

1. Move the binary folder from `~/Applications/binary` to your desired location
2. Add the new path to your shell's configuration file:
   ```bash
   # For bash (edit ~/.bash_profile)
   export PATH="/your/custom/path:$PATH"

   # For zsh (edit ~/.zshrc)
   export PATH="/your/custom/path:$PATH"
   ```
3. Reload your shell configuration:
   ```bash
   # For bash
   source ~/.bash_profile

   # For zsh
   source ~/.zshrc
   ```
</details>

<details>
<summary>🐧 Linux Configuration</summary>

1. Move the binary folder from `~/.local/bin/binary` to your desired location
2. Add the new path to your shell's configuration file:
   ```bash
   # For bash (edit ~/.bashrc)
   export PATH="/your/custom/path:$PATH"

   # For zsh (edit ~/.zshrc)
   export PATH="/your/custom/path:$PATH"
   ```
3. Apply the changes:
   ```bash
   source ~/.bashrc   # for bash
   # or
   source ~/.zshrc    # for zsh
   ```
</details>

> [!IMPORTANT]
> After moving the binary folder, ensure that all executables (ffmpeg, ffprobe, ffplay) are present in the new location and have the correct permissions:
> - Windows: `.exe` extensions required
> - MacOS/Linux: Ensure files have execute permissions (`chmod +x filename`)

## 3. Manual Installation

<details>
<summary>📋 Requirements</summary>

Prerequisites:
* [Python](https://www.python.org/downloads/) > 3.8
* [FFmpeg](https://www.gyan.dev/ffmpeg/builds/)
</details>

<details>
<summary>⚙️ Python Dependencies</summary>

```bash
pip install -r requirements.txt
```
</details>

<details>
<summary>🚀 Usage</summary>

#### On Windows:

```powershell
python test_run.py
```

#### On Linux/MacOS:

```bash
python3 test_run.py
```
</details>

## Update

Keep your script up to date with the latest features by running:

### On Windows:

```powershell
python update.py
```

### On Linux/MacOS:

```bash
python3 update.py
```

<br>

## Update Domains

<details>
<summary>🌐 Domain Configuration Methods</summary>

There are two ways to update the domains for the supported websites:

### 1. Using Local Configuration

1. Create a `domains.json` file in the root directory of the project

2. Add your domain configuration in the following format:
   ```json
   {
      "altadefinizione": {
          "domain": "si",
          "full_url": "https://altadefinizione.si/"
      },
      ...
   }
   ```
   
3. Set `use_api` to `false` in the `DEFAULT` section of your `config.json`:
   ```json
   {
      "DEFAULT": {
         "use_api": false
      }
   }
   ```

### 2. Using API (Legacy)

The API-based domain updates are currently deprecated. To use it anyway, set `use_api` to `true` in your `config.json` file.

Note: If `use_api` is set to `false` and no `domains.json` file is found, the script will raise an error.

#### 💡 Adding a New Site to the Legacy API
If you want to add a new site to the legacy API, just message me on the Discord server, and I'll add it!

</details>

# Configuration

<details>
<summary>⚙️ Overview</summary>

You can change some behaviors by tweaking the configuration file. The configuration file is divided into several main sections.
</details>

<details>
<summary>🔧 DEFAULT Settings</summary>

```json
{
    "DEFAULT": {
        "debug": false,
        "show_message": true,
        "clean_console": true,
        "show_trending": true,
        "use_api": true,
        "not_close": false,
        "telegram_bot": false,
        "download_site_data": false,
        "validate_github_config": false
    }
}
```

- `debug`: Enables debug logging
- `show_message`: Displays informational messages
- `clean_console`: Clears the console between operations
- `show_trending`: Shows trending content
- `use_api`: Uses API for domain updates instead of local configuration
- `not_close`: If set to true, keeps the program running after download is complete
  * Can be changed from terminal with `--not_close true/false`
- `telegram_bot`: Enables Telegram bot integration
- `download_site_data`: If set to false, disables automatic site data download
- `validate_github_config`: If set to false, disables validation and updating of configuration from GitHub
</details>

<details>
<summary>📁 OUT_FOLDER Settings</summary>

```json
{
    "OUT_FOLDER": {
        "root_path": "Video",
        "movie_folder_name": "Movie",
        "serie_folder_name": "Serie",
        "anime_folder_name": "Anime",
        "map_episode_name": "E%(episode)_%(episode_name)",
        "add_siteName": false
    }
}
```

#### Directory Configuration
- `root_path`: Directory where all videos will be saved
  * Windows: `C:\\MyLibrary\\Folder` or `\\\\MyServer\\MyLibrary` (network folder)
  * Linux/MacOS: `Desktop/MyLibrary/Folder`

#### Folder Names
- `movie_folder_name`: Subdirectory for movies (can be changed with `--movie_folder_name`)
- `serie_folder_name`: Subdirectory for TV series (can be changed with `--serie_folder_name`)
- `anime_folder_name`: Subdirectory for anime (can be changed with `--anime_folder_name`)

#### Episode Naming
- `map_episode_name`: Template for episode filenames
  * `%(tv_name)`: Name of TV Show
  * `%(season)`: Season number
  * `%(episode)`: Episode number
  * `%(episode_name)`: Episode name
  * Can be changed with `--map_episode_name`

#### Additional Options
- `add_siteName`: Appends site_name to root path (can be changed with `--add_siteName true/false`)
</details>

<details>
<summary>🔄 QBIT_CONFIG Settings</summary>

```json
{
    "QBIT_CONFIG": {
        "host": "192.168.1.51",
        "port": "6666",
        "user": "admin",
        "pass": "adminadmin"
    }
}
```

To enable qBittorrent integration, follow the setup guide [here](https://github.com/lgallard/qBittorrent-Controller/wiki/How-to-enable-the-qBittorrent-Web-UI).
</details>

<details>
<summary>📡 REQUESTS Settings</summary>

```json
{
    "REQUESTS": {
        "verify": false,
        "timeout": 20,
        "max_retry": 8,
        "proxy": {
            "http": "http://username:password@host:port",
            "https": "https://username:password@host:port"
        }
    }
}
```

- `verify`: Verifies SSL certificates
- `timeout`: Maximum timeout (in seconds) for each request
- `max_retry`: Number of retry attempts per segment during M3U8 index download
- `proxy`: Proxy configuration for HTTP/HTTPS requests
  * Set to empty string `""` to disable proxies (default)
  * Example with authentication:
    ```json
    "proxy": {
        "http": "http://username:password@host:port",
        "https": "https://username:password@host:port"
    }
    ```
  * Example without authentication:
    ```json
    "proxy": {
        "http": "http://host:port",
        "https": "https://host:port"
    }
    ```
</details>

<details>
<summary>📥 M3U8_DOWNLOAD Settings</summary>

```json
{
    "M3U8_DOWNLOAD": {
        "tqdm_delay": 0.01,
        "default_video_workser": 12,
        "default_audio_workser": 12,
        "segment_timeout": 8,
        "download_audio": true,
        "merge_audio": true,
        "specific_list_audio": [
            "ita"
        ],
        "download_subtitle": true,
        "merge_subs": true,
        "specific_list_subtitles": [
            "ita",
            "eng"
        ],
        "cleanup_tmp_folder": true
    }
}
```

#### Performance Settings
- `tqdm_delay`: Delay between progress bar updates
- `default_video_workser`: Number of threads for video download
  * Can be changed with `--default_video_worker <number>`
- `default_audio_workser`: Number of threads for audio download
  * Can be changed with `--default_audio_worker <number>`
- `segment_timeout`: Timeout for downloading individual segments

#### Audio Settings
- `download_audio`: Whether to download audio tracks
- `merge_audio`: Whether to merge audio with video
- `specific_list_audio`: List of audio languages to download
  * Can be changed with `--specific_list_audio ita,eng`

#### Subtitle Settings
- `download_subtitle`: Whether to download subtitles
- `merge_subs`: Whether to merge subtitles with video
- `specific_list_subtitles`: List of subtitle languages to download
  * Can be changed with `--specific_list_subtitles ita,eng`

#### Cleanup
- `cleanup_tmp_folder`: Remove temporary .ts files after download
</details>

<details>
<summary>🌍 Available Language Codes</summary>

| European        | Asian           | Middle Eastern  | Others          |
|-----------------|-----------------|-----------------|-----------------|
| ita - Italian   | chi - Chinese   | ara - Arabic    | eng - English   |
| spa - Spanish   | jpn - Japanese  | heb - Hebrew    | por - Portuguese|
| fre - French    | kor - Korean    | tur - Turkish   | fil - Filipino  |
| ger - German    | hin - Hindi     |                 | ind - Indonesian|
| rus - Russian   | mal - Malayalam |                 | may - Malay     |
| swe - Swedish   | tam - Tamil     |                 | vie - Vietnamese|
| pol - Polish    | tel - Telugu    |                 |                 |
| ukr - Ukrainian | tha - Thai      |                 |                 |
</details>

<details>
<summary>🎥 M3U8_CONVERSION Settings</summary>

```json
{
    "M3U8_CONVERSION": {
        "use_codec": false,
        "use_vcodec": true,
        "use_acodec": true,
        "use_bitrate": true,
        "use_gpu": false,
        "default_preset": "ultrafast"
    }
}
```

#### Basic Settings
- `use_codec`: Use specific codec settings
- `use_vcodec`: Use specific video codec
- `use_acodec`: Use specific audio codec
- `use_bitrate`: Apply bitrate settings
- `use_gpu`: Enable GPU acceleration (if available)
- `default_preset`: FFmpeg encoding preset

#### Encoding Presets
The `default_preset` configuration can be set to:
- `ultrafast`: Extremely fast conversion but larger file size
- `superfast`: Very fast with good quality/size ratio
- `veryfast`: Fast with good compression
- `faster`: Optimal balance for most users
- `fast`: Good compression, moderate time
- `medium`: FFmpeg default setting
- `slow`: High quality, slower process
- `slower`: Very high quality, slow process
- `veryslow`: Maximum quality, very slow process

#### GPU Acceleration
When `use_gpu` is enabled, supports:
- NVIDIA: NVENC 
- AMD: AMF
- Intel: QSV

Note: Requires updated drivers and FFmpeg with hardware acceleration support.
</details>

<details>
<summary>🔍 M3U8_PARSER Settings</summary>

```json
{
    "M3U8_PARSER": {
        "force_resolution": "Best",
        "get_only_link": false
    }
}
```

#### Resolution Options
- `force_resolution`: Choose video resolution:
  * `"Best"`: Highest available resolution
  * `"Worst"`: Lowest available resolution
  * `"720p"`: Force 720p resolution
  * Specific resolutions:
    - 1080p (1920x1080)
    - 720p (1280x720)
    - 480p (640x480)
    - 360p (640x360)
    - 320p (480x320)
    - 240p (426x240)
    - 240p (320x240)
    - 144p (256x144)

#### Link Options
- `get_only_link`: Return M3U8 playlist/index URL instead of downloading
</details>

# Global Search

<details>
<summary>🔍 Feature Overview</summary>

You can now search across multiple streaming sites at once using the Global Search feature. This allows you to find content more efficiently without having to search each site individually.
</details>

<details>
<summary>🎯 Search Options</summary>

When using Global Search, you have three ways to select which sites to search:

1. **Search all sites** - Searches across all available streaming sites
2. **Search by category** - Group sites by their categories (movies, series, anime, etc.)
3. **Select specific sites** - Choose individual sites to include in your search
</details>

<details>
<summary>📝 Navigation and Selection</summary>

After performing a search:

1. Results are displayed in a consolidated table showing:
   - Title
   - Media type (movie, TV series, etc.)
   - Source site

2. Select an item by number to view details or download

3. The system will automatically use the appropriate site's API to handle the download
</details>

<details>
<summary>⌨️ Command Line Arguments</summary>

The Global Search can be configured from the command line:

- `--global` - Perform a global search across multiple sites.
- `-s`, `--search` - Specify the search terms.
</details>

# Examples of terminal usage

```bash
# Change video and audio workers
python test_run.py --default_video_worker 8 --default_audio_worker 8

# Set specific languages
python test_run.py --specific_list_audio ita,eng --specific_list_subtitles eng,spa

# Keep console open after download
python test_run.py --not_close true

# Use global search
python test_run.py --global -s "cars"
```

# Docker

<details>
<summary>🐳 Basic Setup</summary>

Build the image:
```
docker build -t streaming-community-api .
```

Run the container with Cloudflare DNS for better connectivity:
```
docker run -it --dns 1.1.1.1 -p 8000:8000 streaming-community-api
```
</details>

<details>
<summary>💾 Custom Storage Location</summary>

By default the videos will be saved in `/app/Video` inside the container. To save them on your machine:

```
docker run -it --dns 9.9.9.9 -p 8000:8000 -v /path/to/download:/app/Video streaming-community-api
```
</details>

<details>
<summary>🛠️ Quick Setup with Make</summary>

Inside the Makefile (install `make`) are already configured two commands to build and run the container:

```
make build-container

# set your download directory as ENV variable
make LOCAL_DIR=/path/to/download run-container
```

The `run-container` command mounts also the `config.json` file, so any change to the configuration file is reflected immediately without having to rebuild the image.
</details>

# Telegram Usage

<details>
<summary>⚙️ Basic Configuration</summary>

The bot was created to replace terminal commands and allow interaction via Telegram. Each download runs within a screen session, enabling multiple downloads to run simultaneously.

To run the bot in the background, simply start it inside a screen session and then press Ctrl + A, followed by D, to detach from the session without stopping the bot.

Command Functions:

🔹 /start – Starts a new search for a download. This command performs the same operations as manually running the script in the terminal with test_run.py.

🔹 /list – Displays the status of active downloads, with options to:

Stop an incorrect download using /stop <ID>.

View the real-time output of a download using /screen <ID>.

⚠ Warning: If a download is interrupted, incomplete files may remain in the folder specified in config.json. These files must be deleted manually to avoid storage or management issues.

🛠 Configuration: Currently, the bot's settings are stored in the config.json file, which is located in the same directory as the telegram_bot.py script.

## .env Example:

You need to create an .env file and enter your Telegram token and user ID to authorize only one user to use it

```
TOKEN_TELEGRAM=IlTuo2131TOKEN$12D3Telegram
AUTHORIZED_USER_ID=12345678
DEBUG=False
```
</details>

<details>
<summary>📥 Dependencies & Launch</summary>

Install dependencies:
```bash
pip install -r requirements.txt
```

Start the bot (from /StreamingCommunity/TelegramHelp):
```bash
python3 telegram_bot.py
```
</details>

# Tutorials

- [Windows Tutorial](https://www.youtube.com/watch?v=mZGqK4wdN-k)
- [Linux Tutorial](https://www.youtube.com/watch?v=0qUNXPE_mTg)
- [Pypy Tutorial](https://www.youtube.com/watch?v=C6m9ZKOK0p4)
- [Compiled .exe Tutorial](https://www.youtube.com/watch?v=pm4lqsxkTVo)

# To Do

- To Finish [website API](https://github.com/Arrowar/StreamingCommunity/tree/test_gui_1)
- To finish [website API 2](https://github.com/hydrosh/StreamingCommunity/tree/test_gui_1)

## Useful Project

### 🎯 [Unit3Dup](https://github.com/31December99/Unit3Dup)
Bot in Python per la generazione e l'upload automatico di torrent su tracker basati su Unit3D.


### 🇮🇹 [MammaMia](https://github.com/UrloMythus/MammaMia)
Addon per Stremio che consente lo streaming HTTPS di film, serie, anime e TV in diretta in lingua italiana.

### 🧩 [streamingcommunity-unofficialapi](https://github.com/Blu-Tiger/streamingcommunity-unofficialapi)
API non ufficiale per accedere ai contenuti del sito italiano StreamingCommunity.

### 🎥 [stream-buddy](https://github.com/Bbalduzz/stream-buddy)
Tool per guardare o scaricare film dalla piattaforma StreamingCommunity.

# Disclaimer

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.
