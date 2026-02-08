# Coding Conventions

**Analysis Date:** 2026-02-08

## Naming Patterns

**Files:**
- Lowercase with underscores: `mp4.py`, `config_manager.py`, `widevine.py`
- Specialized files: `run.py` for CLI entry points, `__init__.py` for package markers
- Class names in files: PascalCase (e.g., `DRMManager` in `manager.py`)
- Test files: Descriptive names like `MP4.py`, `HLS.py` in Test directory (no `test_` prefix currently)

**Functions:**
- snake_case for all function definitions: `get_sanitize_file()`, `add_encoding_params()`, `signal_handler()`
- Private functions prefixed with underscore: `_convert_to_data_type()`, `_get_max_length()`, `_expand_user_path()`, `_should_run_on_current_os()`
- Helper functions grouped logically: `get_wv_keys()`, `get_pr_keys()` for related DRM operations

**Variables:**
- snake_case for local and module variables: `console`, `headers`, `config_path`, `total_size_value`
- Module-level constants: UPPERCASE_WITH_UNDERSCORES: `REQUEST_VERIFY`, `CREATE_NFO_FILES`, `SKIP_DOWNLOAD`, `CONFIG_FILENAME`
- Class instance variables: snake_case with underscore prefix for private: `_cache_enabled`, `_config_data`, `_cache_prefix`
- Config values assigned at module import: `DELAY = config_manager.remote_cdm.get_int('config', 'delay_after_request')`

**Types:**
- Type hints used in function signatures: `def MP4_Downloader(url: str, path: str, referer: str = None, headers_: dict = None) -> Tuple[str, bool]:`
- Return type annotations: `-> bool`, `-> int`, `-> List[str]`, `-> Dict[str, Any]`
- Optional types with `Optional[str]`, `Optional[Dict]` in HLS_Downloader class
- Type hints in function parameters: `list[str]`, `list[dict]`, `List[Dict]`, `Dict[str, Any]`

**Classes:**
- PascalCase: `ConfigAccessor`, `ConfigManager`, `DRMManager`, `HLS_Downloader`, `InterruptHandler`
- Suffixed with primary responsibility: `*Manager`, `*Downloader`, `*Handler`

## Code Style

**Formatting:**
- No explicit formatter configured (no .black, .ruff, .flake8 config files detected)
- Manual style adherence with date stamps in comments (e.g., `# 09.06.24` at file start)
- Line length appears to be ~120 characters based on code samples
- Indentation: 4 spaces consistently

**Linting:**
- Minimal linting enforcement detected; `ruff: noqa: E402` comment found in test files
- No eslint/flake8/black configuration files in repo
- Appears to be manual code review style

**Import Organization:**
Order observed consistently across modules (in `mp4.py`, `merge.py`, `os.py`, `hls.py`):
1. Standard library imports (os, sys, time, logging, subprocess, threading, typing, etc.)
2. Blank line
3. External library imports (rich, httpx, bs4, curl_cffi, etc.) - marked with comment `# External library` or `# External libraries`
4. Blank line
5. Internal utilities/imports - marked with comment `# Internal utilities`
6. Blank line
7. Logic/domain-specific imports - marked with comment `# Logic class`, `# Logic`, `# DRM Utilities`
8. Blank line
9. Configuration/module-level setup - marked with comment `# Config`, `# Variable`

**Path Aliases:**
- Full module paths used consistently: `from StreamingCommunity.utils.http_client import ...`
- No path aliases detected (no `@` aliases or pyproject.toml path mappings)
- Relative imports for deeply nested modules: `from ..setup.binary_paths import binary_paths` in `os.py`

## Error Handling

**Patterns:**
- Try-except with broad Exception catching frequently used: `except Exception as e:`
- Specific exception types used when known: `except PermissionError as e:`, `except KeyboardInterrupt:`, `except (KeyboardInterrupt):`
- Silent pass with minimal logging: `except Exception: pass` (e.g., in `mp4.py` line 122, HLS downloader)
- Error messages printed to console via Rich: `console.print(f"[red]Error: {e}")`
- Logging module used sparingly: `logging.error(f"Invalid URL: {url}")` in `mp4.py`
- None returns on error: Functions return `None` on failure instead of raising (e.g., `MP4_Downloader` returns `(None, False)`)

**Return Patterns:**
- Tuple returns for status: `(path, success_bool)` for downloaders
- Dict returns for complex operations: `Dict[str, Any]` in HLS_Downloader.start()
- List or None returns: `list[str]` from key extraction or `None` on failure in DRMManager

**Validation:**
- Manual validation before operations: Check `os.path.exists()` before download, validate URL with `url.lower().startswith()`
- Silent catches with fallback logic: HEAD request fails → fallback to GET without Range header (mp4.py lines 136-158)
- Config validation via type conversion: `get_bool()`, `get_int()`, `get_list()` methods in ConfigAccessor

## Logging

**Framework:** Rich Console for output, Python logging module for error records

**Patterns:**
- Rich console for user-facing output: `console.print("[yellow]Message")`, `console.log(f"[red]Error: {e}")`
- Color codes used: `[yellow]`, `[red]`, `[green]`, `[cyan]`, `[magenta]`, `[blue]`, `[bright_*]` variants
- Structured logging with colored tags: `[cyan]Path:[red]{path}` format
- Python logging for backend errors: `logging.error(f"Path creation error: {e}")`
- Progress tracking via console: Rich Progress bars with custom columns (mp4.py lines 174-252)

## Comments

**When to Comment:**
- File header with date: `# 09.06.24` pattern at file start (appears to track modification dates)
- Section headers with inline comments: `# Config`, `# Variable`, `# External library`, `# Internal utilities`, `# Logic class`
- Complex algorithm explanation: Comments explaining interrupt handler logic (mp4.py lines 44-51)
- State machine transitions: Comments for download status tracking flow

**JSDoc/TSDoc:**
- Not used; codebase uses Python docstrings instead
- Function docstrings with triple quotes: See `ConfigAccessor.get()` method (config.py lines 36-48)
- Docstring format: Summary line, blank line, Args section, blank line, Returns section (following Google style)

## Function Design

**Size:**
- Functions range from 5-50 lines typically
- Complex functions decomposed into helper functions: Signal handler split from main MP4_Downloader function
- Larger functions (100+ lines) for complete workflows like MP4_Downloader (lines 62-317)

**Parameters:**
- Positional + keyword args pattern: `MP4_Downloader(url: str, path: str, referer: str = None, headers_: dict = None, ...)`
- Default None for optional parameters: `referer: str = None`
- Trailing underscores for parameter conflicts: `headers_` to avoid shadowing built-ins
- Type hints on all parameters in newer code (config.py, drm/manager.py)

**Return Values:**
- Consistent tuple returns for operation status: `(result, success_flag)` or `(path, kill_download_flag)`
- None on fatal errors rather than exceptions
- Complex return types wrapped in TypedDict style: `Dict[str, Any]` for flexible returns

## Module Design

**Exports:**
- Explicit `__all__` list in package init files: `/StreamingCommunity/utils/__init__.py` exports `config_manager`, `start_message`, etc.
- No barrel files re-exporting complex submodules; direct imports preferred

**Barrel Files:**
- Minimal use of barrel files; most modules import directly from submodules
- Exception: `utils/__init__.py` exports common utilities, `cli/__init__.py` exports search functions

**Organizational Pattern:**
- Manager classes for resource lifecycle: `ConfigManager` (init, load, cache), `DRMManager` (init, key extraction)
- Downloader classes for specific formats: `MP4_Downloader`, `HLS_Downloader` (functional approach)
- Utility modules for helpers: `os.py` (OsManager class), `config.py` (ConfigManager + ConfigAccessor)
- Clear separation: Core logic (`core/`), CLI (`cli/`), Services (`services/`), Utils (`utils/`)

---

*Conventions analysis: 2026-02-08*
