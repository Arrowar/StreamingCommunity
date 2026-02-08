# 06-06-25 By @FrancescoGrazioso -> "https://github.com/FrancescoGrazioso"


import time
import json
import threading
from typing import Any, Dict


# External utilities
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages


# Internal utilities
from .forms import SearchForm, DownloadForm
from GUI.searchapp.api import get_api
from GUI.searchapp.api.base import Entries


# CLI utilities
from StreamingCommunity.source.utils.tracker import download_tracker, context_tracker


def _media_item_to_display_dict(item: Entries, source_alias: str) -> Dict[str, Any]:
    """Convert Entries to template-friendly dictionary."""
    result = {
        'display_title': item.name,
        'display_type': item.type.capitalize(),
        'source': source_alias.capitalize(),
        'source_alias': source_alias,
        'bg_image_url': item.poster,
        'is_movie': item.is_movie,
        'year': item.year,
    }
    result['payload_json'] = json.dumps(item.to_dict())
    return result


@require_http_methods(["GET"])
def search_home(request: HttpRequest) -> HttpResponse:
    """Display search form."""
    form = SearchForm()
    return render(request, "searchapp/home.html", {"form": form})


@require_http_methods(["POST"])
def search(request: HttpRequest) -> HttpResponse:
    """Handle search requests."""
    form = SearchForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Dati non validi")
        return render(request, "searchapp/home.html", {"form": form})

    site = form.cleaned_data["site"]
    query = form.cleaned_data["query"]

    try:
        api = get_api(site)
        media_items = api.search(query)
        results = [_media_item_to_display_dict(item, site) for item in media_items]
    except Exception as e:
        messages.error(request, f"Errore nella ricerca: {e}")
        return render(request, "searchapp/home.html", {"form": form})

    download_form = DownloadForm()
    return render(
        request,
        "searchapp/results.html",
        {
            "form": SearchForm(initial={"site": site, "query": query}),
            "query": query, # Explicitly pass query
            "download_form": download_form,
            "results": results,
        },
    )


def _run_download_in_thread(site: str, item_payload: Dict[str, Any], season: str = None, episodes: str = None, media_type: str = "Film") -> None:
    """Run download in background thread."""
    name = item_payload.get('name', 'Unknown')
    if season and episodes:
        title = f"{name} - S{season} E{episodes}"
    elif season:
        title = f"{name} - S{season}"
    else:
        title = name
        
    download_id = f"{site}_{int(time.time())}_{hash(title) % 10000}"
    
    def _task():
        try:
            # Set context for downloaders in this thread
            context_tracker.download_id = download_id
            context_tracker.site_name = site
            context_tracker.media_type = media_type
            
            api = get_api(site)
            
            # Ensure complete item
            media_item = api.ensure_complete_item(item_payload)
            
            # Start download
            api.start_download(media_item, season=season, episodes=episodes)
        except Exception as e:
            print(f"[Error] Download thread failed: {e}")
            import traceback
            traceback.print_exc()

    threading.Thread(target=_task, daemon=True).start()


@require_http_methods(["POST"])
def series_metadata(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to get series metadata (seasons/episodes).
    Returns JSON with series information.
    """
    try:
        # Parse request
        if request.content_type and "application/json" in request.content_type:
            body = json.loads(request.body.decode("utf-8"))
            source_alias = body.get("source_alias") or body.get("site")
            item_payload = body.get("item_payload") or {}
        else:
            source_alias = request.POST.get("source_alias") or request.POST.get("site")
            item_payload_raw = request.POST.get("item_payload")
            item_payload = json.loads(item_payload_raw) if item_payload_raw else {}

        if not source_alias or not item_payload:
            return JsonResponse({"error": "Parametri mancanti"}, status=400)

        # Get API instance
        api = get_api(source_alias)
        
        # Convert to Entries
        media_item = api._dict_to_entries(item_payload)
        
        # Check if it's a movie
        if media_item.is_movie:
            return JsonResponse({
                "isSeries": False,
                "seasonsCount": 0,
                "episodesPerSeason": {}
            })
        
        # Get series metadata
        seasons = api.get_series_metadata(media_item)
        
        if not seasons:
            return JsonResponse({
                "isSeries": False,
                "seasonsCount": 0,
                "episodesPerSeason": {}
            })
        
        # Build response
        episodes_per_season = {
            season.number: season.episode_count 
            for season in seasons
        }
        
        return JsonResponse({
            "isSeries": True,
            "seasonsCount": len(seasons),
            "episodesPerSeason": episodes_per_season
        })
        
    except Exception as e:
        return JsonResponse({"Error get metadata": str(e)}, status=500)


@require_http_methods(["POST"])
def start_download(request: HttpRequest) -> HttpResponse:
    """Handle download requests for movies or individual series selections."""
    form = DownloadForm(request.POST)
    if not form.is_valid():
        error_msg = f"Dati non validi: {form.errors.as_text()}"
        print(f"[Error] {error_msg}")
        messages.error(request, error_msg)
        return redirect("search_home")

    source_alias = form.cleaned_data["source_alias"]
    item_payload_raw = form.cleaned_data["item_payload"]
    season = form.cleaned_data.get("season") or None
    episode = form.cleaned_data.get("episode") or None

    # Normalize
    if season:
        season = str(season).strip() or None
    if episode:
        episode = str(episode).strip() or None

    try:
        item_payload = json.loads(item_payload_raw)
    except Exception:
        messages.error(request, "Payload non valido")
        return redirect("search_home")

    # Extract title for message
    title = item_payload.get("name")

    # For animeunity, default to all episodes if not specified and not a movie
    site = source_alias.split("_")[0].lower()
    media_type = (item_payload.get("type") or "").lower()
    
    if site == "animeunity" and not episode and media_type not in ("film", "movie", "ova"):
        episode = "*"

    # Start download in background
    _run_download_in_thread(site, item_payload, season, episode, media_type)

    # Success message
    season_info = ""
    if site != "animeunity" and season:
        season_info = f" (Stagione {season}"
    episode_info = f", Episodi {episode}" if episode else ""
    if season_info and episode_info:
        season_info += ")"
    elif season_info:
        season_info += ")"

    messages.success(
        request,
        f"Download avviato per '{title}'{season_info}{episode_info}. "
        f"Il download sta procedendo in background.",
    )

    return redirect("search_home")


@require_http_methods(["GET", "POST"])
def series_detail(request: HttpRequest) -> HttpResponse:
    """Display series details page with seasons and episodes."""
    if request.method == "GET":
        source_alias = request.GET.get("source_alias")
        item_payload_raw = request.GET.get("item_payload")
        
        if not source_alias or not item_payload_raw:
            messages.error(request, "Parametri mancanti per visualizzare i dettagli della serie.")
            return redirect("search_home")
        
        try:
            item_payload = json.loads(item_payload_raw)
        except Exception:
            messages.error(request, "Errore nel caricamento dei dati della serie.")
            return redirect("search_home")
        
        try:
            # Get API instance
            api = get_api(source_alias)
            
            # Ensure complete item
            media_item = api.ensure_complete_item(item_payload)
            
            # Get series metadata
            seasons = api.get_series_metadata(media_item)
            
            if not seasons:
                messages.error(request, "Impossibile recuperare le informazioni sulla serie.")
                return redirect("search_home")
            
            # Convert to template format
            seasons_data = [season.to_dict() for season in seasons]
            
            context = {
                "title": media_item.name,
                "source_alias": source_alias,
                "item_payload": json.dumps(media_item.to_dict()),
                "seasons": seasons_data,
                "bg_image_url": media_item.poster,
            }
            
            return render(request, "searchapp/series_detail.html", context)
            
        except Exception as e:
            messages.error(request, f"Errore nel caricamento dei dettagli: {str(e)}")
            return redirect("search_home")
    
    # POST: download season or selected episodes
    elif request.method == "POST":
        source_alias = request.POST.get("source_alias")
        item_payload_raw = request.POST.get("item_payload")
        season = request.POST.get("season")
        download_type = request.POST.get("download_type")
        episode = request.POST.get("episode", "")
        
        if not all([source_alias, item_payload_raw, season]):
            messages.error(request, "Parametri mancanti per il download.")
            return redirect("search_home")
        
        try:
            item_payload = json.loads(item_payload_raw)
        except Exception:
            messages.error(request, "Errore nel parsing dei dati.")
            return redirect("search_home")
        
        name = item_payload.get("name")
        
        # Prepare download parameters
        if download_type == "full_season":
            episode_selection = "*"
            msg_detail = f"stagione {season} completa"
            
        else:
            episode_selection = episode.strip() if episode else None
            msg_detail = f"S{season}:E{episode_selection}"
        
        # Start download
        _run_download_in_thread(source_alias, item_payload, season, episode_selection)
        
        messages.success(
            request,
            f"Download avviato per '{name}' - {msg_detail}. "
            f"Il download sta procedendo in background."
        )
        
        return redirect("search_home")


@require_http_methods(["GET"])
def download_dashboard(request: HttpRequest) -> HttpResponse:
    """Dashboard to view all active and completed downloads."""
    active_downloads = download_tracker.get_active_downloads()
    history = download_tracker.get_history()
    
    return render(
        request, 
        "searchapp/downloads.html", 
        {
            "active_downloads": active_downloads,
            "history": history
        }
    )


def get_downloads_json(request: HttpRequest) -> JsonResponse:
    """API endpoint to get real-time download progress."""
    active_downloads = download_tracker.get_active_downloads()
    history = download_tracker.get_history()
    
    return JsonResponse({
        "active": active_downloads,
        "history": history
    })

@csrf_exempt
def kill_download(request: HttpRequest) -> JsonResponse:
    """API view to cancel a download."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            download_id = data.get("download_id")
            if download_id:
                download_tracker.request_stop(download_id)
                return JsonResponse({"status": "success"})
        
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    
    return JsonResponse({"status": "error", "message": "Method not allowed", "status_code": 405}, status=405)