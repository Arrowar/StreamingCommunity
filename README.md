<div align="center">

## 📊 Project Status & Info
[![PyPI Version](https://img.shields.io/pypi/v/streamingcommunity?logo=pypi&logoColor=white&labelColor=2d3748&color=3182ce&style=for-the-badge)](https://pypi.org/project/streamingcommunity)
[![Last Commit](https://img.shields.io/github/last-commit/Arrowar/StreamingCommunity?logo=git&logoColor=white&labelColor=2d3748&color=805ad5&style=for-the-badge)](https://github.com/Arrowar/StreamingCommunity/commits)
[![Issues](https://img.shields.io/github/issues/Arrowar/StreamingCommunity?logo=github&logoColor=white&labelColor=2d3748&color=ed8936&style=for-the-badge)](https://github.com/Arrowar/StreamingCommunity/issues)
[![License](https://img.shields.io/github/license/Arrowar/StreamingCommunity?logo=gnu&logoColor=white&labelColor=2d3748&color=e53e3e&style=for-the-badge)](https://github.com/Arrowar/StreamingCommunity/blob/main/LICENSE)

## 💝 Support the Project

[![Donate PayPal](https://img.shields.io/badge/💳_Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white&labelColor=2d3748)](https://www.paypal.com/donate/?hosted_button_id=UXTWMT8P6HE2C)
## 🚀 Download & Install

[![Windows](https://img.shields.io/badge/🪟_Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_win.exe)
[![macOS](https://img.shields.io/badge/🍎_macOS-000000?style=for-the-badge&logo=apple&logoColor=white&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_mac)
[![Linux latest](https://img.shields.io/badge/🐧_Linux_latest-FCC624?style=for-the-badge&logo=linux&logoColor=black&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux_latest)
[![Linux 22.04](https://img.shields.io/badge/🐧_Linux_22.04-FCC624?style=for-the-badge&logo=linux&logoColor=black&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux_previous)
---

*⚡ **Quick Start:** `pip install streamingcommunity` or download the executable for your platform above*

</div>

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
- 🧩 [Hook/Plugin System](#hookplugin-system)
</details>

<details>
<summary>ℹ️ Help & Support</summary>

- 🎓 [Tutorial](#tutorials)
- 📝 [To do](#to-do)
- ⚠️ [Disclaimer](#disclaimer)
</details>

# Installation

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
from StreamingCommunity import HLS_Downloader

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
from StreamingCommunity import MP4_downloader

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
from StreamingCommunity import TOR_downloader

# Initialize torrent client
client = TOR_downloader()

# Add magnet link
client.add_magnet_link("magnet:?xt=urn:btih:example_hash&dn=example_name", save_path=".")

# Start download
client.start_download()
```

See [Torrent example](./Test/Download/TOR.py) for complete usage.
</details>

<details>
<summary>🎞️ DASH Downloader</summary>

```python
license_url = "https://example.com/stream.mpd"
mpd_url = "https://example.com/get_license"

dash_process = DASH_Downloader(
    cdm_device=get_wvd_path(),
    license_url=license_url,
    mpd_url=mpd_url,
    output_path="output.mp4",
)
dash_process.parse_manifest()

if dash_process.download_and_decrypt():
    dash_process.finalize_output()

dash_process.get_status()
```

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

There are two ways to manage the domains for the supported websites:

### 1. Online Domain Fetching (Recommended)

Set `fetch_domain_online` to `true` in your `config.json`:

```json
{
   "DEFAULT": {
      "fetch_domain_online": true
   }
}
```

This will:
- Download the latest domains from the GitHub repository
- Automatically save them to a local `domains.json` file
- Ensure you always have the most up-to-date streaming site domains

### 2. Local Domain Configuration

Set `fetch_domain_online` to `false` to use a local configuration:

```json
{
   "DEFAULT": {
      "fetch_domain_online": false
   }
}
```

Then create a `domains.json` file in the root directory with your domain configuration:

```json
{
   "altadefinizione": {
       "domain": "si",
       "full_url": "https://altadefinizione.si/"
   },
   "streamingcommunity": {
       "domain": "best",
       "full_url": "https://streamingcommunity.best/"
   }
}
```

### 3. Automatic Fallback

If online fetching fails, the script will automatically attempt to use the local `domains.json` file as a fallback, ensuring maximum reliability.

#### 💡 Adding a New Site
If you want to request a new site to be added to the repository, message us on the Discord server!

</details>

## Hook/Plugin System

<details>
<summary>🧩 Run custom scripts before/after the main execution</summary>

Define pre/post hooks in `config.json` under the `HOOKS` section. Supported types:

- **python**: runs `script.py` with the current Python interpreter
- **bash/sh**: runs via `bash`/`sh` on macOS/Linux
- **bat/cmd**: runs via `cmd /c` on Windows
- Inline **command**: use `command` instead of `path`

Sample configuration:

```json
{
  "HOOKS": {
    "pre_run": [
      {
        "name": "prepare-env",
        "type": "python",
        "path": "scripts/prepare.py",
        "args": ["--clean"],
        "env": {"MY_FLAG": "1"},
        "cwd": "~",
        "os": ["linux", "darwin"],
        "timeout": 60,
        "enabled": true,
        "continue_on_error": true
      }
    ],
    "post_run": [
      {
        "name": "notify",
        "type": "bash",
        "command": "echo 'Download completed'"
      }
    ]
  }
}
```

Notes:

- **os**: optional OS filter (`windows`, `darwin` (`darwin` is used for MacOS), `linux`).
- **args**: list of arguments passed to the script.
- **env**: additional environment variables.
- **cwd**: working directory for the script; supports `~` and environment variables.
- **continue_on_error**: if `false`, the app stops when the hook fails.
- **timeout**: in seconds; when exceeded the hook fails.

Hooks are executed automatically by `run.py` before (`pre_run`) and after (`post_run`) the main execution.

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
        "show_trending": true,
        "fetch_domain_online": true,
        "telegram_bot": false,
        "validate_github_config": false
    }
}
```

- `debug`: Enables debug logging
- `show_message`: Displays informational messages
- `show_trending`: Shows trending content
- `fetch_domain_online`: If true, downloads domains from GitHub repository and saves to local file; if false, uses existing local domains.json file
- `telegram_bot`: Enables Telegram bot integration
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
        "specific_list_audio": [
            "ita"
        ],
        "download_subtitle": true,
        "merge_subs": true,
        "specific_list_subtitles": [
            "ita",    // Specify language codes or use ["*"] to download all available subtitles
            "eng"
        ],
        "cleanup_tmp_folder": true,
        "get_only_link": false
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
- `specific_list_audio`: List of audio languages to download
  * Can be changed with `--specific_list_audio ita,eng`

#### Subtitle Settings
- `download_subtitle`: Whether to download subtitles
- `merge_subs`: Whether to merge subtitles with video
- `specific_list_subtitles`: List of subtitle languages to download
  * Use `["*"]` to download all available subtitles
  * Or specify individual languages like `["ita", "eng"]`
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
        "force_resolution": "Best"
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

#### Link options
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
# Run a specific site by name with a search term
python test_run.py --site streamingcommunity --search "interstellar"

# Run a specific site by numeric index (as shown in -h help)
python test_run.py --site 0 --search "interstellar"

# Auto-download the first result from search (requires --site and --search)
python test_run.py --site streamingcommunity --search "interstellar" --auto-first

# Show help (includes available sites by name and by index)
python test_run.py -h

# Change video and audio workers
python test_run.py --default_video_worker 8 --default_audio_worker 8

# Set specific languages
python test_run.py --specific_list_audio ita,eng --specific_list_subtitles eng,spa

# Keep console open after download
python test_run.py --not_close true

# Use global search
python test_run.py --global -s "cars"

# Select specific category
python test_run.py --category 1       # Search in anime category
python test_run.py --category 2       # Search in movies & series
python test_run.py --category 3       # Search in series
python test_run.py --category 4       # Search in torrent category

# If installed via pip, you can also use the entrypoint directly
streamingcommunity --site streamingcommunity --search "interstellar" --auto-first
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
docker run -d --name streaming-community --dns 1.1.1.1 -p 8000:8000 streaming-community-api
```

Tip CLI:
- To run the CLI inside the container, attach to the container and execute:
```
docker exec -it streaming-community python test_run.py
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

- [Windows](https://www.youtube.com/watch?v=mZGqK4wdN-k)
- [Linux](https://www.youtube.com/watch?v=0qUNXPE_mTg)
- [Pypy](https://www.youtube.com/watch?v=C6m9ZKOK0p4)
- [Compiled](https://www.youtube.com/watch?v=pm4lqsxkTVo)

## Useful Project

### 🎯 [Unit3Dup](https://github.com/31December99/Unit3Dup)
Bot in Python per la generazione e l'upload automatico di torrent su tracker basati su Unit3D.

### 🇮🇹 [MammaMia](https://github.com/UrloMythus/MammaMia)
Addon per Stremio che consente lo streaming HTTPS di film, serie, anime e TV in diretta in lingua italiana.

### 🧩 [streamingcommunity-unofficialapi](https://github.com/Blu-Tiger/streamingcommunity-unofficialapi)
API non ufficiale per accedere ai contenuti del sito italiano StreamingCommunity.

# Disclaimer

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

> **Note:** DASH downloads require a valid L3 CDM (Content Decryption Module) to proceed. This project does not provide, include, or facilitate obtaining any CDM. Users are responsible for ensuring compliance with all applicable laws and requirements regarding DRM and decryption modules.
