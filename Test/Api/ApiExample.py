"""Example script that calls the local HTTP API (if enabled).

Run this after enabling `expose_http_api` in `config.old.json`.
"""
import json
from typing import Any, Dict
import httpx

BASE = 'http://127.0.0.1:8080'
# Configure a client with a generous timeout to accommodate provider work
CLIENT_TIMEOUT = 60.0
client = httpx.Client(timeout=CLIENT_TIMEOUT)


def list_providers() -> Dict[str, Any]:
    try:
        r = client.get(f"{BASE}/providers")
        r.raise_for_status()
        data = r.json()
    except httpx.ReadTimeout:
        print(f'Error: request to /providers timed out after {CLIENT_TIMEOUT}s')
        return {}
    except httpx.RequestError as e:
        print(f'Error contacting API: {e}')
        return {}
    print('Providers:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return data


def search_all(query: str) -> Dict[str, Any]:
    payload = {'provider': 'all', 'query': query}
    try:
        r = client.post(f"{BASE}/search", json=payload)
        print(f"Search all for '{query}': status={r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception:
            print(r.text)
            return {}
    except httpx.ReadTimeout:
        print(f"Error: search request timed out after {CLIENT_TIMEOUT}s")
        return {}
    except httpx.RequestError as e:
        print(f"Error contacting API: {e}")
        return {}


def search_provider(provider: str, query: str) -> Dict[str, Any]:
    try:
        payload = {'provider': provider, 'query': query}
        r = client.post(f"{BASE}/search", json=payload)
        print(f"Search provider {provider} for '{query}': status={r.status_code}")
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except httpx.ReadTimeout:
        print(f"Error: search provider request timed out after {CLIENT_TIMEOUT}s")
        return {}
    except httpx.RequestError as e:
        print(f"Error contacting API: {e}")
        return {}


def module_call(module: str, function: str, kwargs: Dict[str, Any], background: bool = False) -> Dict[str, Any]:
    payload = {'module': module, 'function': function, 'kwargs': kwargs, 'background': background}
    try:
        r = client.post(f"{BASE}/module_call", json=payload)
        print(f"Module call {module}.{function} (background={background}): status={r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        except Exception:
            print(r.text)
            return {}
    except httpx.ReadTimeout:
        print(f"Error: module_call timed out after {CLIENT_TIMEOUT}s")
        return {}
    except httpx.RequestError as e:
        print(f"Error contacting API: {e}")
        return {}


def run_examples():
    try:
        providers = list_providers()
    except Exception as e:
        print('Failed to list providers:', e)
        return

    # Example: search across all providers
    search_all('Matrix')

    # Example: search a specific provider (use one provider from the list if present)
    prov_list = providers.get('providers', [])
    if prov_list:
        first = prov_list[0]
        search_provider(first.get('name'), 'Matrix')

    # Example: call a module function synchronously (get_onlyDatabase=True)
    # Note: most provider search functions expect parameter name 'string_to_search'
    module_call('streamingcommunity', 'search', {'string_to_search': 'Matrix', 'get_onlyDatabase': True})

    # Example: start a module call in background
    module_call('streamingcommunity', 'search', {'string_to_search': 'Matrix', 'get_onlyDatabase': True}, background=True)

    # Example: create a download job (if you have a valid item from a provider)
    # We'll try to take the first movie from streamingcommunity results if present
    sc_results = search_provider('streamingcommunity', 'Matrix')
    try:
        items = sc_results.get('results', {}).get('streamingcommunity', [])
        if items:
            first_item = items[0]
            # create job to download film
            payload = {'module': 'streamingcommunity', 'action': 'download_film', 'item': first_item}
            r = client.post(f"{BASE}/jobs", json=payload)
            print('Create job response:', r.status_code, r.text)
            job = r.json()
            job_id = job.get('job_id')
            if job_id:
                # poll job until finished
                import time
                while True:
                    rr = client.get(f"{BASE}/jobs/{job_id}")
                    data = rr.json()
                    print('Job status:', data.get('status'))
                    if data.get('status') in ('finished', 'failed'):
                        print('Final job data:', json.dumps(data, indent=2, ensure_ascii=False))
                        break
                    time.sleep(1)
    except Exception as e:
        print('Job example failed:', e)


if __name__ == '__main__':
    run_examples()
