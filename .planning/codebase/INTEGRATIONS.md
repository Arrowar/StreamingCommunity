# External Integrations

**Analysis Date:** 2026-02-08

## APIs & External Services

**Streaming Platforms:**
- StreamingCommunity - Community streaming platform
  - Implementation: `StreamingCommunity/services/streamingcommunity/`
  - Auth: Cookie/session-based (stored in `login.json`)
  - Client: httpx with custom headers

- RaiPlay - Italian RAI network streaming
  - Implementation: `StreamingCommunity/services/raiplay/`
  - Auth: Session/cookie-based

- MediaSet Infinity - Italian streaming service
  - Implementation: `StreamingCommunity/services/mediasetinfinity/`
  - Auth: Session/cookie-based
  - Token logic updated in recent versions

- Discovery Plus (EU & US variants)
  - Discovery+ EU: `StreamingCommunity/services/discoveryeu/`
    - Auth: Bearer token obtained from `https://eu1-prod-direct.discoveryplus.com/token`
    - Access token lifecycle management in `StreamingCommunity/services/discoveryeu/client.py`
  - Discovery+ EU Plus: `StreamingCommunity/services/discoveryeuplus/`
    - Base API: `https://default.{tenant}-{market}.prd.api.discoveryplus.com`
    - Auth: Bearer token from `/token` endpoint
  - Discovery+ US: `StreamingCommunity/services/discoveryus/`
  - Cookie requirement: `st` token for authentication

- Crunchyroll - Anime streaming
  - Implementation: `StreamingCommunity/services/crunchyroll/`
  - Auth: Session-based

- Animes (AnimeUnity, AnimeWorld)
  - AnimeUnity: `StreamingCommunity/services/animeunity/`
  - AnimeWorld: `StreamingCommunity/services/animeworld/`
  - Auth: Session/cookie-based

- Other platforms:
  - Guarda Serie: `StreamingCommunity/services/guardaserie/`
  - D-MAX: `StreamingCommunity/services/dmax/`
  - Food Network: `StreamingCommunity/services/foodnetwork/`
  - Home Garden TV: `StreamingCommunity/services/homegardentv/`
  - Ipersphera: `StreamingCommunity/services/ipersphera/`
  - Tubi TV: `StreamingCommunity/services/tubitv/`
  - AltaDefinizione: `StreamingCommunity/services/altadefinizione/`
  - Nove: `StreamingCommunity/services/nove/`
  - Realtime: `StreamingCommunity/services/realtime/`

**Video Players (CDN/Protection):**
- VixCloud - VOD player with DRM
  - Implementation: `StreamingCommunity/player/vixcloud.py`
  - Token-based authentication
  - License URL handling

- SuperVideo - Video player
  - Implementation: `StreamingCommunity/player/supervideo.py`

- SweetPixel - Player with CSRF protection
  - Implementation: `StreamingCommunity/player/sweetpixel.py`
  - CSRF token requirement

- Mediapolis VOD - VOD provider
  - Implementation: `StreamingCommunity/player/mediapolisvod.py`

## Data Storage

**Databases:**
- SQLite (local) - DRM key caching
  - Location: `{binary_directory}/drm_keys.db` (configurable)
  - Client: sqlite3 (built-in Python)
  - Tables: `drm_cache`, `drm_keys` with foreign key relationships
  - Implementation: `StreamingCommunity/utils/vault/local_db.py`

- Supabase (remote, optional)
  - External URL: Configured in `conf/remote_cdm.json`
  - Functions endpoint: `{url}/functions/v1`
  - Functions:
    - `/set-key` - Add DRM keys
    - `/get-keys` - Retrieve DRM keys
  - Implementation: `StreamingCommunity/utils/vault/external_supa_db.py`
  - When available: `obj_externalSupaDbVault` replaces local database

**File Storage:**
- Local filesystem only
  - Download directory: `conf/config.json` → `OUT_FOLDER.root_path` (default: "Video")
  - Subdirectories by type: Movie, Serie, Anime
  - Log directory: `/app/logs` (Docker)
  - Data directory: `/app/data` (Docker)

**Caching:**
- In-memory config caching via ConfigAccessor
- See `StreamingCommunity/utils/config.py` for cache mechanism
- DRM key persistence via SQLite or Supabase

## Authentication & Identity

**Auth Provider:**
- Custom session-based authentication per streaming platform
  - Cookie storage: `conf/login.json`
  - Session management handled per service client
  - No OAuth/OpenID Connect integrations

**Auth Mechanisms:**
- Session cookies (most platforms)
- Bearer tokens (Discovery Plus platforms)
- CSRF tokens (SweetPixel player)
- Custom parameter tokens (VixCloud)

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, rollbar, or similar)

**Logs:**
- Standard Python logging module
- Log output to console and `/app/logs` directory (Docker)
- Rich formatting for console output

## CI/CD & Deployment

**Hosting:**
- Docker containerization via `dockerfile`
- Deployment target: Generic Docker host
- No cloud provider integration detected

**CI Pipeline:**
- GitHub Actions (infrastructure present in `.github/` directory)
- Release process via GitHub (see `StreamingCommunity/upload/update.py`)

**Updates:**
- Auto-update mechanism via GitHub releases
- See `StreamingCommunity/upload/update.py`:
  - GitHub API: `https://api.github.com/repos/{author}/{repo}/releases`
  - Binary download from asset URLs
  - Update check functionality

## Environment Configuration

**Required env vars:**
- `PYTHONPATH` - Set to `/app` in Docker
- `HOME` - Set to `/home/appuser` in Docker

**Secrets location:**
- Configuration files (JSON):
  - `conf/config.json` - Application configuration
  - `conf/login.json` - Platform login credentials (secrets)
  - `conf/remote_cdm.json` - Remote DRM CDM configuration
  - `conf/domains.json` - Domain mappings
- Note: `.env` files not detected; configuration is JSON-based

**Remote config updates:**
- Fetched from GitHub raw content URLs
- Cached locally after download
- Auto-update on version mismatch

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## DRM & Content Protection Integration

**Widevine:**
- SDK: `pywidevine` library
- CDM device file: Configurable path via config
- Remote CDM: Optional API endpoints
- Implementation: `StreamingCommunity/core/drm/widevine.py`
- License request: Platform-specific license URLs
- PSSH extraction from manifests (MPD, M3U8)
- Key storage: Local DB or Supabase vault

**PlayReady:**
- SDK: `pyplayready` library
- CDM device file: Configurable path via config
- Remote CDM: Optional API endpoints
- Implementation: `StreamingCommunity/core/drm/playready.py`
- PSSH handling: System-specific PSSH format
- Key storage: Local DB or Supabase vault
- License requests: Custom URL handling

**DRM Manager:**
- Orchestration: `StreamingCommunity/core/drm/manager.py`
- Handles both Widevine and PlayReady
- Vault selection: Local SQLite or Supabase
- Configuration: `conf/remote_cdm.json` for remote CDM APIs

## M3U8 & HLS Integration

**M3U8 Downloader:**
- Tool: n_m3u8dl-re (external binary)
- Purpose: HLS stream downloading and decryption
- Configuration:
  - Thread count: `M3U8_DOWNLOAD.thread_count` (default: 8)
  - Retry count: `M3U8_DOWNLOAD.retry_count` (default: 30)
  - Real-time decryption: `M3U8_DOWNLOAD.real_time_decryption` (optional)
  - Video/audio/subtitle selection via filters
- Implementation: Integrated via binary execution in `StreamingCommunity/core/downloader/`

**Video Conversion:**
- Tool: ffmpeg (system dependency)
- Codec defaults: libx265 (H.265) for video, libopus for audio
- Output: MKV or custom format via config
- GPU support: Optional via `M3U8_CONVERSION.use_gpu`

## Third-party Tools & Utilities

**Media Tools:**
- ffmpeg - Video encoding and processing
- ffprobe - Media stream inspection
- bento4 - MP4/DASH decryption and packaging
- shaka-packager - DASH packaging utility
- megatools - Mega.nz cloud storage access

**Network Tools:**
- curl_cffi - Anti-bot capable HTTP requests
- httpx - Modern HTTP client library
- ua_generator - User-agent generation

**Data Processing:**
- BeautifulSoup4 (bs4) - HTML/XML parsing
- jsbeautifier - JavaScript beautification
- unidecode - Unicode to ASCII conversion
- pathvalidate - Path validation

---

*Integration audit: 2026-02-08*
