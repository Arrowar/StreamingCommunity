from curl_cffi import requests
import json
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich import box

console = Console()

BASE_URL = "https://www.raiplay.it"
SEARCH_URL = f"{BASE_URL}/atomatic/raiplay-search-service/api/v1/msearch"

HEADERS = {
    'accept': 'application/json',
    'accept-language': 'it-IT,it;q=0.9',
    'content-type': 'application/json',
    'domainapikey': 'arSgRtwasD324SaA',
    'origin': BASE_URL,
    'referer': f'{BASE_URL}/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'x-caller': 'web',
    'x-caller-version': '1.0'
}

def search_content(query):
    """Search content on RaiPlay"""
    payload = {
        "templateIn": "6470a982e4e0301afe1f81f1",
        "templateOut": "6516ac5d40da6c377b151642",
        "params": {
            "param": query,
            "from": 0,
            "sort": "relevance",
            "size": 48,
            "additionalSize": 30,
            "onlyVideoQuery": False,
            "onlyProgramsQuery": False
        }
    }
    
    try:
        r = requests.post(SEARCH_URL, headers=HEADERS, json=payload, timeout=10, impersonate="chrome136")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        console.print(f"[red]Search error: {e}[/red]")
        return None

def get_program_details(path_id):
    """Get program details"""
    url = f"{BASE_URL}{path_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, impersonate="chrome136")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        console.print(f"[red]Details error: {e}[/red]")
        return None

def get_episodes_direct(base_path, active_block, active_set):
    """Get episodes directly from episodes.json endpoint"""
    url = f"{BASE_URL}{base_path}/{active_block}/{active_set}/episodes.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, impersonate="chrome136")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        console.print(f"[red]Episodes error: {e}[/red]")
        return None

def scrape_search_results(query):
    """Complete scraping of search results"""
    console.print(f"[cyan]🔍 Search: {query}[/cyan]")
    
    results = search_content(query)
    if not results:
        return
    
    # Extract cards from results
    agg = results.get('agg', {})
    cards = agg.get('video', {}).get('cards', [])
    
    if not cards:
        console.print("[yellow]No results found[/yellow]")
        return
    
    # Group by program
    programs = {}
    for card in cards:
        parent = card.get('parent_path_id', '')
        if parent:
            parent_clean = parent.replace(BASE_URL, '').replace('https://www.raiplay.it', '')
            if parent_clean not in programs:
                programs[parent_clean] = {
                    'name': card.get('programma', 'N/D'),
                    'path_id': parent_clean,
                    'episodes': []
                }
            programs[parent_clean]['episodes'].append({
                'title': card.get('titolo', 'N/D'),
                'episode': card.get('episodio', 'N/D'),
                'duration': card.get('durata', 'N/D'),
                'summary': card.get('sommario', '')
            })
    
    # Show results
    table = Table(title=f"Results: {len(programs)} programs", box=box.ROUNDED)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Program", style="magenta", width=40)
    table.add_column("Episodes", style="green", width=10)
    table.add_column("Path", style="dim", width=40)
    
    prog_list = list(programs.values())
    for idx, prog in enumerate(prog_list, 1):
        table.add_row(
            str(idx),
            prog['name'],
            str(len(prog['episodes'])),
            prog['path_id']
        )
    
    console.print(table)
    
    # Ask which program to explore
    choice = Prompt.ask("\n[green]Select program (number, 0=skip)[/green]", default="0")
    
    if choice == "0":
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(prog_list):
            selected = prog_list[idx]
            scrape_program_full(selected)
            
    except Exception:
        console.print("[red]Invalid selection[/red]")

def scrape_program_full(program_info):
    """Complete scraping of a program"""
    console.print(f"\n[cyan]📺 Scraping: {program_info['name']}[/cyan]")
    
    # Get details
    data = get_program_details(program_info['path_id'])
    if not data:
        return
    
    info = data.get('program_info', {})
    
    # Program info
    panel_content = f"""[bold]Title:[/bold] {info.get('name', 'N/D')}
[bold]Year:[/bold] {info.get('year', 'N/D')}
[bold]Type:[/bold] {info.get('typology', 'N/D')}
[bold]Channel:[/bold] {info.get('channel', 'N/D')}

[dim]{info.get('description', '')}[/dim]"""
    
    console.print(Panel(panel_content, title="📋 Info", border_style="green"))
    
    # Extract blocks - now we look at ALL blocks
    blocks = data.get('blocks', [])
    
    all_seasons = []
    
    console.print(f"\n[dim]Found {len(blocks)} blocks, analyzing...[/dim]")
    
    for block in blocks:
        block_name = block.get('name', 'N/A')
        block_type = block.get('type', '')
        block_id = block.get('id', '')
        
        # Debug: show all blocks
        console.print(f"[dim]  Block: '{block_name}' (type: {block_type})[/dim]")
        
        # Only process multimedia blocks with sets
        if block_type == 'RaiPlay Multimedia Block' and 'sets' in block:
            sets = block.get('sets', [])
            console.print(f"[dim]    → Found {len(sets)} sets[/dim]")
            
            for s in sets:
                set_name = s.get('name', '')
                set_id = s.get('id', '')
                episode_size = s.get('episode_size', {})
                count = episode_size.get('number', 0)
                
                if count > 0:  # Only add sets with episodes
                    all_seasons.append({
                        'name': set_name or block_name,
                        'block_id': block_id,
                        'set_id': set_id,
                        'episodes_count': count,
                        'block_name': block_name
                    })
                    console.print(f"[dim]      ✓ Set: '{set_name}' ({count} episodes)[/dim]")
    
    if not all_seasons:
        console.print("\n[yellow]❌ No seasons/episodes found in blocks[/yellow]")
        console.print("[dim]Tip: This program might use a different structure[/dim]")
        
        # Debug: save full JSON for analysis
        debug = Prompt.ask("\n[yellow]Save full JSON for debugging? (y/n)[/yellow]", default="n")
        if debug.lower() == 'y':
            filename = "debug_program_structure.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            console.print(f"[green]✓ Saved: {filename}[/green]")
        return
    
    # Show seasons
    table = Table(title=f"Found {len(all_seasons)} sections", box=box.ROUNDED)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Section", style="magenta", width=35)
    table.add_column("Episodes", style="green", width=10)
    table.add_column("Block", style="dim", width=20)
    
    for idx, s in enumerate(all_seasons, 1):
        table.add_row(str(idx), s['name'], str(s['episodes_count']), s['block_name'])
    
    console.print(table)
    
    # Scrape all seasons or specific one
    choice = Prompt.ask("\n[green]Scrape (a=all, number=single, 0=skip)[/green]", default="0")
    
    if choice == "0":
        return
    elif choice.lower() == "a":
        for season in all_seasons:
            scrape_season_episodes(program_info, season)
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_seasons):
                scrape_season_episodes(program_info, all_seasons[idx])

        except Exception:
            console.print("[red]Invalid selection[/red]")

def scrape_season_episodes(program_info, season_info):
    """Scrape episodes from a season using episodes.json endpoint"""
    console.print(f"\n[cyan]🎬 Scraping: {season_info['name']}[/cyan]")
    
    # Build the episodes endpoint URL
    base_path = program_info['path_id'].replace('.json', '')
    data = get_episodes_direct(base_path, season_info['block_id'], season_info['set_id'])
    
    if not data:
        return
    
    # Navigate the nested structure to find cards
    items = []
    seasons = data.get('seasons', [])
    if seasons:
        for season in seasons:
            episodes = season.get('episodes', [])
            for episode in episodes:
                cards = episode.get('cards', [])
                items.extend(cards)
    
    if not items:
        console.print("[yellow]No episodes found[/yellow]")
        return
    
    table = Table(title=f"Episodes ({len(items)})", box=box.ROUNDED)
    table.add_column("Ep", style="cyan", width=5)
    table.add_column("Title", style="magenta", width=45)
    table.add_column("Duration", style="green", width=10)
    table.add_column("Info", style="yellow", width=15)
    
    for item in items:
        ep_num = item.get('episode_title', '') or item.get('toptitle', '') or 'N/D'
        title = item.get('name', 'N/D')
        duration = item.get('duration_in_minutes', 'N/D')
        info = item.get('episode', '') or item.get('season', '') or '-'
        
        table.add_row(ep_num, title, duration, info)
    
    console.print(table)
    
    # Save JSON (optional)
    save = Prompt.ask("\n[green]Save JSON data? (y/n)[/green]", default="n")
    if save.lower() == 'y':
        filename = f"{season_info['name'].replace(' ', '_').replace('/', '-')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        console.print(f"[green]✓ Saved: {filename}[/green]")

def main():
    console.print(Panel.fit(
        "[bold cyan]🎭 RaiPlay Scraper v2[/bold cyan]\n"
        "[dim]Enhanced scraping tool for RaiPlay content[/dim]",
        border_style="blue"
    ))
    
    while True:
        query = Prompt.ask("\n[bold]🔍 Search[/bold] (or 'exit')")
        
        if query.lower() in ['esci', 'exit', 'quit', 'q']:
            console.print("[cyan]👋 Goodbye![/cyan]")
            break
        
        scrape_search_results(query)

if __name__ == "__main__":
    main()