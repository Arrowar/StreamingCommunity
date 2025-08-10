"""FastAPI HTTP API for StreamingCommunity with job queue.

Exposes endpoints:
- GET /providers
- POST /search
- POST /module_call
- POST /jobs (create download job)
- GET /jobs
- GET /jobs/{job_id}

Auth: optional Basic Auth via config DEFAULT.http_api_username/password

Jobs are processed sequentially (one at a time) to ensure downloads don't run concurrently.
"""
from __future__ import annotations

import base64
import importlib
import glob
import os
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from StreamingCommunity.Util.config_json import config_manager

app = FastAPI(title="StreamingCommunity API")


# ----------------------- auth dependency -----------------------
def _check_auth(request: Request) -> None:
    username = config_manager.get('DEFAULT', 'http_api_username')
    password = config_manager.get('DEFAULT', 'http_api_password')
    if not username and not password:
        return

    auth = request.headers.get('Authorization')
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required', headers={"WWW-Authenticate": "Basic"})
    try:
        scheme, data = auth.split(' ', 1)
        if scheme.lower() != 'basic':
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Bad auth scheme', headers={"WWW-Authenticate": "Basic"})
        decoded = base64.b64decode(data).decode()
        u, p = decoded.split(':', 1)
        if not (u == username and p == password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials', headers={"WWW-Authenticate": "Basic"})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization header', headers={"WWW-Authenticate": "Basic"})


# ----------------------- registry / helpers -----------------------
API_REGISTRY: Dict[str, Callable[..., Any]] = {}


def expose_api(name: Optional[str] = None):
    def _decorator(func: Callable[..., Any]):
        key = f"{func.__module__.split('.')[-1]}.{name or func.__name__}"
        API_REGISTRY[key] = func
        return func

    return _decorator


def _get_site_modules() -> List[Dict[str, Any]]:
    api_dir = os.path.join(os.path.dirname(__file__), 'Site')
    init_files = glob.glob(os.path.join(api_dir, '*', '__init__.py'))
    modules: List[Dict[str, Any]] = []
    for init_file in init_files:
        module_name = os.path.basename(os.path.dirname(init_file))
        try:
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')
            indice = getattr(mod, 'indice', None)
            use_for = getattr(mod, '_useFor', None)
            deprecated = getattr(mod, '_deprecate', False)
            if not deprecated:
                modules.append({'name': module_name, 'indice': indice, 'use_for': use_for})
        except Exception:
            continue
    modules.sort(key=lambda x: (x['indice'] if x['indice'] is not None else 9999))
    return modules


def _serialize_media_manager(manager: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        media_list = getattr(manager, 'media_list', [])
        for item in media_list:
            try:
                data = item.__dict__.copy()
            except Exception:
                data = {k: getattr(item, k, None) for k in ['id', 'name', 'type', 'url', 'size', 'score', 'date', 'desc']}
            out.append(data)
    except Exception:
        pass
    return out


# ----------------------- pydantic models -----------------------
class SearchRequest(BaseModel):
    provider: Optional[str] = None
    query: str


class ModuleCallRequest(BaseModel):
    module: str
    function: str
    kwargs: Optional[Dict[str, Any]] = None
    background: Optional[bool] = False


class JobCreateRequest(BaseModel):
    module: str
    action: str  # 'download_film' or 'download_series' or custom
    item: Dict[str, Any]
    selections: Optional[Dict[str, Any]] = None


class JobInfo(BaseModel):
    id: int
    status: str
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


# ----------------------- job queue -----------------------
class JobManager:
    def __init__(self):
        self._jobs: Dict[int, Dict[str, Any]] = {}
        self._queue: Deque[int] = deque()
        self._lock = threading.Lock()
        self._local = threading.local()
        self._next_id = 1
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def add_job(self, payload: Dict[str, Any]) -> int:
        with self._lock:
            job_id = self._next_id
            self._next_id += 1
            job = {
                'id': job_id,
                'status': 'queued',
                'created_at': time.time(),
                'progress': 0,
                'payload': payload,
                'result': None,
                'error': None,
            }
            self._jobs[job_id] = job
            self._queue.append(job_id)
            return job_id

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        return list(self._jobs.values())

    def _worker_loop(self) -> None:
        while True:
            job_id = None
            with self._lock:
                if self._queue:
                    job_id = self._queue.popleft()
            if job_id is None:
                time.sleep(0.5)
                continue

            job = self._jobs.get(job_id)
            if not job:
                continue
            # set thread-local current job id so the running code can update progress
            try:
                self._local.current_job = job_id
            except Exception:
                self._local = threading.local()
                self._local.current_job = job_id
            job['status'] = 'running'
            job['started_at'] = time.time()
            try:
                # ensure progress starts at 0
                job['progress'] = 0
                job['result'] = self._run_job(job['payload'])
                job['status'] = 'finished'
                job['progress'] = 100
            except Exception as e:
                job['status'] = 'failed'
                job['error'] = f"{type(e).__name__}: {e}"
                # on failure we set progress to 100 to indicate job completion
                job['progress'] = 100
            finally:
                job['finished_at'] = time.time()
                # clear thread-local current job
                try:
                    del self._local.current_job
                except Exception:
                    pass

    def update_progress(self, percent: float, job_id: Optional[int] = None) -> None:
        """Update progress for a job. Percent is clamped to 0..100."""
        try:
            p = float(percent)
        except Exception:
            return
        p = max(0.0, min(100.0, p))
        with self._lock:
            if job_id is None:
                # try get from thread-local
                job_id = getattr(self._local, 'current_job', None)
            if not job_id:
                return
            job = self._jobs.get(job_id)
            if not job:
                return
            job['progress'] = p

    def get_current_job_id(self) -> Optional[int]:
        return getattr(self._local, 'current_job', None)

    def _run_job(self, payload: Dict[str, Any]) -> Any:
        module_name = payload.get('module')
        action = payload.get('action')
        item = payload.get('item')
        selections = payload.get('selections') or {}

        mod = importlib.import_module(f'StreamingCommunity.Api.Site.{module_name}')
        # prepare MediaItem
        from StreamingCommunity.Api.Template.Class.SearchType import MediaItem

        media_obj = MediaItem(**item)

        if action == 'download_film':
            fn = getattr(mod, 'download_film', None)
            if not callable(fn):
                raise RuntimeError('download_film not available in module')
            return fn(media_obj)
        elif action == 'download_series':
            fn = getattr(mod, 'download_series', None)
            if not callable(fn):
                raise RuntimeError('download_series not available in module')
            season = selections.get('season')
            episode = selections.get('episode')
            return fn(media_obj, season, episode)
        else:
            # try registry or attribute
            key = f"{module_name}.{action}"
            fn = API_REGISTRY.get(key)
            if fn is None:
                fn = getattr(mod, action, None)
            if not callable(fn):
                raise RuntimeError('Action not found')
            return fn(media_obj, **selections)


JOB_MANAGER = JobManager()


# ----------------------- endpoints -----------------------
@app.get('/providers', dependencies=[Depends(_check_auth)])
def providers():
    return {'providers': _get_site_modules()}


@app.post('/search', dependencies=[Depends(_check_auth)])
def search(req: SearchRequest):
    modules = _get_site_modules()
    results: Dict[str, Any] = {}
    targets = []
    if req.provider in (None, 'all'):
        targets = modules
    else:
        for m in modules:
            if str(m.get('indice')) == str(req.provider) or m.get('name') == req.provider:
                targets = [m]
                break

    timeout = 20
    try:
        timeout = int(config_manager.get('DEFAULT', 'http_api_provider_timeout') or 20)
    except Exception:
        timeout = 20

    import concurrent.futures
    futures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(targets)))) as executor:
        for m in targets:
            name = m['name']
            try:
                mod = importlib.import_module(f'StreamingCommunity.Api.Site.{name}')
            except Exception as e:
                results[name] = {'error': {'type': type(e).__name__, 'message': str(e)}}
                continue
            futures[name] = executor.submit(mod.search, req.query, True)

        for name, fut in futures.items():
            try:
                manager = fut.result(timeout=timeout)
                results[name] = _serialize_media_manager(manager) if manager is not None else []
            except concurrent.futures.TimeoutError:
                results[name] = {'error': {'type': 'TimeoutError', 'message': f'Provider timed out after {timeout}s'}}
            except Exception as e:
                results[name] = {'error': {'type': type(e).__name__, 'message': str(e)}}

    return {'query': req.query, 'results': results}


@app.post('/module_call', dependencies=[Depends(_check_auth)])
def module_call(req: ModuleCallRequest):
    # first try registry
    key = f"{req.module}.{req.function}"
    fn = API_REGISTRY.get(key)
    if fn is None:
        try:
            mod = importlib.import_module(f'StreamingCommunity.Api.Site.{req.module}')
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        fn = getattr(mod, req.function, None)
        if not callable(fn):
            raise HTTPException(status_code=400, detail='function not found')

    if req.background:
        # schedule as job
        job_id = JOB_MANAGER.add_job({'module': req.module, 'action': req.function, 'item': req.kwargs or {}, 'selections': {}})
        return {'status': 'scheduled', 'job_id': job_id}

    # call synchronously but protect with timeout via executor
    import concurrent.futures
    try:
        timeout = int(config_manager.get('DEFAULT', 'http_api_provider_timeout') or 20)
    except Exception:
        timeout = 20

    def _call():
        return fn(**(req.kwargs or {}))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        fut = executor.submit(_call)
        try:
            res = fut.result(timeout=timeout)
            return {'result': res}
        except concurrent.futures.TimeoutError:
            raise HTTPException(status_code=500, detail=f'Function timed out after {timeout}s')
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post('/jobs', dependencies=[Depends(_check_auth)])
def create_job(req: JobCreateRequest):
    # validate module exists
    try:
        importlib.import_module(f'StreamingCommunity.Api.Site.{req.module}')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    job_id = JOB_MANAGER.add_job(req.dict())
    return {'job_id': job_id}


@app.get('/jobs', dependencies=[Depends(_check_auth)])
def list_jobs():
    return {'jobs': JOB_MANAGER.list_jobs()}


@app.get('/jobs/{job_id}', dependencies=[Depends(_check_auth)])
def get_job(job_id: int):
    job = JOB_MANAGER.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


def start_api_server():
    port = int(config_manager.get('DEFAULT', 'http_api_port') or 8080)
    # import here to avoid requiring uvicorn at module import time
    try:
        import uvicorn as _uvicorn
    except Exception as e:
        raise RuntimeError('uvicorn is required to run the HTTP server') from e
    _uvicorn.run(app, host='0.0.0.0', port=port, log_level="error")
