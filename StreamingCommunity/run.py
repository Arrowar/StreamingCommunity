# 10.12.23

import os
import sys
import logging
import platform
import argparse
import importlib
import threading
import asyncio
import subprocess
from urllib.parse import urlparse
from typing import Callable, Tuple


# External library
from rich.console import Console
from rich.prompt import Prompt


# Internal utilities
from .global_search import global_search
from StreamingCommunity.Api.Template.loader import load_search_functions
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.config_json import config_manager
from StreamingCommunity.Util.os import internet_manager, os_manager
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity.Lib.TMBD import tmdb
from StreamingCommunity.Upload.update import update as git_update
from StreamingCommunity.TelegramHelp.telegram_bot import get_bot_instance, TelegramSession


# Config
SHOW_TRENDING = config_manager.get_bool('DEFAULT', 'show_trending')
TELEGRAM_BOT = config_manager.get_bool('DEFAULT', 'telegram_bot')
BYPASS_DNS = config_manager.get_bool('DEFAULT', 'bypass_dns')
COLOR_MAP = {
    "anime": "red",
    "film_&_serie": "yellow", 
    "serie": "blue",
    "torrent": "white"
}
CATEGORY_MAP = {1: "anime", 2: "film_&_serie", 3: "serie", 4: "torrent"}


# Variable
console = Console()
msg = Prompt()


def run_function(func: Callable[..., None], close_console: bool = False, search_terms: str = None) -> None:
    """Run function once or indefinitely based on close_console flag."""
    if close_console:
        while 1:
            func(search_terms)
    else:
        func(search_terms)


def initialize():
    """Initialize the application with system checks and setup."""
    start_message()
    
    # Windows 7 terminal size fix
    if platform.system() == "Windows" and "7" in platform.version():
        os.system('mode 120, 40')
    
    # Python version check
    if sys.version_info < (3, 7):
        console.log("[red]Install python version > 3.7.16")
        sys.exit(0)

    # Show trending content
    if SHOW_TRENDING:
        print()
        tmdb.display_trending_films()
        tmdb.display_trending_tv_shows()
    
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
        hooks_section = config_manager.config.get('HOOKS', {})
        hooks_list = hooks_section.get(stage, []) or []
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
        name = hook.get('name') or f"{stage}_hook"
        enabled = hook.get('enabled', True)
        continue_on_error = hook.get('continue_on_error', True)
        timeout = hook.get('timeout')

        if not enabled:
            logging.info(f"Skip hook (disabled): {name}")
            continue

        if not _should_run_on_current_os(hook):
            logging.info(f"Skip hook (OS filter): {name}")
            continue

        try:
            command, popen_kwargs = _build_command_for_hook(hook)
            logging.info(f"Running hook: {name} -> {' '.join(command)}")
            result = None
            if timeout is not None:
                result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=int(timeout), **popen_kwargs)
            else:
                result = subprocess.run(command, check=False, capture_output=True, text=True, **popen_kwargs)

            stdout = (result.stdout or '').strip()
            stderr = (result.stderr or '').strip()
            if stdout:
                logging.info(f"Hook '{name}' stdout: {stdout}")
                try:
                    console.print(f"[cyan][hook:{name} stdout][/cyan]\n{stdout}")
                except Exception:
                    pass
            if stderr:
                logging.warning(f"Hook '{name}' stderr: {stderr}")
                try:
                    console.print(f"[yellow][hook:{name} stderr][/yellow]\n{stderr}")
                except Exception:
                    pass

            if result.returncode != 0:
                message = f"Hook '{name}' exited with code {result.returncode}"
                if continue_on_error:
                    logging.error(message + " (continuing)")
                    continue
                else:
                    logging.error(message + " (stopping)")
                    raise SystemExit(result.returncode)

        except subprocess.TimeoutExpired:
            message = f"Hook '{name}' timed out"
            if continue_on_error:
                logging.error(message + " (continuing)")
                continue
            else:
                logging.error(message + " (stopping)")
                raise SystemExit(124)
        except Exception as e:
            message = f"Hook '{name}' failed: {str(e)}"
            if continue_on_error:
                logging.error(message + " (continuing)")
                continue
            else:
                logging.error(message + " (stopping)")
                raise


def restart_script():
    """Restart script with same command line arguments."""
    print("\nRiavvio dello script...\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def force_exit():
    """Force script termination in any context."""
    print("\nChiusura dello script in corso...")
    
    # Close all threads except main
    for t in threading.enumerate():
        if t is not threading.main_thread():
            print(f"Chiusura thread: {t.name}")
            t.join(timeout=1)
    
    # Stop asyncio if active
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            print("Arresto del loop asyncio...")
            loop.stop()
    except RuntimeError:
        pass
    
    # Exit gracefully or force
    try:
        print("Uscita con sys.exit(0)")
        sys.exit(0)
    except SystemExit:
        pass
    
    print("Uscita forzata con os._exit(0)")
    os._exit(0)


def check_dns():
    """Check DNS configuration and exit if required."""
    if BYPASS_DNS:
        return
        
    hostname_list = [
        urlparse(site_info.get('full_url')).hostname 
        for site_info in config_manager.configSite.values() 
        if urlparse(site_info.get('full_url')).hostname
    ]
    
    if not internet_manager.check_dns_resolve(hostname_list):
        console.print("[red]\nERROR: DNS configuration is required!")
        console.print("[red]The program cannot function correctly without proper DNS settings.")
        console.print("\n[yellow]Please configure one of these DNS servers:")
        console.print("[red]• Cloudflare (1.1.1.1) 'https://developers.cloudflare.com/1.1.1.1/setup/windows/'")
        console.print("[red]• Quad9 (9.9.9.9) 'https://docs.quad9.net/Setup_Guides/Windows/Windows_10/'")
        console.print("\n[yellow]-> The program will not work until you configure your DNS settings.")
        sys.exit(0)


def setup_argument_parser(search_functions):
    """Setup and return configured argument parser."""
    # Build help text
    module_info = {}
    for alias, (_func, _use_for) in search_functions.items():
        module_name = alias.split("_")[0].lower()
        try:
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')
            module_info[module_name] = int(getattr(mod, 'indice'))
        except Exception:
            continue
    
    available_names = ", ".join(sorted(module_info.keys()))
    available_indices = ", ".join([f"{idx}={name.capitalize()}" for name, idx in sorted(module_info.items(), key=lambda x: x[1])])
    
    parser = argparse.ArgumentParser(
        description='Script to download movies and series from the internet.',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"Available sites by name: {available_names}\nAvailable sites by index: {available_indices}"
    )
    
    # Add arguments
    parser.add_argument("script_id", nargs="?", default="unknown", help="ID dello script")
    parser.add_argument('-s', '--search', default=None, help='Search terms')
    parser.add_argument('--global', action='store_true', help='Global search across sites')
    parser.add_argument('--not_close', type=bool, help='Keep console open after execution')
    
    parser.add_argument('--specific_list_audio', type=str, help='Audio languages (e.g., ita,eng)')
    parser.add_argument('--specific_list_subtitles', type=str, help='Subtitle languages (e.g., eng,spa)')
    parser.add_argument('--force_resolution', type=str, choices=["Best", "Worst", "720p", "1080p", "480p", "360p"],
                    help='Choose video resolution:\n'
                            '  "Best": Highest available resolution\n'
                            '  "Worst": Lowest available resolution\n'
                            '  "720p": Force 720p resolution\n'
                            '  Specific resolutions:\n'
                            '    - 1080p (1920x1080)\n'
                            '    - 720p (1280x720)\n'
                            '    - 480p (640x480)\n'
                            '    - 360p (640x360)')

    parser.add_argument('--category', type=int, help='Category (1: anime, 2: film_&_serie, 3: serie, 4: torrent)')
    parser.add_argument('--auto-first', action='store_true', help='Auto-download first result (use with --site and --search)')
    parser.add_argument('--site', type=str, help='Site by name or index')
    
    return parser


def apply_config_updates(args):
    """Apply command line arguments to configuration."""
    config_updates = {}
    
    arg_mappings = {
        'not_close': 'DEFAULT.not_close', 
        'force_resolution': 'M3U8_CONVERSION.force_resolution',
    }
    
    for arg_name, config_key in arg_mappings.items():
        if getattr(args, arg_name) is not None:
            config_updates[config_key] = getattr(args, arg_name)
    
    # Handle list arguments
    if args.specific_list_audio is not None:
        config_updates['M3U8_DOWNLOAD.specific_list_audio'] = args.specific_list_audio.split(',')
    if args.specific_list_subtitles is not None:
        config_updates['M3U8_DOWNLOAD.specific_list_subtitles'] = args.specific_list_subtitles.split(',')
    
    # Apply updates
    for key, value in config_updates.items():
        section, option = key.split('.')
        config_manager.set_key(section, option, value)
    
    if config_updates:
        config_manager.save_config()


def build_function_mappings(search_functions):
    """Build mappings between indices/names and functions."""
    input_to_function = {}
    choice_labels = {}
    module_name_to_function = {}
    
    for alias, (func, use_for) in search_functions.items():
        module_name = alias.split("_")[0]
        try:
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')
            site_index = str(getattr(mod, 'indice'))
            input_to_function[site_index] = func
            choice_labels[site_index] = (module_name.capitalize(), use_for.lower())
            module_name_to_function[module_name.lower()] = func
        except Exception as e:
            console.print(f"[red]Error mapping module {module_name}: {str(e)}")
    
    return input_to_function, choice_labels, module_name_to_function


def handle_direct_site_selection(args, input_to_function, module_name_to_function, search_terms):
    """Handle direct site selection via command line."""
    if not args.site:
        return False
        
    site_key = str(args.site).strip().lower()
    func_to_run = input_to_function.get(site_key) or module_name_to_function.get(site_key)
    
    if func_to_run is None:
        available_sites = ", ".join(sorted(module_name_to_function.keys()))
        console.print(f"[red]Unknown site:[/red] '{args.site}'. Available: [yellow]{available_sites}[/yellow]")
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
                console.print("[yellow]No results found. Falling back to interactive mode.[/yellow]")
        except Exception as e:
            console.print(f"[red]Auto-first failed:[/red] {str(e)}")
    
    run_function(func_to_run, search_terms=search_terms)
    return True


def get_user_site_selection(args, choice_labels):
    """Get site selection from user (interactive or category-based)."""
    bot = get_bot_instance() if TELEGRAM_BOT else None
    
    if args.category:
        selected_category = CATEGORY_MAP.get(args.category)
        category_sites = [(key, label[0]) for key, label in choice_labels.items() if label[1] == selected_category]
        
        if len(category_sites) == 1:
            console.print(f"[green]Selezionato automaticamente: {category_sites[0][1]}[/green]")
            return category_sites[0][0]
        
        # Multiple sites in category
        color = COLOR_MAP.get(selected_category, 'white')
        prompt_items = [f"[{color}]({k}) {v}[/{color}]" for k, v in category_sites]
        prompt_line = ", ".join(prompt_items)
        
        if TELEGRAM_BOT:
            console.print(f"\nInsert site: {prompt_line}")
            return bot.ask("select_site", f"Insert site: {prompt_line}", None)
        else:
            return msg.ask(f"\n[cyan]Insert site: {prompt_line}", choices=[k for k, _ in category_sites], show_choices=False)
    
    else:
        # Show all sites
        legend_text = " | ".join([f"[{color}]{cat.capitalize()}[/{color}]" for cat, color in COLOR_MAP.items()])
        console.print(f"\n[bold cyan]Category Legend:[/bold cyan] {legend_text}")
        
        if TELEGRAM_BOT:
            category_legend = "Categorie: \n" + " | ".join([cat.capitalize() for cat in COLOR_MAP.keys()])
            prompt_message = "Inserisci il sito:\n" + "\n".join([f"{key}: {label[0]}" for key, label in choice_labels.items()])
            console.print(f"\n{prompt_message}")
            return bot.ask("select_provider", f"{category_legend}\n\n{prompt_message}", None)
        else:
            prompt_message = "[cyan]Insert site: " + ", ".join([
                f"[{COLOR_MAP.get(label[1], 'white')}]({key}) {label[0]}[/{COLOR_MAP.get(label[1], 'white')}]" 
                for key, label in choice_labels.items()
            ])
            return msg.ask(prompt_message, choices=list(choice_labels.keys()), default="0", show_choices=False, show_default=False)


def main(script_id=0):
    if TELEGRAM_BOT:
        get_bot_instance().send_message(f"Avviato script {script_id}", None)

    Logger()
    execute_hooks('pre_run')
    initialize()

    try:
        check_dns()
        search_functions = load_search_functions()

        parser = setup_argument_parser(search_functions)
        args = parser.parse_args()

        apply_config_updates(args)

        if getattr(args, 'global'):
            global_search(args.search)
            return

        input_to_function, choice_labels, module_name_to_function = build_function_mappings(search_functions)

        if handle_direct_site_selection(args, input_to_function, module_name_to_function, args.search):
            return

        category = get_user_site_selection(args, choice_labels)

        if category in input_to_function:
            run_function(input_to_function[category], search_terms=args.search)
        else:
            if TELEGRAM_BOT:
                get_bot_instance().send_message("Categoria non valida", None)
            console.print("[red]Invalid category.")

            if getattr(args, 'not_close'):
                restart_script()
            else:
                force_exit()
                if TELEGRAM_BOT:
                    get_bot_instance().send_message("Chiusura in corso", None)
                    script_id = TelegramSession.get_session()
                    if script_id != "unknown":
                        TelegramSession.deleteScriptId(script_id)
    finally:
        execute_hooks('post_run')