# Technology Stack

**Analysis Date:** 2026-02-08

## Languages

**Primary:**
- Python 3.8+ - Core application for content downloading and streaming
  - Supported: 3.8, 3.9, 3.10, 3.11, 3.12 (see `setup.py`)

**Secondary:**
- Python (GUI) - Django 4.2+ for web interface (`GUI/requirements.txt`)

## Runtime

**Environment:**
- Python interpreter (3.8 minimum, 3.12 maximum)
- Docker containerization available via `dockerfile` (Python 3.11-slim base)

**Package Manager:**
- pip - Python package manager
- Lockfile: Not present (no requirements.lock or similar)

## Frameworks

**Core:**
- None (standard library + external packages, no web framework for CLI)

**GUI/Web:**
- Django 4.2 to <5.0 - Web interface for streaming platform (`GUI/requirements.txt`)

**Testing:**
- Not detected in requirements

**Build/Dev:**
- setuptools - Package building and distribution (see `setup.py`)
- Entry point: `streamingcommunity=StreamingCommunity.cli.run:main`

## Key Dependencies

**Critical:**
- httpx - HTTP client for API requests (async-capable)
- curl_cffi - CFFI-based curl wrapper for HTTP requests with anti-bot capabilities
- bs4 (BeautifulSoup4) - HTML/XML parsing for web scraping
- rich - Terminal UI and formatting
- ua_generator - User-agent generation for requests
- pywidevine - Widevine DRM key extraction (CDP implementation)
- pyplayready - PlayReady DRM key extraction
- jsbeautifier - JavaScript code beautification for parsing
- pathvalidate - File path validation and sanitization
- unidecode - Unicode normalization for filenames

**Infrastructure:**
- ffmpeg - Multimedia framework for video processing (system dependency via `dockerfile`)
- ffprobe - Media stream inspection (system dependency)
- n_m3u8dl-re - M3U8 downloader for HLS streams
- bento4 - MP4/Dash media tools
- shaka-packager - Media packaging utility
- megatools - Mega.nz client tools

**System Libraries (Docker):**
- libicu-dev - Unicode/internationalization library
- nano - Text editor
- sqlite3 - Lightweight database (built-in to Python)

## Configuration

**Environment:**
- Configuration via JSON files:
  - `conf/config.json` - Main application configuration
  - `conf/login.json` - Platform login credentials
  - `conf/domains.json` - Streaming platform domains
  - `conf/remote_cdm.json` - DRM CDM configuration
- Remote config fetching from GitHub (see `StreamingCommunity/utils/config.py`)
  - `CONFIG_DOWNLOAD_URL`: https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/conf/config.json
  - `CONFIG_LOGIN_DOWNLOAD_URL`: https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/conf/login.json
  - `DOMAINS_DOWNLOAD_URL`: https://raw.githubusercontent.com/Arrowar/SC_Domains/refs/heads/main/domains.json
  - `REMOTE_CDM_DOWNLOAD_URL`: https://raw.githubusercontent.com/Arrowar/StreamingCommunity/refs/heads/main/conf/remote_cdm.json

**Build:**
- `setup.py` - Standard setuptools configuration
- `dockerfile` - Docker containerization (Python 3.11-slim, exposed port 8000)
- Runs Django development server: `python GUI/manage.py runserver 0.0.0.0:8000`

## Platform Requirements

**Development:**
- Python 3.8+ interpreter
- pip for dependency management
- ffmpeg and ffprobe for video processing
- Optional: Docker for containerized execution

**Production:**
- Deployment target: Docker container (port 8000 exposed)
- User context: Non-root appuser (UID 1000) for security
- Directories required:
  - `/app/Video` - Output directory for downloads
  - `/app/logs` - Log storage
  - `/app/data` - Application data
  - `/home/appuser/.config` - User configuration

## Entry Points

**CLI:**
- `StreamingCommunity.cli.run:main` - Primary command-line interface
- See `setup.py` entry_points for console script registration

**GUI:**
- `GUI/manage.py runserver 0.0.0.0:8000` - Django web interface
- Accessible at `http://localhost:8000` when running in container

## Special Dependencies

**DRM/Content Protection:**
- pywidevine - Extracts Widevine DRM keys for protected content
- pyplayready - Extracts PlayReady DRM keys for protected content
- Requires external CDM devices or remote CDM APIs

**HTTP Obfuscation:**
- curl_cffi - Bypasses anti-bot protections on streaming platforms
- ua_generator - Generates realistic user-agents

**File System:**
- pathvalidate - Ensures platform-compatible filenames across OS

---

*Stack analysis: 2026-02-08*
