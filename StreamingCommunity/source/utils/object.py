# 04.01.25

class StreamInfo:
    def __init__(self, type_: str, language: str = "", resolution: str = "", codec: str = "", bandwidth: str = "", raw_bandwidth: str = "", name: str = "", selected: bool = False, 
            extension: str = "", total_duration: float = 0.0, segment_count: int = 0, segments_protection: str = "NONE"):
        self.type = type_
        self.resolution = resolution
        self.language = language
        self.name = name
        self.bandwidth = bandwidth
        self.raw_bandwidth = raw_bandwidth
        self.codec = codec
        self.selected = selected
        self.extension = extension
        self.total_duration = total_duration
        self.segment_count = segment_count
        self.final_size = None
        self.segments_protection = segments_protection


class KeysManager:
    def __init__(self, keys=None):
        self._keys = []  # list of (kid, key) tuples
        if keys:
            self.add_keys(keys)
    
    def add_keys(self, keys):
        if isinstance(keys, str):
            # Handle "KID:KEY" or "KID:KEY|KID2:KEY2"
            for k in keys.split('|'):
                if ':' in k:
                    kid, key = k.split(':', 1)
                    self._keys.append((kid.strip(), key.strip()))

        elif isinstance(keys, list):
            for k in keys:
                if isinstance(k, str):
                    if ':' in k:
                        kid, key = k.split(':', 1)
                        self._keys.append((kid.strip(), key.strip()))

                elif isinstance(k, dict):
                    kid = k.get('kid', '')
                    key = k.get('key', '')
                    if kid and key:
                        self._keys.append((kid.strip(), key.strip()))
    
    def get_keys_list(self):
        return [f"{kid}:{key}" for kid, key in self._keys]
    
    def get_keys_dict(self):
        return {kid: key for kid, key in self._keys}
    
    def find_key_by_kid(self, kid):
        kid = kid.lower().replace('-', '')
        for k, v in self._keys:
            if k.lower().replace('-', '') == kid:
                return f"{k}:{v}"
        return None
    
    def __len__(self):
        return len(self._keys)
    
    def __iter__(self):
        return iter(self._keys)
    
    def __getitem__(self, index):
        return self._keys[index]
    
    def __bool__(self):
        return len(self._keys) > 0