# 04.01.25

class StreamInfo:
    def __init__(self, type_: str, language: str = "", resolution: str = "", codec: str = "", bandwidth: str = "", raw_bandwidth: str = "", name: str = "", selected: bool = False, 
            extension: str = "", total_duration: float = 0.0, frame_rate: float = 0.0, channels: str = "", role: str = "", group_id: str = "", descriptor: str = ""):
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
        self.frame_rate = frame_rate
        self.channels = channels
        self.role = role
        self.group_id = group_id
        self.descriptor = descriptor  #N_m3u8, Manual
        self.final_size = None

    def get_short_codec(self) -> str:
        """Get short human-readable codec name based on stream type."""
        if self.type == "Video":
            from StreamingCommunity.source.utils.trans_codec import get_video_codec_name
            return get_video_codec_name(self.codec)
        elif self.type == "Audio":
            from StreamingCommunity.source.utils.trans_codec import get_audio_codec_name
            return get_audio_codec_name(self.codec)
        elif self.type == "Subtitle":
            from StreamingCommunity.source.utils.trans_codec import get_subtitle_codec_name
            return get_subtitle_codec_name(self.codec)
        else:
            return self.codec

    def get_identifier(self) -> str:
        """Generate a unique identifier string for stream tracking and comparison."""
        parts = [self.type.lower()]

        if self.type == "Video" and self.resolution:
            parts.append(self.resolution.lower().replace('x', 'p'))
        elif self.type in ("Audio", "Subtitle") and self.language:
            parts.append(self.language)

        if self.codec:
            parts.append(self.get_short_codec().lower().replace('.', ''))

        if self.raw_bandwidth and self.raw_bandwidth != "0":
            try:
                bitrate_k = int(self.raw_bandwidth) // 1000
                parts.append(f"{bitrate_k}k")
            except (ValueError, TypeError):
                pass

        return "_".join(filter(None, parts))

class KeysManager:
    def __init__(self, keys=None):
        self._keys = []
        if keys:
            self.add_keys(keys)
    
    def add_keys(self, keys):
        if isinstance(keys, str):
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