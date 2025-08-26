import threading
import importlib
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
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

        # Data di uscita (prova diversi campi comuni; visualizza preferibilmente l'anno)
        release_raw = (
            item_dict.get("release_date")
            or item_dict.get("first_air_date")
            or item_dict.get("air_date")
            or item_dict.get("date")
            or item_dict.get("publish_date")
            or item_dict.get("publishedAt")
        )
        release_year = (
            item_dict.get("year")
            or item_dict.get("release_year")
            or item_dict.get("start_year")
        )
        display_release = None
        if release_raw:
            # Prova parsing in vari formati comuni
            parsed_date = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y"):
                try:
                    parsed_date = datetime.strptime(str(release_raw)[:10], fmt)
                    break
                except Exception:
                    continue
            if parsed_date:
                display_release = str(parsed_date.year)
            else:
                # Fallback: prova a estrarre l'anno da una stringa tipo 2021-...
                try:
                    year_guess = int(str(release_raw)[:4])
                    display_release = str(year_guess)
                except Exception:
                    display_release = str(release_raw)
        elif release_year:
            display_release = str(release_year)
        item_dict["display_release"] = display_release

        # Immagine di sfondo (usa il primo campo disponibile)
        bg_image_url = (
            item_dict.get("poster")
            or item_dict.get("poster_url")
            or item_dict.get("image")
            or item_dict.get("image_url")
            or item_dict.get("cover")
            or item_dict.get("cover_url")
            or item_dict.get("thumbnail")
            or item_dict.get("thumb")
            or item_dict.get("backdrop")
            or item_dict.get("backdrop_url")
        )
        if isinstance(bg_image_url, dict):
            # Alcune API possono restituire un oggetto con varie dimensioni
            # Prova chiavi comuni
            bg_image_url = (
                bg_image_url.get("url")
                or bg_image_url.get("large")
                or bg_image_url.get("medium")
                or bg_image_url.get("small")
            )
        item_dict["bg_image_url"] = bg_image_url
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
    site: str,
    item_payload: Dict[str, Any],
    season: Optional[str],
    episode: Optional[str],
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
def series_metadata(request: HttpRequest) -> JsonResponse:
    try:
        # Expect either JSON body or standard form fields
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

        site = (source_alias.split("_")[0] if source_alias else "").lower()
        media_type = (
            item_payload.get("type") or item_payload.get("media_type") or ""
        ).lower()

        # Films and OVA: no seasons/episodes
        if media_type in ("film", "movie", "ova"):
            return JsonResponse(
                {"isSeries": False, "seasonsCount": 0, "episodesPerSeason": {}}
            )

        # Guard rail: require id and slug where needed
        media_id = item_payload.get("id")
        slug = item_payload.get("slug") or item_payload.get("name")

        if site == "streamingcommunity":
            # Lazy import to avoid loading heavy package during tests unless needed
            import importlib

            try:
                scrape_mod = importlib.import_module(
                    "StreamingCommunity.Api.Site.streamingcommunity.util.ScrapeSerie"
                )
                GetSerieInfo = getattr(scrape_mod, "GetSerieInfo")
            except Exception as imp_err:
                return JsonResponse({"error": f"Import error: {imp_err}"}, status=500)

            # Best-effort base_url
            base_url = ""
            try:
                from StreamingCommunity.Util.config_json import config_manager

                base_url = (
                    config_manager.get_site("streamingcommunity", "full_url") or ""
                ).rstrip("/")
            except Exception:
                base_url = ""

            scraper = GetSerieInfo(url=base_url, media_id=media_id, series_name=slug)
            seasons_count = scraper.getNumberSeason()
            episodes_per_season: Dict[int, int] = {}
            for season_number in range(1, (seasons_count or 0) + 1):
                try:
                    episodes = scraper.getEpisodeSeasons(season_number)
                    episodes_per_season[season_number] = len(episodes or [])
                except Exception:
                    episodes_per_season[season_number] = 0

            return JsonResponse(
                {
                    "isSeries": True,
                    "seasonsCount": seasons_count or 0,
                    "episodesPerSeason": episodes_per_season,
                }
            )

        if site == "animeunity":
            import importlib

            try:
                scrape_mod = importlib.import_module(
                    "StreamingCommunity.Api.Site.animeunity.util.ScrapeSerie"
                )
                ScrapeSerieAnime = getattr(scrape_mod, "ScrapeSerieAnime")
            except Exception as imp_err:
                return JsonResponse({"error": f"Import error: {imp_err}"}, status=500)

            # Best-effort base_url
            base_url = ""
            try:
                from StreamingCommunity.Util.config_json import config_manager

                base_url = (
                    config_manager.get_site("animeunity", "full_url") or ""
                ).rstrip("/")
            except Exception:
                base_url = ""

            scraper = ScrapeSerieAnime(url=base_url)
            # Optional fields
            try:
                scraper.setup(series_name=slug, media_id=media_id)
            except Exception:
                pass

            try:
                episodes_count = scraper.get_count_episodes()
            except Exception:
                episodes_count = None

            return JsonResponse(
                {
                    "isSeries": True,
                    "seasonsCount": 1,
                    "episodesPerSeason": {1: (episodes_count or 0)},
                }
            )

        # Default: unknown site treated as no metadata
        return JsonResponse(
            {"isSeries": False, "seasonsCount": 0, "episodesPerSeason": {}}
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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

    # Per animeunity, se non specificato e se non è un contenuto non seriale (film/ova),
    # scarica tutti gli episodi evitando prompt
    media_type = (
        item_payload.get("type") or item_payload.get("media_type") or ""
    ).lower()
    if (
        site == "animeunity"
        and not episode
        and media_type not in ("film", "movie", "ova")
    ):
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
