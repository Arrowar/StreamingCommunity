import threading
import importlib
import json
from typing import Any, Dict, List

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .forms import SearchForm, DownloadForm


def _load_site_search(site: str):
    module_path = f"StreamingCommunity.Api.Site.{site}"
    mod = importlib.import_module(module_path)
    return getattr(mod, "search")


def _ensure_direct_item(search_fn, item_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Garantisce un direct_item valido ricostruendolo dal database se mancano campi chiave."""
    if item_payload.get("id") and (item_payload.get("slug") or item_payload.get("url")):
        return item_payload

    query = (
        item_payload.get("title")
        or item_payload.get("name")
        or item_payload.get("slug")
        or item_payload.get("display_title")
    )
    if not query:
        return item_payload

    try:
        database = search_fn(query, get_onlyDatabase=True)
        if (
            not database
            or not hasattr(database, "media_list")
            or not database.media_list
        ):
            return item_payload

        # Prova match per slug
        wanted_slug = item_payload.get("slug")
        if wanted_slug:
            for el in database.media_list:
                if getattr(el, "slug", None) == wanted_slug:
                    return el.__dict__.copy()

        # Altrimenti primo risultato
        return database.media_list[0].__dict__.copy()
    except Exception:
        return item_payload


def _search_results_to_list(
    database_obj: Any, source_alias: str
) -> List[Dict[str, Any]]:
    # database_obj expected to be MediaManager with media_list of MediaItem-like objects
    results = []
    if not database_obj or not hasattr(database_obj, "media_list"):
        return results
    for element in database_obj.media_list:
        item_dict = element.__dict__.copy() if hasattr(element, "__dict__") else {}
        # Campi sicuri per il template
        item_dict["display_title"] = (
            item_dict.get("title")
            or item_dict.get("name")
            or item_dict.get("slug")
            or "Senza titolo"
        )
        item_dict["display_type"] = (
            item_dict.get("type") or item_dict.get("media_type") or "Unknown"
        )
        item_dict["source"] = source_alias.capitalize()
        item_dict["source_alias"] = source_alias
        try:
            item_dict["payload_json"] = json.dumps(item_dict)
        except Exception:
            item_dict["payload_json"] = json.dumps(
                {
                    k: item_dict.get(k)
                    for k in ["id", "name", "title", "type", "url", "slug"]
                    if k in item_dict
                }
            )
        results.append(item_dict)
    return results


@require_http_methods(["GET"])
def search_home(request: HttpRequest) -> HttpResponse:
    form = SearchForm()
    return render(request, "searchapp/home.html", {"form": form})


@require_http_methods(["POST"])
def search(request: HttpRequest) -> HttpResponse:
    form = SearchForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Dati non validi")
        return render(request, "searchapp/home.html", {"form": form})

    site = form.cleaned_data["site"]
    query = form.cleaned_data["query"]

    try:
        search_fn = _load_site_search(site)
        database = search_fn(query, get_onlyDatabase=True)
        results = _search_results_to_list(database, site)
    except Exception as e:
        messages.error(request, f"Errore nella ricerca: {e}")
        return render(request, "searchapp/home.html", {"form": form})

    download_form = DownloadForm()
    return render(
        request,
        "searchapp/results.html",
        {
            "form": SearchForm(initial={"site": site, "query": query}),
            "download_form": download_form,
            "results": results,
        },
    )


def _run_download_in_thread(
    site: str, item_payload: Dict[str, Any], season: str | None, episode: str | None
) -> None:
    def _task():
        try:
            search_fn = _load_site_search(site)

            # Assicura direct_item valido
            direct_item = _ensure_direct_item(search_fn, item_payload)

            selections = None
            # Per animeunity consideriamo solo gli episodi
            if site == "animeunity":
                selections = {"episode": episode or None} if episode else None
            else:
                if season or episode:
                    selections = {"season": season or None, "episode": episode or None}

            search_fn(direct_item=direct_item, selections=selections)
        except Exception:
            return

    threading.Thread(target=_task, daemon=True).start()


@require_http_methods(["POST"])
def start_download(request: HttpRequest) -> HttpResponse:
    form = DownloadForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Dati non validi")
        return redirect("search_home")

    source_alias = form.cleaned_data["source_alias"]
    item_payload_raw = form.cleaned_data["item_payload"]
    season = form.cleaned_data.get("season") or None
    episode = form.cleaned_data.get("episode") or None

    # Normalizza spazi
    if season:
        season = str(season).strip() or None
    if episode:
        episode = str(episode).strip() or None

    try:
        item_payload = json.loads(item_payload_raw)
    except Exception:
        messages.error(request, "Payload non valido")
        return redirect("search_home")

    # source_alias is like 'streamingcommunity' or 'animeunity'
    site = source_alias.split("_")[0].lower()

    # Estrai titolo per il messaggio
    title = (
        item_payload.get("display_title")
        or item_payload.get("title")
        or item_payload.get("name")
        or "contenuto selezionato"
    )

    # Per animeunity, se non specificato, scarica tutti gli episodi evitando prompt
    if site == "animeunity" and not episode:
        episode = "*"

    _run_download_in_thread(site, item_payload, season, episode)

    # Messaggio di successo con dettagli
    season_info = ""
    if site != "animeunity" and season:
        season_info = f" (Stagione {season}"
    episode_info = f", Episodi {episode}" if episode else ""
    season_info += ")" if season_info and not episode_info == "" else ""

    messages.success(
        request,
        f"Download avviato per '{title}'{season_info}{episode_info}. "
        f"Il download sta procedendo in background.",
    )

    return redirect("search_home")
