# 29.12.25

from rich.console import Console


# Variable
console = Console()


def map_keys_to_representations(keys: list, representations: list) -> dict:
    """
    Map decryption keys to representations based on their default_KID.
    
    Args:
        keys (list): List of key dictionaries with 'kid' and 'key' fields
        representations (list): List of representation dictionaries with 'default_kid' field
    
    Returns:
        dict: Mapping of representation type to key info
    """
    key_mapping = {}
    
    for rep in representations:
        rep_type = rep.get('type', 'unknown')
        default_kid = rep.get('default_kid')
        
        if not default_kid:
            continue
            
        # Normalize KID (remove dashes, lowercase)
        normalized_rep_kid = default_kid.replace('-', '').lower()
        
        for key_info in keys:
            normalized_key_kid = key_info['kid'].replace('-', '').lower()
            
            if normalized_key_kid == normalized_rep_kid:
                key_mapping[rep_type] = {
                    'kid': key_info['kid'],
                    'key': key_info['key'],
                    'representation_id': rep.get('id'),
                    'default_kid': default_kid
                }
                #console.print(f"[cyan]Mapped [red]{rep_type} [cyan]key: [red]{key_info['kid']} [cyan]→ representation [red]{rep.get('id')}")
                break
    
    return key_mapping