<div align="center">

<img src="https://i.postimg.cc/Y9t2XgB1/z562m3.png" alt="StreamingCommunity Logo" width="110" style="background: transparent;"><br><br>

[![PyPI Version](https://img.shields.io/pypi/v/streamingcommunity?logo=pypi&logoColor=white&labelColor=2d3748&color=3182ce&style=for-the-badge)](https://pypi.org/project/streamingcommunity/)
[![Last Commit](https://img.shields.io/github/last-commit/Arrowar/StreamingCommunity?logo=git&logoColor=white&labelColor=2d3748&color=805ad5&style=for-the-badge)](https://github.com/Arrowar/StreamingCommunity/commits)
[![Sponsor](https://img.shields.io/badge/💖_Sponsor-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white&labelColor=2d3748)](https://ko-fi.com/arrowar)

[![Windows](https://img.shields.io/badge/🪟_Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_win.exe)
[![macOS](https://img.shields.io/badge/🍎_macOS-000000?style=for-the-badge&logo=apple&logoColor=white&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_mac)
[![Linux latest](https://img.shields.io/badge/🐧_Linux_latest-FCC624?style=for-the-badge&logo=linux&logoColor=black&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux_latest)
[![Linux 22.04](https://img.shields.io/badge/🐧_Linux_22.04-FCC624?style=for-the-badge&logo=linux&logoColor=black&labelColor=2d3748)](https://github.com/Arrowar/StreamingCommunity/releases/latest/download/StreamingCommunity_linux_previous)

*⚡ **Quick Start:** `pip install StreamingCommunity && StreamingCommunity`*

📺 **[Services](.github/doc/site.md)** - See all supported streaming platforms

</div>

## 📖 Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [DNS Configuration](#dns-configuration)
- [Downloaders](#downloaders)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Global Search](#global-search)
- [Advanced Features](#advanced-features)
- [Docker](#docker)
- [Related Projects](#related-projects)

---

## Installation

### Manual Clone
```bash
git clone https://github.com/Arrowar/StreamingCommunity.git
cd StreamingCommunity
pip install -r requirements.txt
python test_run.py
```

### Dependencies
```bash
# Windows
pip install -r requirements.txt

# Linux/MacOS  
pip3 install -r requirements.txt

# Android Termux
pip install -r requirements-termux.txt
```

### Update
```bash
python update.py
```

### Additional Documentation
- 📝 [Login Guide](.github/doc/login.md) - Authentication for supported services

---

## Quick Start

```bash
# If installed via PyPI
StreamingCommunity

# If cloned manually
python test_run.py
```

---

## DNS Configuration

**Required for optimal functionality and reliability.**

Use one of these DNS providers:

- **Cloudflare DNS**: `1.1.1.1` - [Setup guide](https://developers.cloudflare.com/1.1.1.1/setup/)
- **Quad9 DNS**: `9.9.9.9` - [Setup guide](https://quad9.net/)

---

## Downloaders

| Type | Description | Example |
|------|-------------|---------|
| **HLS** | HTTP Live Streaming (m3u8) | [View example](./Test/Downloads/HLS.py) |
| **MP4** | Direct MP4 download | [View example](./Test/Downloads/MP4.py) |
| **DASH** | MPEG-DASH with DRM bypass* | [View example](./Test/Downloads/DASH.py) |
| **MEGA** | MEGA.nz downloads | [View example](./Test/Downloads/MEGA.py) |

**\*DASH with DRM bypass:** Requires a valid L3 CDM (Content Decryption Module). This project does not provide or facilitate obtaining CDMs. Users must ensure compliance with applicable laws.

---

## Configuration

Key configuration parameters in `config.json`:

### Output Directories
```json
{
    "OUT_FOLDER": {
        "root_path": "Video",
        "movie_folder_name": "Movie",
        "serie_folder_name": "Serie",
        "anime_folder_name": "Anime",
        "map_episode_name": "%(episode_name) S%(season)E%(episode)",
        "add_siteName": false
    }
}
```

- **`root_path`**: Base directory where videos are saved
  - Windows: `C:\\MyLibrary\\Folder` or `\\\\MyServer\\Share`
  - Linux/MacOS: `Desktop/MyLibrary/Folder`

- **`movie_folder_name`**: Subfolder name for movies (default: `"Movie"`)
- **`serie_folder_name`**: Subfolder name for TV series (default: `"Serie"`)
- **`anime_folder_name`**: Subfolder name for anime (default: `"Anime"`)

- **`map_episode_name`**: Episode filename template
  - `%(tv_name)`: TV Show name
  - `%(season)`: Season number (zero-padded)
  - `%(episode)`: Episode number (zero-padded)
  - `%(episode_name)`: Episode title
  - Example: `"%(episode_name) S%(season)E%(episode)"` → `"Pilot S01E01"`

- **`add_siteName`**: Append site name to root path (default: `false`)

### M3U8 Download Settings
```json
{
    "M3U8_DOWNLOAD": {
        "thread_count": 12,
        "retry_count": 40,
        "concurrent_download": true,
        "max_speed": "30MB",
        "check_segments_count": true,
        "select_video": "res=.*1080.*:for=best",
        "select_audio": "lang='ita|Ita':for=all",
        "select_subtitle": "lang='ita|eng|Ita|Eng':for=all",
        "cleanup_tmp_folder": true
    }
}
```

#### Performance Settings
- **`thread_count`**: Number of parallel download threads (default: `12`)
- **`retry_count`**: Maximum retry attempts for failed segments (default: `40`)
- **`concurrent_download`**: Download video and audio simultaneously (default: `true`)
- **`max_speed`**: Speed limit per stream (e.g., `"30MB"`, `"10MB"`)
- **`check_segments_count`**: Verify segment count matches manifest (default: `true`)
- **`cleanup_tmp_folder`**: Remove temporary files after download (default: `true`)

#### Stream Selection

**- `select_video`**
```
OPTIONS: id=REGEX:lang=REGEX:name=REGEX:codecs=REGEX:res=REGEX:frame=REGEX:
         segsMin=number:segsMax=number:ch=REGEX:range=REGEX:url=REGEX:
         plistDurMin=hms:plistDurMax=hms:bwMin=int:bwMax=int:role=string:for=FOR

    for=FOR: Selection type - best (default), best[number], worst[number], all
```
```json
"select_video": "for=best"                                // Select best video
"select_video": "res=3840*:codecs=hvc1:for=best"          // Select 4K HEVC video
"select_video": "res=.*1080.*:for=best"                   // Select 1080p video
"select_video": "plistDurMin=1h20m30s:for=best"           // Duration > 1h 20m 30s
"select_video": "role=main:for=best"                      // Main video role
"select_video": "bwMin=800:bwMax=1000:for=best"           // Bandwidth 800-1000 Kbps
```

**- `select_audio`** 
```json
"select_audio": "for=all"                                 // Select all audio tracks
"select_audio": "lang=en:for=best"                        // Select best English audio
"select_audio": "lang='ja|en':for=best2"                  // Best 2 tracks (Japanese or English)
"select_audio": "lang='ita|Ita':for=all"                  // All Italian audio tracks
"select_audio": "role=main:for=best"                      // Main audio role
```

**- `select_subtitle`** 
```json
"select_subtitle": "for=all"                              // Select all subtitles
"select_subtitle": "name=English:for=all"                 // All subtitles containing "English"
"select_subtitle": "lang='ita|eng|Ita|Eng':for=all"       // Italian and English subtitles
"select_subtitle": "lang=en:for=best"                     // Best English subtitle
```

### M3U8 Conversion Settings
```json
{
    "M3U8_CONVERSION": {
        "use_gpu": false,
        "param_video": ["-c:v", "libx265", "-crf", "28", "-preset", "medium"],
        "param_audio": ["-c:a", "libopus", "-b:a", "128k"],
        "subtitle_disposition": true,
        "subtitle_disposition_language": ["forced-ita", "ita-forced"],
        "param_final": ["-c", "copy"],
        "extension": "mkv"
    }
}
```

- **`use_gpu`**: Enable hardware acceleration (default: `false`)
- **`param_video`**: FFmpeg video encoding parameters
  - Example: `["-c:v", "libx265", "-crf", "28", "-preset", "medium"]` (H.265/HEVC encoding)
- **`param_audio`**: FFmpeg audio encoding parameters
  - Example: `["-c:a", "libopus", "-b:a", "128k"]` (Opus audio at 128kbps)
- **`subtitle_disposition`**: Automatically set default subtitle track (default: `true`)
- **`subtitle_disposition_language`**: Languages to mark as default/forced
  - Example: `["forced-ita", "ita-forced"]` for Italian forced subtitles
- **`param_final`**: Final FFmpeg parameters (default: `["-c", "copy"]` for stream copy)
- **`extension`**: Output file format (`"mkv"` or `"mp4"`)

### Request Settings
```json
{
    "REQUESTS": {
        "verify": false,
        "timeout": 30,
        "max_retry": 10
    }
}
```

- **`verify`**: Enable SSL certificate verification (default: `false`)
- **`timeout`**: Request timeout in seconds (default: `30`)
- **`max_retry`**: Maximum retry attempts for failed requests (default: `10`)

### Domain Management
```json
{
    "DEFAULT": {
        "show_message": false,
        "show_device_info": false,
        "fetch_domain_online": true
    }
}
```

- **`show_message`**: Display debug messages (default: `false`)
- **`show_device_info`**: Display device information (default: `false`)
- **`fetch_domain_online`**: Automatically fetch latest domains from GitHub (default: `true`)

---

## Usage Examples

### Basic Commands
```bash
# Show help and available sites
python test_run.py -h

# Search and download
python test_run.py --site streamingcommunity --search "interstellar"

# Auto-download first result
python test_run.py --site streamingcommunity --search "interstellar" --auto-first

# Use site by index
python test_run.py --site 0 --search "interstellar"
```

### Advanced Options
```bash
# Keep console open
python test_run.py --not_close true
```

---

## Global Search

Search across multiple streaming sites simultaneously:

```bash
# Global search
python test_run.py --global -s "cars"

# Search by category
python test_run.py --category 1    # Anime
python test_run.py --category 2    # Movies & Series
python test_run.py --category 3    # Series only
```

Results display title, media type, and source site in a consolidated table.

---

## Advanced Features

### Hook System

Execute custom scripts before/after downloads. Configure in `config.json`:

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

#### Hook Configuration Options

- **`name`**: Descriptive name for the hook
- **`type`**: Script type - `python`, `bash`, `sh`, `bat`, `cmd`
- **`path`**: Path to script file (alternative to `command`)
- **`command`**: Inline command to execute (alternative to `path`)
- **`args`**: List of arguments passed to the script
- **`env`**: Additional environment variables as key-value pairs
- **`cwd`**: Working directory for script execution (supports `~` and environment variables)
- **`os`**: Optional OS filter - `["windows"]`, `["darwin"]` (macOS), `["linux"]`, or combinations
- **`timeout`**: Maximum execution time in seconds (hook fails if exceeded)
- **`enabled`**: Enable/disable the hook without removing configuration
- **`continue_on_error`**: If `false`, stops execution when hook fails

#### Hook Types

- **Python hooks**: Run with current Python interpreter
- **Bash/sh hooks**: Execute via `bash`/`sh` on macOS/Linux
- **Bat/cmd hooks**: Execute via `cmd /c` on Windows
- **Inline commands**: Use `command` instead of `path` for simple one-liners

Hooks are automatically executed by `run.py` before (`pre_run`) and after (`post_run`) the main execution flow.

---

## Docker

### Basic Setup
```bash
# Build image
docker build -t streaming-community-api .

# Run with Cloudflare DNS
docker run -d --name streaming-community --dns 1.1.1.1 -p 8000:8000 streaming-community-api
```

### Custom Storage Location
```bash
docker run -d --dns 9.9.9.9 -p 8000:8000 -v /your/path:/app/Video streaming-community-api
```

### Using Make
```bash
make build-container
make LOCAL_DIR=/your/path run-container
```

---

## TODO

- [ ] Improve GUI - Enhance the graphical user interface
- [ ] Add Crunchyroll subtitle synchronization

---

## Related Projects

- **[Unit3Dup](https://github.com/31December99/Unit3Dup)** - Torrent automation for Unit3D trackers
- **[MammaMia](https://github.com/UrloMythus/MammaMia)** - Stremio addon for Italian streaming

---

## Disclaimer
>
> This software is provided strictly for **educational and research purposes only**. The author and contributors:
>
> - **DO NOT** assume any responsibility for illegal or unauthorized use of this software
> - **DO NOT** encourage, promote, or support the download of copyrighted content without proper authorization
> - **DO NOT** provide, include, or facilitate obtaining any DRM circumvention tools, CDM modules, or decryption keys
> - **DO NOT** endorse piracy or copyright infringement in any form
>
> ### User Responsibilities
>
> By using this software, you agree that:
>
> 1. **You are solely responsible** for ensuring your use complies with all applicable local, national, and international laws and regulations
> 2. **You must have legal rights** to access and download any content you process with this software
> 3. **You will not use** this software to circumvent DRM, access unauthorized content, or violate copyright laws
> 4. **You understand** that downloading copyrighted content without permission is illegal in most jurisdictions
>
> ### No Warranty
>
> This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.
>
> **If you do not agree with these terms, do not use this software.**

---

<div align="center">

**Made with ❤️ for streaming lovers**

*If you find this project useful, consider starring it! ⭐*

</div>