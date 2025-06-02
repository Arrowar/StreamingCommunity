# 20.04.2024

import re
import os
import json
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import httpx
import ua_generator

JSON_FILE_PATH = os.path.join(".github", ".domain", "domains.json")


def load_domains(file_path):
    if not os.path.exists(file_path):
        print(f"Error: The file {file_path} was not found.")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    except Exception as e:
        print(f"Error reading the file {file_path}: {e}")
        return None

def save_domains(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data successfully saved to {file_path}")

    except Exception as e:
        print(f"Error saving the file {file_path}: {e}")

def get_new_tld(full_url):
    try:
        parsed_url = urlparse(full_url)
        hostname = parsed_url.hostname
        if hostname:
            parts = hostname.split('.')
            return parts[-1]
        
    except Exception:
        pass

    return None

def extract_domain_from_response(response, original_url):
    if 'location' in response.headers:
        return response.headers['location']
    
    if str(response.url) != original_url:
        return str(response.url)
    
    try:
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' in content_type or 'text/plain' in content_type:
            response_text = response.text
            
            js_redirect_patterns = [
                r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                r'window\.location\s*=\s*["\']([^"\']+)["\']',
                r'location\.href\s*=\s*["\']([^"\']+)["\']',
                r'document\.location\s*=\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in js_redirect_patterns:
                js_match = re.search(pattern, response_text, re.IGNORECASE)
                if js_match:
                    return js_match.group(1)
            
            meta_patterns = [
                r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*content=["\'][^"\']*url=([^"\'>\s]+)',
                r'<meta[^>]*content=["\'][^"\']*url=([^"\'>\s]+)[^>]*http-equiv=["\']?refresh["\']?'
            ]
            
            for pattern in meta_patterns:
                meta_match = re.search(pattern, response_text, re.IGNORECASE)
                if meta_match:
                    return meta_match.group(1)
            
            canonical_match = re.search(r'<link[^>]*rel=["\']?canonical["\']?[^>]*href=["\']([^"\']+)["\']', response_text, re.IGNORECASE)
            if canonical_match:
                return canonical_match.group(1)
            
            base_match = re.search(r'<base[^>]*href=["\']([^"\']+)["\']', response_text, re.IGNORECASE)
            if base_match:
                return base_match.group(1)
            
            error_redirect_patterns = [
                r'[Rr]edirect(?:ed)?\s+to:?\s*([^\s<>"\']+)',
                r'[Nn]ew\s+[Uu][Rr][Ll]:?\s*([^\s<>"\']+)',
                r'[Mm]oved\s+to:?\s*([^\s<>"\']+)',
                r'[Ff]ound\s+at:?\s*([^\s<>"\']+)'
            ]
            
            for pattern in error_redirect_patterns:
                error_match = re.search(pattern, response_text)
                if error_match:
                    potential_url = error_match.group(1)
                    if potential_url.startswith(('http://', 'https://', '//')):
                        return potential_url
    
    except Exception as e:
        print(f"    [!] Error extracting from response content: {e}")
    
    return None

def try_url(url_to_try, headers, timeout=15):
    try:
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=False) as client:
            response = client.get(url_to_try)
            
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('location')
                if location:
                    print(f"    [+] Found redirect ({response.status_code}) to: {location}")
                    try:
                        final_response = client.get(location)
                        if 200 <= final_response.status_code < 400:
                            return final_response
                        else:
                            return httpx.Response(
                                status_code=200,
                                headers={"location": location},
                                content=b"",
                                request=response.request
                            )
                    except Exception:
                        return httpx.Response(
                            status_code=200,
                            headers={"location": location},
                            content=b"",
                            request=response.request
                        )
            
            elif response.status_code in [403, 409, 429, 503]:
                print(f"    [!] HTTP {response.status_code} - attempting to extract redirect info")
                
                location = response.headers.get('location')
                if location:
                    print(f"    [+] Found location header in error response: {location}")
                    return httpx.Response(
                        status_code=200,
                        headers={"location": location},
                        content=b"",
                        request=response.request
                    )
                
                new_url = extract_domain_from_response(response, url_to_try)
                if new_url and new_url != url_to_try:
                    print(f"    [+] Found redirect URL in error response content: {new_url}")
                    return httpx.Response(
                        status_code=200,
                        headers={"location": new_url},
                        content=b"",
                        request=response.request
                    )
            
            if 200 <= response.status_code < 400:
                return response
            
            print(f"  [!] HTTP {response.status_code} for {url_to_try}")
        
    except httpx.HTTPStatusError as http_err:
        new_url = extract_domain_from_response(http_err.response, url_to_try)
        if new_url:
            print(f"    [+] Found new URL from HTTPStatusError response: {new_url}")
            return httpx.Response(
                status_code=200,
                headers={"location": new_url},
                content=b"",
                request=http_err.request
            )
    except Exception as e:
        print(f"  [!] Error for {url_to_try}: {type(e).__name__}")
    
    return None

def update_domain_entries(data):
    if not data:
        return False

    updated_count = 0

    for key, entry in data.items():
        print(f"\n--- [DOMAIN] {key} ---")
        original_full_url = entry.get("full_url")
        original_domain_in_entry = entry.get("domain")

        if not original_full_url:
            print(f"  [!] 'full_url' missing. Skipped.")
            continue

        ua = ua_generator.generate(device=('desktop', 'mobile'), browser=('chrome', 'edge', 'firefox', 'safari'))
        current_headers = ua.headers.get()

        print(f"  [] Stored URL: {original_full_url}")
        if original_domain_in_entry:
            print(f"  [] Stored Domain (TLD): {original_domain_in_entry}")
        
        print(f"  [] Testing URL: {original_full_url}")
        response = try_url(original_full_url, current_headers)

        if response:
            final_url_from_request = str(response.url)
            print(f"    [+] Redirect/Response to: {final_url_from_request}")

            parsed_final_url = urlparse(final_url_from_request)
            normalized_full_url = urlunparse(parsed_final_url._replace(path='/', params='', query='', fragment=''))
            if parsed_final_url.path == '' and not normalized_full_url.endswith('/'):
                normalized_full_url += '/'
            
            if normalized_full_url != final_url_from_request:
                print(f"    [+] Normalized URL: {normalized_full_url}")

            if normalized_full_url != original_full_url:
                new_tld_val = get_new_tld(final_url_from_request)
                
                if new_tld_val:
                    entry["full_url"] = normalized_full_url
                    
                    if new_tld_val != original_domain_in_entry:
                        print(f"    [-] Domain TLD Changed: '{original_domain_in_entry}' -> '{new_tld_val}'")
                        entry["old_domain"] = original_domain_in_entry if original_domain_in_entry else entry.get("old_domain", "")
                        entry["domain"] = new_tld_val
                        entry["time_change"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"    [-] Domain & URL Updated: New TLD '{new_tld_val}', New URL '{normalized_full_url}'")
                    else:
                        entry["domain"] = new_tld_val
                        print(f"    [-] URL Updated (TLD Unchanged '{new_tld_val}'): New URL '{normalized_full_url}'")
                    
                    updated_count += 1

                else:
                    print(f"    [!] Could not extract TLD from {final_url_from_request}. URL not updated despite potential change.")
            else:
                print(f"    [] Same Domain: {final_url_from_request}")

        else:
            print(f"  [-] No response for {key}")
        
    return updated_count > 0

def main():
    print("Starting domain update script...")
    domain_data = load_domains(JSON_FILE_PATH)

    if domain_data:
        if update_domain_entries(domain_data):
            save_domains(JSON_FILE_PATH, domain_data)
            print("\nUpdate complete. Some entries were modified.")
        else:
            print("\nUpdate complete. No domains were modified.")
    else:
        print("\nCannot proceed without domain data.")
    
    print("Script finished.")

if __name__ == "__main__":
    main()