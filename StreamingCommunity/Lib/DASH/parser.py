# 25.07.25

import json
import logging
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
from isodate import parse_duration


# External libraries
from lxml import etree
from curl_cffi import requests
from rich.console import Console
from rich.table import Table


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager


# Variables
console = Console()
max_timeout = config_manager.get_int('REQUESTS', 'timeout')
FILTER_CUSTOM_RESOLUTION = str(config_manager.get('M3U8_CONVERSION', 'force_resolution')).strip().lower()
DOWNLOAD_SPECIFIC_AUDIO = config_manager.get_list('M3U8_DOWNLOAD', 'specific_list_audio')


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


class DurationUtils:
    """Utilities for handling ISO-8601 durations"""
    
    @staticmethod
    def parse_duration(duration_str: Optional[str]) -> int:
        """Parse ISO-8601 duration to seconds using isodate library"""
        if not duration_str:
            return 0
        try:
            duration = parse_duration(duration_str)
            return int(duration.total_seconds())
        except Exception:
            return 0

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format seconds like '~48m55s' or '~1h02m03s'"""
        if not seconds or seconds < 0:
            return ""
        
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        
        if h > 0:
            return f"~{h}h{m:02d}m{s:02d}s"
        return f"~{m}m{s:02d}s"


class URLBuilder:
    """Handles URL construction with template substitution"""
    
    @staticmethod
    def build_url(base: str, template: str, rep_id: Optional[str] = None, number: Optional[int] = None, time: Optional[int] = None, bandwidth: Optional[int] = None) -> Optional[str]:
        if not template:
            return None

        # Substitute placeholders
        if rep_id is not None:
            template = template.replace('$RepresentationID$', rep_id)
        if bandwidth is not None:
            template = template.replace('$Bandwidth$', str(bandwidth))
        if time is not None:
            template = template.replace('$Time$', str(time))
        
        # Handle $Number$ with optional formatting (e.g., $Number%05d$)
        if '$Number' in template:
            num_str = str(number if number is not None else 0)
            
            # Check for formatting like $Number%05d$
            if '%0' in template and 'd$' in template:
                start = template.find('%0')
                end = template.find('d$', start)
                if start != -1 and end != -1:
                    width_str = template[start+2:end]
                    try:
                        width = int(width_str)
                        num_str = str(number if number is not None else 0).zfill(width)
                    except ValueError:
                        pass
            
            template = template.replace('$Number%05d$', num_str)
            template = template.replace('$Number$', num_str)

        return URLBuilder._finalize_url(base, template)

    @staticmethod
    def _finalize_url(base: str, template: str) -> str:
        """Finalize URL construction preserving query and fragment"""
        parts = template.split('#', 1)
        path_and_query = parts[0]
        fragment = ('#' + parts[1]) if len(parts) == 2 else ''
        
        if '?' in path_and_query:
            path, query = path_and_query.split('?', 1)
            abs_path = urljoin(base, path)
            return abs_path + '?' + query + fragment
        else:
            return urljoin(base, path_and_query) + fragment


class NamespaceManager:
    """Manages XML namespaces for DASH manifests"""
    
    def __init__(self, root: etree._Element):
        self.nsmap = self._extract_namespaces(root)
    
    @staticmethod
    def _extract_namespaces(root: etree._Element) -> Dict[str, str]:
        """Extract namespaces from root element"""
        nsmap = {}
        if root.nsmap:
            # Use 'mpd' as default prefix for the main namespace
            nsmap['mpd'] = root.nsmap.get(None) or 'urn:mpeg:dash:schema:mpd:2011'
            nsmap['cenc'] = 'urn:mpeg:cenc:2013'

            # Add other namespaces if present
            for prefix, uri in root.nsmap.items():
                if prefix is not None:
                    nsmap[prefix] = uri

        else:
            # Fallback to default DASH namespace
            nsmap['mpd'] = 'urn:mpeg:dash:schema:mpd:2011'
            nsmap['cenc'] = 'urn:mpeg:cenc:2013'
        return nsmap
    
    def find(self, element: etree._Element, path: str) -> Optional[etree._Element]:
        """Find element using namespace-aware XPath"""
        return element.find(path, namespaces=self.nsmap)
    
    def findall(self, element: etree._Element, path: str) -> List[etree._Element]:
        """Find all elements using namespace-aware XPath"""
        return element.findall(path, namespaces=self.nsmap)


class BaseURLResolver:
    """Resolves base URLs at different MPD hierarchy levels"""
    
    def __init__(self, mpd_url: str, ns_manager: NamespaceManager):
        self.mpd_url = mpd_url
        self.ns = ns_manager
    
    def get_initial_base_url(self, root: etree._Element) -> str:
        """Get base URL from MPD root"""
        base_url = self.mpd_url.rsplit('/', 1)[0] + '/'
        
        base_elem = self.ns.find(root, 'mpd:BaseURL')
        if base_elem is not None and base_elem.text:
            base_text = base_elem.text.strip()
            base_url = base_text if base_text.startswith('http') else urljoin(base_url, base_text)
        
        return base_url
    
    def resolve_base_url(self, element: etree._Element, current_base: str) -> str:
        """Resolve base URL for any element"""
        base_elem = self.ns.find(element, 'mpd:BaseURL')
        if base_elem is not None and base_elem.text:
            base_text = base_elem.text.strip()
            return base_text if base_text.startswith('http') else urljoin(current_base, base_text)
        return current_base


class ContentProtectionHandler:
    """Handles DRM and content protection"""
    def __init__(self, ns_manager: NamespaceManager):
        self.ns = ns_manager
    
    def is_protected(self, element: etree._Element) -> bool:
        """Check if element has DRM protection"""
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            value = (cp.get('value') or '').lower()
            
            # Check for CENC
            if DRMSystem.CENC_SCHEME in scheme_id and ('cenc' in value or value):
                return True
            
            # Check for any DRM UUID
            if DRMSystem.from_uuid(scheme_id):
                return True
        
        return False
    
    def get_drm_types(self, element: etree._Element) -> List[str]:
        """
        Determine all DRM types from ContentProtection elements.
        Returns: List of DRM types found ['widevine', 'playready', 'fairplay']
        """
        drm_types = []
        
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            drm_type = DRMSystem.from_uuid(scheme_id)
            
            if drm_type and drm_type not in drm_types:
                drm_types.append(drm_type)
        
        return drm_types
    
    def get_primary_drm_type(self, element: etree._Element, preferred_drm: str = DRMSystem.WIDEVINE) -> Optional[str]:
        """
        Get primary DRM type based on preference.
        
        Args:
            element: XML element to check
            preferred_drm: Preferred DRM system ('widevine', 'playready', 'auto')
        
        Returns: Primary DRM type to use
        """
        drm_types = self.get_drm_types(element)
        
        if not drm_types:
            return None
        
        # If only one DRM, return it
        if len(drm_types) == 1:
            return drm_types[0]
        
        # Multiple DRM systems, apply preference
        if preferred_drm in drm_types:
            return preferred_drm
        
        # Fallback to priority order
        for fallback in DRMSystem.PRIORITY:
            if fallback in drm_types:
                return fallback
        
        return drm_types[0]
    
    def extract_default_kid(self, element: etree._Element) -> Optional[str]:
        """Extract default_KID from ContentProtection elements (Widevine/PlayReady/CENC)."""
        def _extract_kid_from_cp(cp: etree._Element) -> Optional[str]:
            kid = (cp.get('{urn:mpeg:cenc:2013}default_KID') or 
                   cp.get('default_KID') or 
                   cp.get('cenc:default_KID'))

            # Fallback: any attribute key that ends with 'default_KID' (case-insensitive)
            if not kid:
                for k, v in (cp.attrib or {}).items():
                    if isinstance(k, str) and k.lower().endswith('default_kid') and v:
                        kid = v
                        break

            if not kid:
                return None

            # Normalize UUID -> hex (no dashes), lowercase
            return kid.strip().replace('-', '').lower()

        cps = self.ns.findall(element, 'mpd:ContentProtection')
        if not cps:
            return None

        # Prefer Widevine KID, then CENC protection, then any other CP
        preferred = []
        fallback = []

        for cp in cps:
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            if DRMSystem.UUIDS[DRMSystem.WIDEVINE] in scheme_id:
                preferred.append(cp)
            elif DRMSystem.CENC_SCHEME in scheme_id:
                preferred.append(cp)
            else:
                fallback.append(cp)

        for cp in preferred + fallback:
            kid = _extract_kid_from_cp(cp)
            if kid:
                return kid

        return None
    
    def extract_pssh(self, root: etree._Element, drm_type: str = DRMSystem.WIDEVINE) -> Optional[str]:
        """
        Extract PSSH (Protection System Specific Header) for specific DRM type.
        
        Args:
            root: XML root element
            drm_type: DRM type ('widevine', 'playready', 'fairplay')
        """
        target_uuid = DRMSystem.get_uuid(drm_type)
        if not target_uuid:
            return None
        
        # Search in all ContentProtection elements in the entire MPD
        all_cps = self.ns.findall(root, './/mpd:ContentProtection')
        
        # Try specific DRM type first
        for cp in all_cps:
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            if target_uuid in scheme_id:
                pssh = self.ns.find(cp, 'cenc:pssh')
                if pssh is not None and pssh.text:
                    return pssh.text.strip()
        
        return None


class SegmentTimelineParser:
    """Parses SegmentTimeline elements"""
    
    def __init__(self, ns_manager: NamespaceManager):
        self.ns = ns_manager
    
    def parse(self, seg_template: etree._Element, start_number: int = 1) -> Tuple[List[int], List[int]]:
        """Parse SegmentTimeline and return (number_list, time_list)"""
        seg_timeline = self.ns.find(seg_template, 'mpd:SegmentTimeline')
        if seg_timeline is None:
            return [], []
        
        number_list = []
        time_list = []
        current_time = 0
        current_number = start_number
        
        for s_elem in self.ns.findall(seg_timeline, 'mpd:S'):
            d = s_elem.get('d')
            if d is None:
                continue
            
            d = int(d)
            
            # Explicit time
            if s_elem.get('t') is not None:
                current_time = int(s_elem.get('t'))
            
            # Repeat count
            r = int(s_elem.get('r', 0))
            if r == -1:
                r = 0  # Special case: repeat until end
            
            # Add segments
            for _ in range(r + 1):
                number_list.append(current_number)
                time_list.append(current_time)
                current_number += 1
                current_time += d
        
        return number_list, time_list


class SegmentURLBuilder:
    """Builds segment URLs from SegmentTemplate"""
    
    def __init__(self, ns_manager: NamespaceManager):
        self.ns = ns_manager
        self.timeline_parser = SegmentTimelineParser(ns_manager)
    
    def build_urls(self, seg_template: etree._Element, rep_id: str, bandwidth: int, base_url: str, period_duration: int = 0) -> Tuple[Optional[str], List[str], int, float]:
        """Build initialization and segment URLs"""
        init_template = seg_template.get('initialization')
        media_template = seg_template.get('media')
        start_number = int(seg_template.get('startNumber', 1))
        timescale = int(seg_template.get('timescale', 1) or 1)
        duration_attr = seg_template.get('duration')
        
        # Build init URL
        init_url = None
        if init_template:
            init_url = URLBuilder.build_url(base_url, init_template, rep_id=rep_id, bandwidth=bandwidth)
        
        # Parse timeline
        number_list, time_list = self.timeline_parser.parse(seg_template, start_number)
        
        segment_count = 0
        segment_duration = 0.0
        
        # Determine segment count
        if time_list:
            segment_count = len(time_list)
        elif number_list:
            segment_count = len(number_list)
        elif duration_attr:

            # Estimate from duration
            d = int(duration_attr)
            segment_duration = d / float(timescale)
            
            if period_duration > 0 and segment_duration > 0:
                segment_count = int((period_duration / segment_duration) + 0.5)
            else:
                segment_count = 100
            
            max_segments = min(segment_count, 20000)
            number_list = list(range(start_number, start_number + max_segments))
        else:
            segment_count = 100
            number_list = list(range(start_number, start_number + 100))
        
        # Build segment URLs
        segment_urls = self._build_segment_urls(
            media_template, base_url, rep_id, bandwidth, number_list, time_list
        )
        
        if not segment_count:
            segment_count = len(segment_urls)
        
        return init_url, segment_urls, segment_count, segment_duration
    
    def _build_segment_urls(self, template: str, base_url: str, rep_id: str, bandwidth: int, number_list: List[int], time_list: List[int]) -> List[str]:
        """Build list of segment URLs"""
        if not template:
            return []
        
        urls = []
        
        if '$Time$' in template and time_list:
            for t in time_list:
                urls.append(URLBuilder.build_url(base_url, template, rep_id=rep_id, time=t, bandwidth=bandwidth))
        elif '$Number' in template and number_list:
            for n in number_list:
                urls.append(URLBuilder.build_url(base_url, template, rep_id=rep_id, number=n, bandwidth=bandwidth))
        else:
            urls.append(URLBuilder.build_url(base_url, template, rep_id=rep_id, bandwidth=bandwidth))
        
        return urls


class MetadataExtractor:
    """Extracts metadata from representations"""
    
    def __init__(self, ns_manager: NamespaceManager):
        self.ns = ns_manager
    
    def get_audio_channels(self, rep_elem: etree._Element, adapt_elem: etree._Element) -> int:
        """Extract audio channel count"""
        for parent in (rep_elem, adapt_elem):
            if parent is None:
                continue
            
            for acc in self.ns.findall(parent, 'mpd:AudioChannelConfiguration'):
                val = acc.get('value')
                if val:
                    try:
                        return int(val)
                    except ValueError:
                        pass
        return 0
    
    @staticmethod
    def parse_frame_rate(frame_rate: Optional[str]) -> float:
        """Parse frame rate (e.g., '25' or '30000/1001')"""
        if not frame_rate:
            return 0.0
        
        fr = frame_rate.strip()
        if '/' in fr:
            try:
                num, den = fr.split('/', 1)
                return float(num) / float(den)
            except Exception:
                return 0.0
        
        try:
            return float(fr)
        except Exception:
            return 0.0
    
    @staticmethod
    def determine_content_type(mime_type: str, width: int, height: int, audio_sampling_rate: int, codecs: str) -> str:
        """Determine if content is video, audio, or other"""
        if mime_type:
            return mime_type.split('/')[0]
        elif width or height:
            return 'video'
        elif audio_sampling_rate or (codecs and 'mp4a' in codecs.lower()):
            return 'audio'
        return 'unknown'
    
    @staticmethod
    def clean_language(lang: str, content_type: str, rep_id: str, bandwidth: int) -> Optional[str]:
        """Clean and normalize language tag"""
        if lang and lang.lower() not in ['undefined', 'none', '']:
            return lang
        elif content_type == 'audio':
            return f"aud_{rep_id}" if rep_id else f"aud_{bandwidth or 0}"
        return None


class RepresentationParser:
    """Parses DASH representations"""
    
    def __init__(self, ns_manager: NamespaceManager, url_resolver: BaseURLResolver):
        self.ns = ns_manager
        self.url_resolver = url_resolver
        self.segment_builder = SegmentURLBuilder(ns_manager)
        self.protection_handler = ContentProtectionHandler(ns_manager)
        self.metadata_extractor = MetadataExtractor(ns_manager)
    
    def parse_adaptation_set(
        self,
        adapt_set: etree._Element,
        base_url: str,
        period_duration: int = 0
    ) -> List[Dict[str, Any]]:
        """Parse all representations in adaptation set"""
        representations = []
        
        # Adaptation set attributes
        mime_type = adapt_set.get('mimeType', '')
        lang = adapt_set.get('lang', '')
        adapt_frame_rate = adapt_set.get('frameRate')
        content_type = adapt_set.get('contentType', '')
        
        # Resolve base URL
        adapt_base = self.url_resolver.resolve_base_url(adapt_set, base_url)
        
        # Check protection and extract default_KID
        adapt_protected = self.protection_handler.is_protected(adapt_set)
        adapt_default_kid = self.protection_handler.extract_default_kid(adapt_set)
        adapt_drm_types = self.protection_handler.get_drm_types(adapt_set)
        adapt_drm_type = self.protection_handler.get_primary_drm_type(adapt_set)
        
        # Get segment template
        adapt_seg_template = self.ns.find(adapt_set, 'mpd:SegmentTemplate')
        
        # Parse each representation
        for rep_elem in self.ns.findall(adapt_set, 'mpd:Representation'):
            rep = self._parse_representation(
                rep_elem, adapt_set, adapt_seg_template,
                adapt_base, mime_type, lang, period_duration
            )
            
            if rep:
                rep_frame_rate = rep_elem.get('frameRate') or adapt_frame_rate
                rep['frame_rate'] = self.metadata_extractor.parse_frame_rate(rep_frame_rate)
                rep['channels'] = self.metadata_extractor.get_audio_channels(rep_elem, adapt_set)
                rep_protected = adapt_protected or self.protection_handler.is_protected(rep_elem)
                rep['protected'] = bool(rep_protected)
                rep_default_kid = self.protection_handler.extract_default_kid(rep_elem) or adapt_default_kid
                rep['default_kid'] = rep_default_kid
                
                # Get all DRM types and primary DRM type
                rep_drm_types = self.protection_handler.get_drm_types(rep_elem) or adapt_drm_types
                rep_drm_type = self.protection_handler.get_primary_drm_type(rep_elem) or adapt_drm_type
                rep['drm_types'] = rep_drm_types
                rep['drm_type'] = rep_drm_type
                
                if content_type:
                    rep['type'] = content_type
                
                representations.append(rep)
        
        return representations
    
    def _parse_representation(self, rep_elem: etree._Element, adapt_set: etree._Element, adapt_seg_template: Optional[etree._Element], base_url: str, mime_type: str, lang: str, period_duration: int) -> Optional[Dict[str, Any]]:
        """Parse single representation"""
        rep_id = rep_elem.get('id')
        bandwidth = int(rep_elem.get('bandwidth', 0))
        codecs = rep_elem.get('codecs')
        width = int(rep_elem.get('width', 0))
        height = int(rep_elem.get('height', 0))
        audio_sampling_rate = int(rep_elem.get('audioSamplingRate', 0))
        
        # Find segment template
        rep_seg_template = self.ns.find(rep_elem, 'mpd:SegmentTemplate')
        seg_template = rep_seg_template if rep_seg_template is not None else adapt_seg_template
        
        # Handle SegmentBase (single file)
        if seg_template is None:
            return self._parse_segment_base(rep_elem, base_url, rep_id, bandwidth, codecs, width, height, audio_sampling_rate, mime_type, lang)
        
        # Build segment URLs
        rep_base = self.url_resolver.resolve_base_url(rep_elem, base_url)
        init_url, segment_urls, seg_count, seg_duration = self.segment_builder.build_urls(
            seg_template, rep_id, bandwidth, rep_base, period_duration
        )
        
        # Determine content type and language
        content_type = self.metadata_extractor.determine_content_type(mime_type, width, height, audio_sampling_rate, codecs)
        clean_lang = self.metadata_extractor.clean_language(lang, content_type, rep_id, bandwidth)
        
        rep_data = {
            'id': rep_id,
            'type': content_type,
            'codec': codecs,
            'bandwidth': bandwidth,
            'width': width,
            'height': height,
            'audio_sampling_rate': audio_sampling_rate,
            'language': clean_lang,
            'init_url': init_url,
            'segment_urls': segment_urls,
            'segment_count': seg_count,
        }
        
        if seg_duration:
            rep_data['segment_duration_seconds'] = seg_duration
        
        return rep_data
    
    def _parse_segment_base(self, rep_elem: etree._Element, base_url: str, rep_id: str, bandwidth: int, codecs: str, width: int, height: int, audio_sampling_rate: int, mime_type: str, lang: str) -> Optional[Dict[str, Any]]:
        """Parse representation with SegmentBase (single file)"""
        seg_base = self.ns.find(rep_elem, 'mpd:SegmentBase')
        rep_base = self.ns.find(rep_elem, 'mpd:BaseURL')
        
        if seg_base is None or rep_base is None or not (rep_base.text or "").strip():
            return None
        
        media_url = urljoin(base_url, rep_base.text.strip())
        content_type = self.metadata_extractor.determine_content_type(mime_type, width, height, audio_sampling_rate, codecs)
        clean_lang = self.metadata_extractor.clean_language(lang, content_type, rep_id, bandwidth)
        
        return {
            'id': rep_id,
            'type': content_type,
            'codec': codecs,
            'bandwidth': bandwidth,
            'width': width,
            'height': height,
            'audio_sampling_rate': audio_sampling_rate,
            'language': clean_lang,
            'init_url': media_url,
            'segment_urls': [media_url],
            'segment_count': 1,
        }


class RepresentationFilter:
    """Filters and deduplicates representations"""
    
    @staticmethod
    def deduplicate_by_quality(reps: List[Dict[str, Any]], content_type: str) -> List[Dict[str, Any]]:
        """Keep BEST quality representation per resolution/language"""
        quality_map = {}
        
        # Define grouping key based on content type
        def get_grouping_key(rep):
            if content_type == 'video':
                return (rep['width'], rep['height'])
            else:  # audio
                return (rep['language'], rep['audio_sampling_rate'])
        
        # Define quality comparison
        def get_quality_rank(rep):
            if content_type == 'video':
                return CodecQuality.get_video_codec_rank(rep['codec'])
            else:
                return CodecQuality.get_audio_codec_rank(rep['codec'])
        
        # Group and select best quality
        for rep in reps:
            key = get_grouping_key(rep)
            
            if key not in quality_map:
                quality_map[key] = rep
            else:
                existing = quality_map[key]
                existing_rank = get_quality_rank(existing)
                new_rank = get_quality_rank(rep)
                
                # Select BEST quality (higher codec rank or higher bandwidth)
                if new_rank > existing_rank or (new_rank == existing_rank and rep['bandwidth'] > existing['bandwidth']):
                    quality_map[key] = rep
        
        return list(quality_map.values())
    
    @staticmethod
    def deduplicate_videos(reps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep best video per resolution"""
        return RepresentationFilter.deduplicate_by_quality(reps, 'video')
    
    @staticmethod
    def deduplicate_audios(reps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep best audio per language"""
        return RepresentationFilter.deduplicate_by_quality(reps, 'audio')


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


class FileTypeDetector:
    """Detects file types from URLs"""
    
    @staticmethod
    def infer_url_type(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        try:
            path = urlparse(url).path
            ext = Path(path).suffix
            return ext.lstrip(".").lower() if ext else None
        except Exception:
            return None
    
    @staticmethod
    def infer_segment_urls_type(urls: Optional[List[str]]) -> Optional[str]:
        if not urls:
            return None
        
        types = {FileTypeDetector.infer_url_type(u) for u in urls if u}
        types.discard(None)
        
        if not types:
            return None
        return next(iter(types)) if len(types) == 1 else "mixed"


class TablePrinter:
    """Prints representation tables"""
    
    def __init__(self, mpd_duration: int, mpd_sub_list: list = None):
        self.mpd_duration = mpd_duration
        self.mpd_sub_list = mpd_sub_list or []
    
    def print_table(self, representations: List[Dict[str, Any]], selected_video: Optional[Dict[str, Any]] = None, selected_audio: Optional[Dict[str, Any]] = None, selected_subs: list = None, available_drm_types: list = None):
        """Print tracks table using Rich tables"""
        approx = DurationUtils.format_duration(self.mpd_duration)
        
        videos = sorted([r for r in representations if r['type'] == 'video'], 
                       key=lambda r: (r['height'], r['width'], r['bandwidth']), reverse=True)
        audios = sorted([r for r in representations if r['type'] == 'audio'], 
                       key=lambda r: r['bandwidth'], reverse=True)
        
        # Create main tracks table with DRM column
        table = Table(show_header=True, header_style="bold")
        table.add_column("Type", style="cyan")
        table.add_column("Sel", width=3, style="green bold")
        table.add_column("Info", style="white")
        table.add_column("Resolution/ID", style="yellow")
        table.add_column("Bitrate", style="green")
        table.add_column("Codec", style="white")
        table.add_column("Lang/FPS", style="blue")
        table.add_column("Channels", style="magenta")
        table.add_column("Segments", style="white")
        table.add_column("Duration", style="white")
        table.add_column("DRM", style="red")
        
        # Add video tracks
        for vid in videos:
            checked = 'X' if selected_video and vid['id'] == selected_video['id'] else ' '
            drm_info = self._get_drm_display(vid)
            drm_systems = self._get_drm_systems_display(vid)
            fps = f"{vid['frame_rate']:.0f}" if vid.get('frame_rate') else ""
            
            table.add_row("Video", checked, drm_info, f"{vid['width']}x{vid['height']}", f"{vid['bandwidth'] // 1000} Kbps", vid.get('codec', ''), fps, vid['id'], str(vid['segment_count']), approx or "", drm_systems)
        
        # Add audio tracks
        for aud in audios:
            checked = 'X' if selected_audio and aud['id'] == selected_audio['id'] else ' '
            drm_info = self._get_drm_display(aud)
            drm_systems = self._get_drm_systems_display(aud)
            ch = f"{aud['channels']}CH" if aud.get('channels') else ""
            
            table.add_row("Audio", checked, drm_info, aud['id'], f"{aud['bandwidth'] // 1000} Kbps", aud.get('codec', ''), aud.get('language', ''), ch, str(aud['segment_count']), approx or "", drm_systems)
        
        # Add subtitle tracks from mpd_sub_list
        if self.mpd_sub_list:
            for sub in self.mpd_sub_list:
                checked = 'X' if selected_subs and sub in selected_subs else ' '
                language = sub.get('language')
                sub_type = str(sub.get('format')).upper()
                table.add_row("Subtitle", checked, f"Sub ({sub_type})", language, "", "", language, "", "", approx or "", "")
        
        console.print(table)
    
    def _get_drm_display(self, rep: Dict[str, Any]) -> str:
        """Generate DRM display string for table (only shows CENC)"""
        content_type = "Vid" if rep['type'] == 'video' else "Aud"
        
        if not rep.get('protected'):
            return content_type
        
        return f"{content_type} *CENC"
    
    def _get_drm_systems_display(self, rep: Dict[str, Any]) -> str:
        """Generate DRM systems display for the DRM column"""
        if not rep.get('protected'):
            return ""
        
        # Get all DRM types available for this stream
        drm_types = rep.get('drm_types', [])
        if not drm_types:
            drm_type = rep.get('drm_type', '').lower()
            if drm_type:
                drm_types = [drm_type]
        
        if not drm_types:
            return "DRM"
        
        # Create abbreviations using DRMSystem utility
        drm_abbrevs = [DRMSystem.get_abbrev(drm) for drm in drm_types]
        
        # Join multiple DRM systems with +
        return '+'.join(drm_abbrevs)


class MPD_Parser:
    """Main MPD parser class"""
    
    def __init__(self, mpd_url: str, auto_save: bool = True, save_dir: Optional[str] = None, mpd_sub_list: list = None):
        self.mpd_url = mpd_url
        self.auto_save = auto_save
        self.save_dir = Path(save_dir) if save_dir else None
        self.mpd_sub_list = mpd_sub_list or []
        
        self.root = None
        self.mpd_content = None
        self.pssh = None
        self.representations = []
        self.mpd_duration = 0
        
        # Initialize utility classes (will be set after parsing)
        self.ns_manager = None
        self.url_resolver = None
        self.protection_handler = None
        self.rep_parser = None
        self.table_printer = None
    
    def parse(self, custom_headers: Optional[Dict[str, str]] = None) -> None:
        """Parse the MPD file and extract all representations"""
        self._fetch_and_parse_mpd(custom_headers or {})
        
        # Initialize utility classes
        self.ns_manager = NamespaceManager(self.root)
        self.url_resolver = BaseURLResolver(self.mpd_url, self.ns_manager)
        self.protection_handler = ContentProtectionHandler(self.ns_manager)
        self.rep_parser = RepresentationParser(self.ns_manager, self.url_resolver)
        
        # Extract MPD duration
        duration_str = self.root.get('mediaPresentationDuration')
        self.mpd_duration = DurationUtils.parse_duration(duration_str)
        
        # Extract PSSH for all DRM types using DRMSystem constants
        self.pssh_widevine = self.protection_handler.extract_pssh(self.root, DRMSystem.WIDEVINE)
        self.pssh_playready = self.protection_handler.extract_pssh(self.root, DRMSystem.PLAYREADY)
        self.pssh_fairplay = self.protection_handler.extract_pssh(self.root, DRMSystem.FAIRPLAY)
        
        # Get all available DRM types
        self.available_drm_types = []
        if self.pssh_widevine:
            self.available_drm_types.append(DRMSystem.WIDEVINE)
        if self.pssh_playready:
            self.available_drm_types.append(DRMSystem.PLAYREADY)
        if self.pssh_fairplay:
            self.available_drm_types.append(DRMSystem.FAIRPLAY)
        
        # Legacy support: set pssh to widevine by default
        self.pssh = self.pssh_widevine or self.pssh_playready or self.pssh_fairplay
        
        self._parse_representations()
        self._deduplicate_representations()
        self._extract_and_merge_subtitles()
        self.table_printer = TablePrinter(self.mpd_duration, self.mpd_sub_list)
        
        # Auto-save if enabled
        if self.auto_save:
            self._auto_save_files()
    
    def _fetch_and_parse_mpd(self, custom_headers: Dict[str, str]) -> None:
        """Fetch MPD content and parse XML"""
        response = requests.get(self.mpd_url, headers=custom_headers, timeout=max_timeout, impersonate="chrome124")
        response.raise_for_status()
        
        logging.info(f"Successfully fetched MPD: {len(response.content)} bytes")
        self.mpd_content = response.content
        self.root = etree.fromstring(response.content)
    
    def _parse_representations(self) -> None:
        """Parse all representations from the MPD"""
        base_url = self.url_resolver.get_initial_base_url(self.root)
        rep_aggregator = {}
        
        periods = self.ns_manager.findall(self.root, './/mpd:Period')
        
        for period_idx, period in enumerate(periods):
            #period_id = period.get('id', f'period_{period_idx}')
            period_base_url = self.url_resolver.resolve_base_url(period, base_url)
            
            # Get period duration and protection info
            period_duration_str = period.get('duration')
            period_duration = DurationUtils.parse_duration(period_duration_str) or self.mpd_duration
            period_protected = self.protection_handler.is_protected(period)
            period_drm_types = self.protection_handler.get_drm_types(period)
            period_drm_type = self.protection_handler.get_primary_drm_type(period)
            
            # Parse adaptation sets
            for adapt_set in self.ns_manager.findall(period, 'mpd:AdaptationSet'):
                representations = self.rep_parser.parse_adaptation_set(
                    adapt_set, period_base_url, period_duration
                )
                
                # Apply Period-level protection if needed
                for rep in representations:
                    if not rep.get('protected') and period_protected:
                        rep['protected'] = True
                        if not rep.get('drm_types'):
                            rep['drm_types'] = period_drm_types
                        if not rep.get('drm_type'):
                            rep['drm_type'] = period_drm_type
                
                # Aggregate representations with unique keys
                self._aggregate_representations(rep_aggregator, representations)
        
        self.representations = list(rep_aggregator.values())
    
    def _aggregate_representations(self, aggregator: dict, representations: List[Dict]) -> None:
        """Aggregate representations with unique keys (helper method)"""
        for rep in representations:
            rep_id = rep['id']
            unique_key = f"{rep_id}_{rep.get('protected', False)}_{rep.get('width', 0)}x{rep.get('height', 0)}"
            
            if unique_key not in aggregator:
                aggregator[unique_key] = rep
            else:
                # Concatenate segment URLs for multi-period content
                existing = aggregator[unique_key]
                if rep['segment_urls']:
                    existing['segment_urls'].extend(rep['segment_urls'])
                if not existing['init_url'] and rep['init_url']:
                    existing['init_url'] = rep['init_url']
    
    def _deduplicate_representations(self) -> None:
        """Remove duplicate representations - KEEP BEST QUALITY regardless of DRM"""
        videos = [r for r in self.representations if r['type'] == 'video']
        audios = [r for r in self.representations if r['type'] == 'audio']
        others = [r for r in self.representations if r['type'] not in ['video', 'audio']]
        
        deduplicated_videos = RepresentationFilter.deduplicate_by_quality(videos, 'video')
        deduplicated_audios = RepresentationFilter.deduplicate_by_quality(audios, 'audio')
        
        self.representations = deduplicated_videos + deduplicated_audios + others
    
    def get_resolutions(self) -> List[Dict[str, Any]]:
        """Return list of video representations"""
        return [r for r in self.representations if r['type'] == 'video']
    
    def get_audios(self) -> List[Dict[str, Any]]:
        """Return list of audio representations"""
        return [r for r in self.representations if r['type'] == 'audio']
    
    def get_best_video(self) -> Optional[Dict[str, Any]]:
        """Return the best video representation"""
        videos = self.get_resolutions()
        if not videos:
            return None
        return max(videos, key=lambda r: (r['height'], r['width'], r['bandwidth']))
    
    def get_best_audio(self) -> Optional[Dict[str, Any]]:
        """Return the best audio representation"""
        audios = self.get_audios()
        if not audios:
            return None
        return max(audios, key=lambda r: r['bandwidth'])
    
    @staticmethod
    def get_worst(representations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Return the worst representation"""
        videos = [r for r in representations if r['type'] == 'video']
        audios = [r for r in representations if r['type'] == 'audio']
        
        if videos:
            return min(videos, key=lambda r: (r['height'], r['width'], r['bandwidth']))
        elif audios:
            return min(audios, key=lambda r: r['bandwidth'])
        return None
    
    @staticmethod
    def get_list(representations: List[Dict[str, Any]], type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return filtered list of representations"""
        if type_filter:
            return [r for r in representations if r['type'] == type_filter]
        return representations
    
    def select_video(self, force_resolution: str = None) -> Tuple[Optional[Dict[str, Any]], List[str], str, str]:
        """Select video representation based on resolution preference"""
        video_reps = self.get_resolutions()
        available_resolutions = [f"{rep['width']}x{rep['height']}" for rep in video_reps]
        resolution = (force_resolution or FILTER_CUSTOM_RESOLUTION or "best").lower()
        
        # Select based on preference
        if resolution == "best":
            selected_video = self.get_best_video()
            filter_custom_resolution = "Best"
        elif resolution == "worst":
            selected_video = self.get_worst(video_reps)
            filter_custom_resolution = "Worst"
        else:
            # Try to find specific resolution
            selected_video = self._find_specific_resolution(video_reps, resolution)
            filter_custom_resolution = resolution if selected_video else f"{resolution} (fallback to Best)"
            if not selected_video:
                selected_video = self.get_best_video()
        
        downloadable_video = f"{selected_video['width']}x{selected_video['height']}" if selected_video else "N/A"
        return selected_video, available_resolutions, filter_custom_resolution, downloadable_video
    
    def _find_specific_resolution(self, video_reps: List[Dict], resolution: str) -> Optional[Dict]:
        """Find video representation matching specific resolution"""
        for rep in video_reps:
            rep_res = f"{rep['width']}x{rep['height']}"
            if (resolution in rep_res.lower() or 
                resolution.replace('p', '') in str(rep['height']) or
                rep_res.lower() == resolution):
                return rep
        return None
    
    def select_audio(self, preferred_audio_langs: Optional[List[str]] = None) -> Tuple[Optional[Dict[str, Any]], List[str], str, str]:
        """Select audio representation based on language preference"""
        audio_reps = self.get_audios()
        available_langs = [rep['language'] for rep in audio_reps if rep['language']]
        preferred_langs = preferred_audio_langs or DOWNLOAD_SPECIFIC_AUDIO
        
        # Try to find preferred language
        selected_audio = None
        filter_custom_audio = "First"
        
        if preferred_langs:
            for lang in preferred_langs:
                for rep in audio_reps:
                    if rep['language'] and rep['language'].lower() == lang.lower():
                        selected_audio = rep
                        filter_custom_audio = lang
                        break
                if selected_audio:
                    break
        
        if not selected_audio:
            selected_audio = self.get_best_audio()
        
        downloadable_audio = selected_audio['language'] if selected_audio else "N/A"
        return selected_audio, available_langs, filter_custom_audio, downloadable_audio
    
    def print_tracks_table(self, selected_video: Optional[Dict[str, Any]] = None, selected_audio: Optional[Dict[str, Any]] = None, selected_subs: list = None) -> None:
        """Print tracks table"""
        if self.table_printer:
            self.table_printer.print_table(self.representations, selected_video, selected_audio, selected_subs, self.available_drm_types)
    
    def save_mpd(self, output_path: str) -> None:
        """Save raw MPD manifest"""
        if self.mpd_content is None:
            raise ValueError("MPD content not available. Call parse() first.")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'wb') as f:
            f.write(self.mpd_content)
        
        logging.info(f"MPD manifest saved to: {output_file}")
    
    def save_best_video_json(self, output_path: str) -> None:
        """Save best video representation as JSON"""
        best_video = self.get_best_video()
        if best_video is None:
            raise ValueError("No video representation available.")
        
        video_json = dict(best_video)
        video_json["stream_type"] = "dash"
        video_json["init_url_type"] = FileTypeDetector.infer_url_type(video_json.get("init_url"))
        video_json["segment_url_type"] = FileTypeDetector.infer_segment_urls_type(video_json.get("segment_urls"))
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(video_json, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Best video JSON saved to: {output_file}")
    
    def save_best_audio_json(self, output_path: str) -> None:
        """Save best audio representation as JSON"""
        best_audio = self.get_best_audio()
        if best_audio is None:
            raise ValueError("No audio representation available.")
        
        audio_json = dict(best_audio)
        audio_json["stream_type"] = "dash"
        audio_json["init_url_type"] = FileTypeDetector.infer_url_type(audio_json.get("init_url"))
        audio_json["segment_url_type"] = FileTypeDetector.infer_segment_urls_type(audio_json.get("segment_urls"))
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(audio_json, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Best audio JSON saved to: {output_file}")
    
    def _auto_save_files(self) -> None:
        """Auto-save MPD files to tmp directory"""
        if not self.save_dir:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_dir.mkdir(parents=True, exist_ok=True)
            
            # Save MPD manifest
            mpd_path = self.save_dir / f"manifest_{timestamp}.mpd"
            self.save_mpd(str(mpd_path))
            
            # Save JSON files
            if self.get_best_video():
                video_path = self.save_dir / f"best_video_{timestamp}.json"
                self.save_best_video_json(str(video_path))
            
            if self.get_best_audio():
                audio_path = self.save_dir / f"best_audio_{timestamp}.json"
                self.save_best_audio_json(str(audio_path))
            
        except Exception as e:
            console.print(f"[red]Error during auto-save: {e}")
    
    def _extract_and_merge_subtitles(self) -> None:
        """Extract subtitles from MPD manifest and merge with external mpd_sub_list"""
        base_url = self.url_resolver.get_initial_base_url(self.root)
        extracted_subs = []
        seen_subs = set()
        
        periods = self.ns_manager.findall(self.root, './/mpd:Period')
        
        for period in periods:
            period_base_url = self.url_resolver.resolve_base_url(period, base_url)
            
            for adapt_set in self.ns_manager.findall(period, 'mpd:AdaptationSet'):
                if adapt_set.get('contentType', '') != 'text':
                    continue
                
                self._extract_subtitle_from_adaptation_set(
                    adapt_set, period_base_url, extracted_subs, seen_subs
                )
        
        # Merge with external subtitles
        self._merge_external_subtitles(extracted_subs)
    
    def _extract_subtitle_from_adaptation_set(self, adapt_set, period_base_url, extracted_subs, seen_subs):
        """Extract subtitle from a single adaptation set (helper method)"""
        language = adapt_set.get('lang', 'unknown')
        label_elem = self.ns_manager.find(adapt_set, 'mpd:Label')
        label = label_elem.text.strip() if label_elem is not None and label_elem.text else None
        
        for rep_elem in self.ns_manager.findall(adapt_set, 'mpd:Representation'):
            mime_type = rep_elem.get('mimeType', '')
            rep_id = rep_elem.get('id', '')
            
            # Determine format
            sub_format = self._determine_subtitle_format(mime_type)
            
            # Try SegmentTemplate first, then BaseURL
            seg_template = self.ns_manager.find(rep_elem, 'mpd:SegmentTemplate') or self.ns_manager.find(adapt_set, 'mpd:SegmentTemplate')
            
            if seg_template is not None:
                self._process_subtitle_template(seg_template, rep_elem, rep_id, period_base_url, language, label, sub_format, extracted_subs, seen_subs)
            else:
                self._process_subtitle_baseurl(rep_elem, period_base_url, language, label, sub_format, rep_id, extracted_subs, seen_subs)
    
    def _determine_subtitle_format(self, mime_type: str) -> str:
        """Determine subtitle format from mimeType"""
        mime_lower = mime_type.lower()
        if 'vtt' in mime_lower:
            return 'vtt'
        elif 'ttml' in mime_lower or 'xml' in mime_lower:
            return 'ttml'
        elif 'srt' in mime_lower:
            return 'srt'
        return 'vtt'
    
    def _process_subtitle_template(self, seg_template, rep_elem, rep_id, period_base_url, language, label, sub_format, extracted_subs, seen_subs):
        """Process subtitle with SegmentTemplate"""
        media_template = seg_template.get('media')
        if not media_template:
            return
        
        number_list, time_list = SegmentTimelineParser(self.ns_manager).parse(seg_template, 1)
        rep_base = self.url_resolver.resolve_base_url(rep_elem, period_base_url)
        
        # Build segment URLs
        segment_urls = []
        if '$Time$' in media_template and time_list:
            segment_urls = [URLBuilder.build_url(rep_base, media_template, rep_id=rep_id, time=t) for t in time_list]
        elif '$Number' in media_template and number_list:
            segment_urls = [URLBuilder.build_url(rep_base, media_template, rep_id=rep_id, number=n) for n in number_list]
        else:
            segment_urls = [URLBuilder.build_url(rep_base, media_template, rep_id=rep_id)]
        
        if not segment_urls:
            return
        
        # Create subtitle entry
        first_url = segment_urls[0]
        unique_key = f"{language}_{label}_{first_url}"
        
        if unique_key not in seen_subs:
            seen_subs.add(unique_key)
            extracted_subs.append({
                'language': language,
                'label': label or language,
                'format': sub_format,
                'url': segment_urls[0] if len(segment_urls) == 1 else None,
                'segment_urls': segment_urls if len(segment_urls) > 1 else None,
                'id': rep_id
            })
    
    def _process_subtitle_baseurl(self, rep_elem, period_base_url, language, label, sub_format, rep_id, extracted_subs, seen_subs):
        """Process subtitle with BaseURL"""
        base_url_elem = self.ns_manager.find(rep_elem, 'mpd:BaseURL')
        if base_url_elem is None or not base_url_elem.text:
            return
        
        url = urljoin(period_base_url, base_url_elem.text.strip())
        unique_key = f"{language}_{label}_{url}"
        
        if unique_key not in seen_subs:
            seen_subs.add(unique_key)
            extracted_subs.append({
                'language': language,
                'label': label or language,
                'format': sub_format,
                'url': url,
                'id': rep_id
            })
    
    def _merge_external_subtitles(self, extracted_subs):
        """Merge extracted subtitles with external list"""
        existing_keys = set()
        
        # Track existing subtitles
        for sub in self.mpd_sub_list:
            if sub.get('language'):
                first_url = sub.get('segment_urls', [None])[0] if sub.get('segment_urls') else sub.get('url', '')
                sub_key = f"{sub['language']}_{sub.get('label')}_{first_url}"
                existing_keys.add(sub_key)
        
        # Add new subtitles
        for sub in extracted_subs:
            first_url = sub.get('segment_urls', [None])[0] if sub.get('segment_urls') else sub.get('url', '')
            sub_key = f"{sub['language']}_{sub.get('label')}_{first_url}"
            
            if sub_key not in existing_keys:
                self.mpd_sub_list.append(sub)
                existing_keys.add(sub_key)