# 18.06.24

import ssl
import time
from urllib.parse import urlparse, unquote


# External libraries
import httpx


# Internal utilities
from StreamingCommunity.Util.headers import get_headers
from StreamingCommunity.Util.console import console
from StreamingCommunity.Util._jsonConfig import config_manager


# Variable
VERIFY = config_manager.get("REQUESTS", "verify")


def get_tld(url_str):
    """Extract the TLD (Top-Level Domain) from the URL."""
    try:
        url_str = unquote(url_str)
        parsed = urlparse(url_str)
        domain = parsed.netloc.lower()

        if domain.startswith('www.'):
            domain = domain[4:]
        parts = domain.split('.')

        return parts[-1] if len(parts) >= 2 else None
    
    except Exception:
        return None

def get_base_domain(url_str):
    """Extract base domain without protocol, www and path."""
    try:
        parsed = urlparse(url_str)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        # Check if domain has multiple parts separated by dots
        parts = domain.split('.')
        if len(parts) > 2:
            return '.'.join(parts[:-1])
        
        return parts[0]
    
    except Exception:
        return None
    
def get_base_url(url_str):
    """Extract base URL including protocol and domain, removing path and query parameters."""
    try:
        parsed = urlparse(url_str)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    except Exception:
        return None

def validate_url(url, base_url, max_timeout, max_retries=2, sleep=1):
    """Validate if URL is accessible and matches expected base domain."""
    console.print(f"\n[cyan]Starting validation for URL[white]: [yellow]{url}")
    
    # Verify URL structure matches base_url structure
    base_domain = get_base_domain(base_url)
    url_domain = get_base_domain(url)

    if base_domain != url_domain:
        console.print(f"[red]Domain structure mismatch: {url_domain} != {base_domain}")
        return False, None
    
    # Count dots to ensure we don't have extra subdomains
    base_dots = base_url.count('.')
    url_dots = url.count('.')
    if url_dots > base_dots + 1:
        console.print(f"[red]Too many subdomains in URL")
        return False, None

    client = httpx.Client(
        verify=VERIFY,
        headers=get_headers(),
        timeout=max_timeout
    )

    for retry in range(max_retries):
        try:
            time.sleep(sleep)
            
            # Initial check without redirects
            response = client.get(url, follow_redirects=False)
            if response.status_code == 403:
                console.print(f"[red]Check failed (403) - Attempt {retry + 1}/{max_retries}")
                continue
                
            if response.status_code >= 400:
                console.print(f"[red]Check failed: HTTP {response.status_code}")
                return False, None
                
            # Follow redirects and verify final domain
            final_response = client.get(url, follow_redirects=True)
            final_domain = get_base_domain(str(final_response.url))
            console.print(f"[cyan]Redirect url: [red]{final_response.url}")
            
            if final_domain != base_domain:
                console.print(f"[red]Final domain mismatch: {final_domain} != {base_domain}")
                return False, None
                
            new_tld = get_tld(str(final_response.url))
            if new_tld != get_tld(url):
                return True, new_tld
                
            return True, None
            
        except (httpx.RequestError, ssl.SSLError) as e:
            console.print(f"[red]Connection error: {str(e)}")
            time.sleep(sleep)
            continue
            
    return False, None

def search_domain(site_name: str, base_url: str, get_first: bool = False):
    """Search for valid domain matching site name and base URL."""
    max_timeout = config_manager.get_int("REQUESTS", "timeout")
    
    try:
        is_correct, redirect_tld = validate_url(base_url, base_url, max_timeout)

        if is_correct:
            tld = redirect_tld or get_tld(base_url)
            config_manager.configSite[site_name]['domain'] = tld

            console.print(f"[green]Successfully validated initial URL")
            return tld, base_url
        
        else:
            return None, None
        
    except Exception as e:
        console.print(f"[red]Error testing initial URL: {str(e)}")