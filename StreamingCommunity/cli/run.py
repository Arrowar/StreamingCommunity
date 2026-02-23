# 10.12.23

import os
import sys
import logging
import platform
import argparse
import subprocess
from typing import Callable, Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from . import call_global_search, call_queue_command
from StreamingCommunity.setup import get_prd_path, get_wvd_path, get_info_wvd, get_info_prd
from StreamingCommunity.services._base import load_search_functions
from StreamingCommunity.utils import config_manager, os_manager, start_message
from StreamingCommunity.upload import git_update, binary_update
from StreamingCommunity.upload.version import __version__, __title__


# Config
console = Console()
msg = Prompt()
COLOR_MAP = {
    "anime": "red",
    "film_serie": "yellow", 
    "serie": "blue",
    "film": "green"
}
CATEGORY_MAP = {1: "anime", 2: "Film_serie", 3: "serie"}
SHOW_DEVICE_INFO = config_manager.config.get_bool('DEFAULT', 'show_device_info')
NOT_CLOSE = config_manager.config.get_bool('DEFAULT', 'close_console')


def run_function(func: Callable[..., None], search_terms: str = None) -> None:
    """Run function once or indefinitely based on close_console flag."""
    func(search_terms)


def initialize():
    """Initialize the application with system checks and setup."""
    start_message(False)

    if SHOW_DEVICE_INFO:
        prd_path = get_prd_path()
        wvd_path = get_wvd_path()
        
        if prd_path is not None:
            console.print(get_info_prd(prd_path))
        if wvd_path is not None:
            console.print(get_info_wvd(wvd_path))
    
    # Windows 7 terminal size fix
    if platform.system() == "Windows" and "7" in platform.version():
        os.system('mode 120, 40')
    
    # Python version check
    if sys.version_info < (3, 7):
        console.log("[red]Install python version > 3.7.16")
        sys.exit(0)

    # Attempt GitHub update
    try:
        git_update()
    except Exception as e:
        console.log(f"[red]Error with loading github: {str(e)}")


def _expand_user_path(path: str) -> str:
    """Expand '~' and environment variables and normalize the path."""
    if not path:
        return path
    return os.path.normpath(os.path.expandvars(os.path.expanduser(path)))


def _should_run_on_current_os(hook: dict) -> bool:
    """Check if a hook is allowed on current OS."""
    allowed_systems = hook.get('os')
    if not allowed_systems:
        return True
    try:
        normalized = [str(s).strip().lower() for s in allowed_systems]
    except Exception:
        return True
    return os_manager.system in normalized


def _build_command_for_hook(hook: dict) -> Tuple[list, dict]:
    """Build the subprocess command and environment for a hook definition."""
    hook_type = str(hook.get('type', '')).strip().lower()
    script_path = hook.get('path')
    inline_command = hook.get('command')
    args = hook.get('args', [])
    env = hook.get('env') or {}
    workdir = hook.get('cwd')

    if isinstance(args, str):
        args = [a for a in args.split(' ') if a]
    elif not isinstance(args, list):
        args = []

    if script_path:
        script_path = _expand_user_path(script_path)
        if not os.path.isabs(script_path):
            script_path = os.path.abspath(script_path)

    if workdir:
        workdir = _expand_user_path(workdir)

    base_env = os.environ.copy()
    for k, v in env.items():
        base_env[str(k)] = str(v)

    if hook_type == 'python':
        if not script_path:
            raise ValueError("Missing 'path' for python hook")
        command = [sys.executable, script_path] + args
        return ([c for c in command if c], {'env': base_env, 'cwd': workdir})

    if os_manager.system in ('linux', 'darwin'):
        if hook_type in ('bash', 'sh', 'shell'):
            if inline_command:
                command = ['/bin/bash', '-lc', inline_command]
            else:
                if not script_path:
                    raise ValueError("Missing 'path' for bash/sh hook")
                command = ['/bin/bash', script_path] + args
            return (command, {'env': base_env, 'cwd': workdir})

    if os_manager.system == 'windows':
        if hook_type in ('bat', 'cmd', 'shell'):
            if inline_command:
                command = ['cmd', '/c', inline_command]
            else:
                if not script_path:
                    raise ValueError("Missing 'path' for bat/cmd hook")
                command = ['cmd', '/c', script_path] + args
            return (command, {'env': base_env, 'cwd': workdir})

    raise ValueError(f"Unsupported hook type '{hook_type}' on OS '{os_manager.system}'")


def _iter_hooks(stage: str):
    """Yield hook dicts for a given stage ('pre_run' | 'post_run')."""
    try:
        hooks_list = config_manager.config.get_list('HOOKS', stage)
        if not isinstance(hooks_list, list):
            return
        for hook in hooks_list:
            if not isinstance(hook, dict):
                continue
            yield hook
    except Exception:
        return


def execute_hooks(stage: str) -> None:
    """Execute configured hooks for the given stage. Stage can be 'pre_run' or 'post_run'."""
    stage = str(stage).strip().lower()
    if stage not in ('pre_run', 'post_run'):
        return

    for hook in _iter_hooks(stage):
        console.print(f"\n[green]Executing hook for stage '{stage}'...")
        name = hook.get('name') or f"{stage}_hook"
        enabled = hook.get('enabled', True)
        continue_on_error = hook.get('continue_on_error', True)
        timeout = hook.get('timeout')

        if not enabled:
            continue

        if not _should_run_on_current_os(hook):
            continue

        try:
            command, popen_kwargs = _build_command_for_hook(hook)
            result = None
            if timeout is not None:
                result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=int(timeout), **popen_kwargs)
            else:
                result = subprocess.run(command, check=False, capture_output=True, text=True, **popen_kwargs)

            stdout = (result.stdout or '').strip()
            stderr = (result.stderr or '').strip()
            if stdout:
                console.print(f"[cyan][hook:{name} stdout]\n{stdout}")
            if stderr:
                logging.warning(f"Hook '{name}' stderr: {stderr}")
                console.print(f"[yellow][hook:{name} stderr]\n{stderr}")

            if result.returncode != 0:
                message = f"Hook '{name}' exited with code {result.returncode}"
                if continue_on_error:
                    logging.error(message + " (continuing)")
                    continue
                else:
                    logging.error(message + " (stopping)")
                    raise SystemExit(result.returncode)

        except Exception as e:
            message = f"Hook '{name}' failed: {str(e)}"
            if continue_on_error:
                logging.error(message + " (continuing)")
                continue
            else:
                logging.error(message + " (stopping)")
                raise


def force_exit():
    """Force script termination in any context."""
    console.print("\n[red]Closing the application...")
    sys.exit(0)


def setup_argument_parser(search_functions):
    """Setup and return configured argument parser."""
    module_info = {}
    for func in search_functions.values():
        module_info[func.module_name] = func.indice
    
    available_names = ", ".join(sorted(module_info.keys()))
    available_indices = ", ".join([f"{idx}={name.capitalize()}" for name, idx in sorted(module_info.items(), key=lambda x: x[1])])
    
    parser = argparse.ArgumentParser(
        description='Script to download movies, series and anime.',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"Available sites by name: {available_names}\nAvailable sites by index: {available_indices}"
    )
    
    # Add arguments
    parser.add_argument('-s', '--search', default=None, help='Search terms')
    parser.add_argument('--auto-first', action='store_true', help='Auto-download first result (use with --site and --search)')
    parser.add_argument('--site', type=str, help='Site by name or index')
    parser.add_argument('--global', action='store_true', help='Global search across sites')
    parser.add_argument('-q', '--queue', type=str, nargs='*', help='Queue management commands: status, download, clear, summary')
    parser.add_argument('--not_close', type=bool, help='Keep console open after last download')
    parser.add_argument('-sv', '--s_video', type=str, help='''Select video tracks. Example:  1. select best video (best) 2. Select 4K+HEVC video (res="3840*":codecs=hvc1:for=best)''')
    parser.add_argument('-sa', '--s_audio', type=str, help='''Select audio tracks. Example:  1. Select all (all) 2. Select best eng audio (lang=en:for=best) 3. Select best 2, and language is ja or en (lang="ja|en":for=best2)''')
    parser.add_argument('-ss', '--s_subtitle', type=str, help='''Select subtitle tracks. Example:  1. Select all subs (all) 2. Select all subs containing "English" (name="English":for=all)''')
    parser.add_argument('--use_proxy', action='store_true', help='Enable proxy for requests')
    parser.add_argument('--extension', type=str, help='Output file extension (mkv, mp4)')
    parser.add_argument('-UP', '--update', action='store_true', help='Auto-update to latest version (binary only)')
    parser.add_argument('--version', action='version', version=f'{__title__} {__version__}')
    return parser


def apply_config_updates(args):
    """Apply command line arguments to configuration."""
    config_updates = {}
    
    arg_mappings = {
        's_video': 'DOWNLOAD.select_video',
        's_audio': 'DOWNLOAD.select_audio',
        's_subtitle': 'DOWNLOAD.select_subtitle',
        'not_close': 'DEFAULT.close_console',
        'use_proxy': 'REQUESTS.use_proxy',
        'extension': 'PROCESS.extension'
    }
    
    for arg_name, config_key in arg_mappings.items():
        if getattr(args, arg_name) is not None:
            config_updates[config_key] = getattr(args, arg_name)
    
    # Apply updates
    for key, value in config_updates.items():
        section, option = key.split('.')
        config_manager.config.set_key(section, option, value)
    
    if config_updates:
        config_manager.save_config()


def build_function_mappings(search_functions):
    """Build mappings between indices/names and functions."""
    input_to_function = {}
    choice_labels = {}
    module_name_to_function = {}
    
    for func in search_functions.values():
        module_name = func.module_name
        site_index = str(func.indice)
        input_to_function[site_index] = func
        choice_labels[site_index] = (module_name.capitalize(), func.use_for.lower())
        module_name_to_function[module_name.lower()] = func
    
    return input_to_function, choice_labels, module_name_to_function


def handle_direct_site_selection(args, input_to_function, module_name_to_function, search_terms):
    """Handle direct site selection via command line."""
    if not args.site:
        return False
        
    site_key = str(args.site).strip().lower()
    func_to_run = input_to_function.get(site_key) or module_name_to_function.get(site_key)
    
    if func_to_run is None:
        available_sites = ", ".join(sorted(module_name_to_function.keys()))
        console.print(f"[red]Unknown site: '{args.site}'. Available: [yellow]{available_sites}")
        return False
    
    # Handle auto-first option
    if args.auto_first and search_terms:
        try:
            database = func_to_run(search_terms, get_onlyDatabase=True)
            if database and hasattr(database, 'media_list') and database.media_list:
                first_item = database.media_list[0]
                item_dict = first_item.__dict__.copy() if hasattr(first_item, '__dict__') else {}
                func_to_run(direct_item=item_dict)
                return True
            else:
                console.print("[yellow]No results found. Falling back to interactive mode.")
        except Exception as e:
            console.print(f"[red]Auto-first failed: {str(e)}")
    
    run_function(func_to_run, search_terms=search_terms)
    return True


def get_user_site_selection(args, choice_labels):
    """Get site selection from user (interactive or category-based)."""
    legend_text = " | ".join([f"[{color}]{cat.capitalize()}[/{color}]" for cat, color in COLOR_MAP.items()])
    legend_text += " | [magenta]Global[/magenta]"
    console.print(f"\n[cyan]Category Legend: {legend_text}")
    
    choice_keys = list(choice_labels.keys()) + ["global"]
    prompt_message = "[cyan]Insert site: " + ", ".join([
        f"[{COLOR_MAP.get(label[1], 'white')}]({key}) {label[0]}[/{COLOR_MAP.get(label[1], 'white')}]" 
        for key, label in choice_labels.items()
    ]) + ", [magenta](global) Global[/magenta]"
    return msg.ask(prompt_message, choices=choice_keys, default="0", show_choices=False, show_default=False)


def main():
    execute_hooks('pre_run')
    initialize()

    try:
        search_functions = load_search_functions()
        parser = setup_argument_parser(search_functions)
        args = parser.parse_args()
        
        # Handle queue commands
        if args.queue is not None:
            action = args.queue[0] if args.queue and len(args.queue) > 0 else "status"
            queue_args = args.queue[1:] if args.queue and len(args.queue) > 1 else []
            call_queue_command(action, queue_args)
            return
        
        # Handle auto-update
        if args.update:
            console.print("\n[cyan]  AUTO-UPDATE MODE")
            success = binary_update()
            
            if success:
                console.print("\n[green]Update process initiated successfully!")
            else:
                console.print("\n[yellow]Update was not performed")
            return
        
        apply_config_updates(args)

        if getattr(args, 'global'):
            call_global_search(args.search)
            return

        input_to_function, choice_labels, module_name_to_function = build_function_mappings(search_functions)
        if handle_direct_site_selection(args, input_to_function, module_name_to_function, args.search):
            return
        
        if not NOT_CLOSE:
            while True:
                category = get_user_site_selection(args, choice_labels)

                if category == "global":
                    call_global_search(args.search)

                if category in input_to_function:
                    run_function(input_to_function[category], search_terms=args.search)
                
                user_response = msg.ask("\n[cyan]Do you want to perform another search? (y/n)", choices=["y", "n"], default="n")
                if user_response.lower() != 'y':
                    break

            force_exit()

        else:
            category = get_user_site_selection(args, choice_labels)

            if category == "global":
                call_global_search(args.search)

            if category in input_to_function:
                run_function(input_to_function[category], search_terms=args.search)

            force_exit()
                
    finally:
        execute_hooks('post_run')