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
        "map_episode_name": "E%(episode)_%(episode_name)",
        "add_siteName": false
    }
}
```

- **`root_path`**: Where videos are saved
  - Windows: `C:\\MyLibrary\\Folder` or `\\\\MyServer\\Share`
  - Linux/MacOS: `Desktop/MyLibrary/Folder`

- **`map_episode_name`**: Episode filename template
  - `%(tv_name)`: TV Show name
  - `%(season)`: Season number
  - `%(episode)`: Episode number
  - `%(episode_name)`: Episode title

- **`add_siteName`**: Append site name to root path (default: `false`)

### Language Selection
```json
{
    "M3U8_DOWNLOAD": {
        "specific_list_audio": ["ita", "it-IT"],
        "specific_list_subtitles": ["ita", "it-IT"],
        "merge_subs": true
    }
}
```

- **`specific_list_audio`**: Audio languages to download (e.g., `["ita", "eng"]`)
- **`specific_list_subtitles`**: Subtitle languages (use `["*"]` for all available)
- **`merge_subs`**: Merge subtitles into video file (default: `true`)

### Performance
```json
{
    "M3U8_DOWNLOAD": {
        "concurrent_download": true,
        "max_speed": "30MB",
        "check_segments_count": false,
        "cleanup_tmp_folder": true
    }
}
```

- **`concurrent_download`**: Download video and audio simultaneously
- **`max_speed`**: Speed limit per stream (e.g., `"30MB"`, `"10MB"`)
- **`check_segments_count`**: Verify segment count matches manifest
- **`cleanup_tmp_folder`**: Remove temporary files after download

### Video Encoding
```json
{
    "M3U8_CONVERSION": {
        "force_resolution": "Best",
        "extension": "mkv",
        "use_gpu": false,
        "subtitle_disposition": false,
        "subtitle_disposition_language": "ita"
    }
}
```

- **`force_resolution`**: `"Best"`, `"1080p"`, `"720p"`, etc.
- **`extension`**: Output format (`"mkv"`, `"mp4"`)
- **`use_gpu`**: Enable hardware acceleration
- **`subtitle_disposition`**: Automatically set default subtitle track
- **`subtitle_disposition_language`**: Language to set as default (e.g., `"ita"`, `"eng"`)

### Domain Management
```json
{
    "DEFAULT": {
        "fetch_domain_online": true
    }
}
```

#### Online Domain Fetching (Recommended)
When `fetch_domain_online` is set to `true`:
  - Automatically downloads the latest domains from the GitHub repository
  - Saves domains to a local `domains.json` file
  - Ensures you always have up-to-date streaming site domains
  - Falls back to local `domains.json` if online fetch fails

#### Local Domain Configuration
When `fetch_domain_online` is set to `false`:
  - Uses only the local `domains.json` file in the root directory
  - Allows manual domain management
  - Example `domains.json` structure:

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

#### Adding New Sites
To request a new site, contact us on the Discord server!

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
# Specify languages
python test_run.py --specific_list_audio ita,eng --specific_list_subtitles eng,spa

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