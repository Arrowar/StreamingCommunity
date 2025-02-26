<p align="center">
  <img src="https://i.ibb.co/v6RnT0wY/s2.jpg" alt="Project Logo" width="700"/>
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

- 🔄 [Update Domains](#update-domains)
- 🛠️ [Installation](#installation)
    - 📦 [PyPI Installation](#1-pypi-installation)
    - 🔄 [Automatic Installation](#2-automatic-installation)
    - 🔧 [Binary Location](#binary-location)
    - 📝 [Manual Installation](#3-manual-installation)
        - 💻 [Win 7](https://github.com/Ghost6446/StreamingCommunity_api/wiki/Installation#win-7)
        - 📱 [Termux](https://github.com/Ghost6446/StreamingCommunity_api/wiki/Termux)
- ⚙️ [Configuration](#configuration)
    - 🔧 [Default](#default-settings)
    - 📩 [Request](#requests-settings)
    - 📥 [Download](#m3u8_download-settings)
    - 🔍 [Parser](#m3u8_parser-settings)
- 📝 [Command](#command)
- 💻 [Examples of terminal](#examples-of-terminal-usage)
- 🐳 [Docker](#docker)
- 📝 [Telegram Usage](#telegram-usage)
- 🎓 [Tutorial](#tutorials)
- 📝 [To do](#to-do)
- 💬 [Support](#support)
- 🤝 [Contribute](#contributing)
- ⚠️ [Disclaimer](#disclaimer)
- ⚡ [Contributors](#contributors)

# Installation

<p align="center">
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_win.exe" style="margin: 0 20px;">
    <img src="https://img.shields.io/badge/-Windows-blue.svg?style=for-the-badge&logo=windows" alt="Windows">
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_mac" style="margin: 0 20px;">
    <img src="https://img.shields.io/badge/-macOS-black.svg?style=for-the-badge&logo=apple" alt="macOS">
  </a>
  <a href="https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux" style="margin: 0 20px;">
    <img src="https://img.shields.io/badge/-Linux-orange.svg?style=for-the-badge&logo=linux" alt="Linux">
  </a>
</p>


## 1. PyPI Installation

Install directly from PyPI:

```bash
pip install StreamingCommunity
```

### Creating a Run Script

Create `run_streaming.py`:

```python
from StreamingCommunity.run import main

if __name__ == "__main__":
    main()
```

Run the script:
```bash
python run_streaming.py
```

### Updating via PyPI

```bash
pip install --upgrade StreamingCommunity
```

## 2. Automatic Installation

### Supported Operating Systems 💿

| OS              | Automatic Installation Support |
|:----------------|:------------------------------:|
| Windows 10/11   |              ✔️              |
| Windows 7       |              ❌              |
| Debian Linux    |              ✔️              |
| Arch Linux      |              ✔️              |
| CentOS Stream 9 |              ✔️              |
| FreeBSD         |              ⏳              |
| MacOS           |              ✔️              |
| Termux          |              ❌              |

### Installation Steps

#### On Windows:

```powershell
.\Installer\win_install.bat
```

#### On Linux/MacOS/BSD:

```bash
sudo chmod +x Installer/unix_install.sh && ./Installer/unix_install.sh
```

### Usage

#### On Windows:

```powershell
python .\test_run.py
```

or

```powershell
source .venv/bin/activate && python test_run.py && deactivate
```

#### On Linux/MacOS/BSD:

```bash
./test_run.py
```

## Binary Location

### Default Locations
- **Windows**: `C:\binary`
- **MacOS**: `~/Applications/binary`
- **Linux**: `~/.local/bin/binary`

You can customize these locations by following these steps for your operating system:

#### Windows
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

#### MacOS
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

#### Linux
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

> [!IMPORTANT]
> After moving the binary folder, ensure that all executables (ffmpeg, ffprobe, ffplay) are present in the new location and have the correct permissions:
> - Windows: `.exe` extensions required
> - MacOS/Linux: Ensure files have execute permissions (`chmod +x filename`)

## 3. Manual Installation

### Requirements 📋

Prerequisites:
* [Python](https://www.python.org/downloads/) > 3.8
* [FFmpeg](https://www.gyan.dev/ffmpeg/builds/)

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Usage

#### On Windows:

```powershell
python test_run.py
```

#### On Linux/MacOS:

```bash
python3 test_run.py
```

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

# Configuration

You can change some behaviors by tweaking the configuration file.

The configuration file is divided into several main sections:

## DEFAULT Settings

```json
{
    "DEFAULT": {
        "debug": false,
        "show_message": true,
        "clean_console": true,
        "show_trending": true,
        "use_api": true,
        "not_close": false,
        "telegram_bot": false
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

## OUT_FOLDER Settings

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

- `root_path`: Directory where all videos will be saved

  ### Path examples:
  * Windows: `C:\\MyLibrary\\Folder` or `\\\\MyServer\\MyLibrary` (if you want to use a network folder)
  * Linux/MacOS: `Desktop/MyLibrary/Folder`
    <br/><br/>

- `movie_folder_name`: The name of the subdirectory where movies will be stored
  * Can be changed from terminal with `--movie_folder_name`
    <br/><br/>

- `serie_folder_name`: The name of the subdirectory where TV series will be stored
  * Can be changed from terminal with `--serie_folder_name`
    <br/><br/>

- `anime_folder_name`: The name of the subdirectory where anime will be stored
  * Can be changed from terminal with `--anime_folder_name`
    <br/><br/>

- `map_episode_name`: Template for episode filenames

  ### Episode name usage:

  You can choose different vars:
  * `%(tv_name)` : Is the name of TV Show
  * `%(season)` : Is the number of the season
  * `%(episode)` : Is the number of the episode
  * `%(episode_name)` : Is the name of the episode
  * Can be changed from terminal with `--map_episode_name`
    <br><br>

- `add_siteName`: If set to true, appends the site_name to the root path before the movie and serie folders
  * Can be changed from terminal with `--add_siteName true/false`
    <br/><br/>

## QBIT_CONFIG Settings

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

## REQUESTS Settings

```json
{
    "REQUESTS": {
        "verify": false,
        "timeout": 20,
        "max_retry": 8
    }
}
```

- `verify`: Verifies SSL certificates
- `timeout`: Maximum timeout (in seconds) for each request
- `max_retry`: Number of retry attempts per segment during M3U8 index download

## M3U8_DOWNLOAD Settings

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

- `tqdm_delay`: Delay between progress bar updates
- `default_video_workser`: Number of threads for video download
  * Can be changed from terminal with `--default_video_worker <number>`
    <br/><br/>

- `default_audio_workser`: Number of threads for audio download
  * Can be changed from terminal with `--default_audio_worker <number>`
    <br/><br/>

- `segment_timeout`: Timeout for downloading individual segments
- `download_audio`: Whether to download audio tracks
- `merge_audio`: Whether to merge audio with video
- `specific_list_audio`: List of audio languages to download
  * Can be changed from terminal with `--specific_list_audio ita,eng`
    <br/><br/>

- `download_subtitle`: Whether to download subtitles
- `merge_subs`: Whether to merge subtitles with video
- `specific_list_subtitles`: List of subtitle languages to download
  * Can be changed from terminal with `--specific_list_subtitles ita,eng`
    <br/><br/>

- `cleanup_tmp_folder`: Remove temporary .ts files after download

## Available Language Codes

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

## M3U8_CONVERSION Settings

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

- `use_codec`: Use specific codec settings
- `use_vcodec`: Use specific video codec
- `use_acodec`: Use specific audio codec
- `use_bitrate`: Apply bitrate settings
- `use_gpu`: Enable GPU acceleration (if available)
- `default_preset`: FFmpeg encoding preset (ultrafast, fast, medium, slow, etc.)

### Advanced M3U8 Conversion Options

The software supports various advanced encoding options via FFmpeg:

#### Encoding Presets
The `default_preset` configuration can be set to one of the following values:
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
When `use_gpu` is enabled, the system will use available hardware acceleration:
- NVIDIA: NVENC 
- AMD: AMF
- Intel: QSV

You need to have updated drivers and FFmpeg compiled with hardware acceleration support.

## M3U8_PARSER Settings

```json
{
    "M3U8_PARSER": {
        "force_resolution": "Best",
        "get_only_link": false
    }
}
```

- `force_resolution`: Choose the video resolution for downloading:
    * `"Best"`: Highest available resolution
    * `"Worst"`: Lowest available resolution
    * `"720p"`: Force 720p resolution
    * Or specify one of these resolutions:
        - 1080p (1920x1080)
        - 720p (1280x720)
        - 480p (640x480)
        - 360p (640x360)
        - 320p (480x320)
        - 240p (426x240)
        - 240p (320x240)
        - 144p (256x144)

- `get_only_link`: Return M3U8 playlist/index URL instead of downloading

## SITE_EXTRA Settings

```json
{
    "SITE_EXTRA": {
        "ddlstreamitaly": {
            "ips4_device_key": "",
            "ips4_member_id": "",
            "ips4_login_key": ""
        }
    }
}
```

- Site-specific configuration for `ddlstreamitaly`:
  - `ips4_device_key`: Device key for authentication
  - `ips4_member_id`: Member ID for authentication
  - `ips4_login_key`: Login key for authentication
  
## Update Domains

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

# COMMAND

- Download a specific season by entering its number.
  *  **Example:** `1` will download *Season 1* only.

-  Use the wildcard `*` to download every available season.
   * **Example:** `*` will download all seasons in the series.

- Specify a range of seasons using a hyphen `-`.
   * **Example:** `1-2` will download *Seasons 1 and 2*.

- Enter a season number followed by `-*` to download from that season to the end.
  * **Example:** `3-*` will download from *Season 3* to the final season.

# Examples of terminal usage

```bash
# Change video and audio workers
python test_run.py --default_video_worker 8 --default_audio_worker 8

# Set specific languages
python test_run.py --specific_list_audio ita,eng --specific_list_subtitles eng,spa

# Keep console open after download
python test_run.py --not_close true
```

# Docker

You can run the script in a docker container, to build the image just run

```
docker build -t streaming-community-api .
```

and to run it use

```
docker run -it -p 8000:8000 streaming-community-api
```

By default the videos will be saved in `/app/Video` inside the container, if you want to to save them in your machine instead of the container just run

```
docker run -it -p 8000:8000 -v /path/to/download:/app/Video streaming-community-api
```

### Docker quick setup with Make

Inside the Makefile (install `make`) are already configured two commands to build and run the container:

```
make build-container

# set your download directory as ENV variable
make LOCAL_DIR=/path/to/download run-container
```

The `run-container` command mounts also the `config.json` file, so any change to the configuration file is reflected immediately without having to rebuild the image.

# Telegram Usage

## Configuration

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

## Install Python Dependencies

```bash
pip install -r requirements.txt
```

## On Linux/MacOS:

Start the bot from the folder /StreamingCommunity/TelegramHelp

```bash
python3 telegram_bot.py
```

# Tutorials

- [Windows Tutorial](https://www.youtube.com/watch?v=mZGqK4wdN-k)
- [Linux Tutorial](https://www.youtube.com/watch?v=0qUNXPE_mTg)
- [Pypy Tutorial](https://www.youtube.com/watch?v=C6m9ZKOK0p4)
- [Compiled .exe Tutorial](https://www.youtube.com/watch?v=pm4lqsxkTVo)

# To Do

- To Finish [website API](https://github.com/Arrowar/StreamingCommunity/tree/test_gui_1)
- To finish [website API 2](https://github.com/hydrosh/StreamingCommunity/tree/test_gui_1)

# Contributing

Contributions are welcome! Steps:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request


# Disclaimer

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

## Contributors

<a href="https://github.com/Arrowar/StreamingCommunity/graphs/contributors" alt="View Contributors">
  <img src="https://contrib.rocks/image?repo=Arrowar/StreamingCommunity&max=1000&columns=10" alt="Contributors" />
</a>
