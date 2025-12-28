# 29.12.25

from typing import Optional


class DRMSystem:
    """DRM system constants and utilities"""
    WIDEVINE = 'widevine'
    PLAYREADY = 'playready'
    FAIRPLAY = 'fairplay'
    
    # UUID mappings
    UUIDS = {
        WIDEVINE: 'edef8ba9-79d6-4ace-a3c8-27dcd51d21ed',
        PLAYREADY: '9a04f079-9840-4286-ab92-e65be0885f95',
        FAIRPLAY: '94ce86fb-07ff-4f43-adb8-93d2fa968ca2'
    }
    
    # Display abbreviations
    ABBREV = {
        WIDEVINE: 'WV',
        PLAYREADY: 'PR',
        FAIRPLAY: 'FP'
    }
    
    # Fallback priority order
    PRIORITY = [WIDEVINE, PLAYREADY, FAIRPLAY]
    
    # CENC protection scheme
    CENC_SCHEME = 'urn:mpeg:dash:mp4protection:2011'
    
    @classmethod
    def get_uuid(cls, drm_type: str) -> Optional[str]:
        """Get UUID for DRM type"""
        return cls.UUIDS.get(drm_type.lower())
    
    @classmethod
    def get_abbrev(cls, drm_type: str) -> str:
        """Get abbreviation for DRM type"""
        return cls.ABBREV.get(drm_type.lower(), drm_type.upper()[:2])
    
    @classmethod
    def from_uuid(cls, uuid: str) -> Optional[str]:
        """Get DRM type from UUID"""
        uuid_lower = uuid.lower()
        for drm_type, drm_uuid in cls.UUIDS.items():
            if drm_uuid in uuid_lower:
                return drm_type
        return None


class CodecQuality:
    """Codec quality rankings"""
    VIDEO_CODEC_RANK = {
        'av01': 5, 'vp9': 4, 'vp09': 4, 'hev1': 3, 
        'hvc1': 3, 'avc1': 2, 'avc3': 2, 'mp4v': 1,
    }
    
    AUDIO_CODEC_RANK = {
        'opus': 5, 'mp4a.40.2': 4, 'mp4a.40.5': 3, 
        'mp4a': 2, 'ac-3': 2, 'ec-3': 3,
    }
    
    @staticmethod
    def get_video_codec_rank(codec: Optional[str]) -> int:
        if not codec:
            return 0
        codec_lower = codec.lower()
        for key, rank in CodecQuality.VIDEO_CODEC_RANK.items():
            if codec_lower.startswith(key):
                return rank
        return 0
    
    @staticmethod
    def get_audio_codec_rank(codec: Optional[str]) -> int:
        if not codec:
            return 0
        codec_lower = codec.lower()
        for key, rank in CodecQuality.AUDIO_CODEC_RANK.items():
            if codec_lower.startswith(key):
                return rank
        return 0


class AdPeriodDetector:
    """Detects advertisement periods"""
    
    AD_INDICATORS = ['_ad/', 'ad_bumper', '/creative/', '_OandO/']
    
    @staticmethod
    def is_ad_period(period_id: str, base_url: str) -> bool:
        """Check if period is an advertisement"""
        for indicator in AdPeriodDetector.AD_INDICATORS:
            if indicator in base_url:
                return True
        
        if period_id and '_subclip_' in period_id:
            return False
        
        return False