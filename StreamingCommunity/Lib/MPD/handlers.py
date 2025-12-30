# 29.12.25

from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urljoin


# External library
from lxml import etree
from rich.console import Console


# Logic
from .constants import DRMSystem, CodecQuality
from .utils import URLBuilder, NamespaceManager, MetadataExtractor


# Variable
console = Console()


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
    
    def get_encryption_method(self, element: etree._Element) -> Optional[str]:
        """
        Extract encryption method from ContentProtection elements.
        Returns: 'ctr', 'cbc', 'cenc', 'cbcs', 'cbc1', 'cens' or None
        """
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            value = (cp.get('value') or '').lower()
            
            # Check CENC scheme with value attribute
            if DRMSystem.CENC_SCHEME in scheme_id and value:
                if value in ['cenc', 'cens']:
                    return 'ctr'  # AES CTR mode
                elif value in ['cbc1', 'cbcs']:
                    return 'cbc'  # AES CBC mode
                return value
        
        return None
    
    def get_drm_types(self, element: etree._Element) -> List[str]:
        """Determine all DRM types from ContentProtection elements that actually have PSSH data."""
        drm_types = []
        
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            drm_type = DRMSystem.from_uuid(scheme_id)
            
            if drm_type and drm_type not in drm_types:
                if self._has_pssh_data(cp, drm_type):
                    drm_types.append(drm_type)
        
        return drm_types
    
    def _has_pssh_data(self, cp_element: etree._Element, drm_type: str) -> bool:
        """Check if ContentProtection element has actual PSSH data for the DRM type."""
        pssh = self.ns.find(cp_element, 'cenc:pssh')
        if pssh is not None and pssh.text and pssh.text.strip():
            return True
        
        # For PlayReady, check mspr:pro
        if drm_type == DRMSystem.PLAYREADY:
            pro = self.ns.find(cp_element, 'mspr:pro')
            if pro is not None and pro.text and pro.text.strip():
                return True
        return False
    
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
                if pssh is not None and pssh.text and pssh.text.strip():
                    return pssh.text.strip()
                
                if drm_type == DRMSystem.PLAYREADY:
                    pro = self.ns.find(cp, 'mspr:pro')
                    if pro is not None and pro.text and pro.text.strip():
                        return pro.text.strip()
        
        return None


class SegmentTimelineParser:
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


class RepresentationParser:
    def __init__(self, ns_manager: NamespaceManager, url_resolver):
        self.ns = ns_manager
        self.url_resolver = url_resolver
        self.segment_builder = SegmentURLBuilder(ns_manager)
        self.protection_handler = ContentProtectionHandler(ns_manager)
        self.metadata_extractor = MetadataExtractor(ns_manager)
    
    def parse_adaptation_set(self, adapt_set: etree._Element, base_url: str, period_duration: int = 0) -> List[Dict[str, Any]]:
        """Parse all representations in adaptation set"""
        representations = []
        
        # Adaptation set attributes
        mime_type = adapt_set.get('mimeType', '')
        lang = adapt_set.get('lang', '')
        adapt_frame_rate = adapt_set.get('frameRate')
        content_type = adapt_set.get('contentType', '')
        adapt_width = int(adapt_set.get('width', 0))
        adapt_height = int(adapt_set.get('height', 0))
        
        # Resolve base URL
        adapt_base = self.url_resolver.resolve_base_url(adapt_set, base_url)
        
        # Check protection and extract default_KID and encryption method
        adapt_protected = self.protection_handler.is_protected(adapt_set)
        adapt_default_kid = self.protection_handler.extract_default_kid(adapt_set)
        adapt_encryption_method = self.protection_handler.get_encryption_method(adapt_set)
        adapt_drm_types = self.protection_handler.get_drm_types(adapt_set)
        adapt_drm_type = self.protection_handler.get_primary_drm_type(adapt_set)
        
        # Get segment template
        adapt_seg_template = self.ns.find(adapt_set, 'mpd:SegmentTemplate')
        
        # Parse each representation
        for rep_elem in self.ns.findall(adapt_set, 'mpd:Representation'):
            rep_mime_type = rep_elem.get('mimeType', mime_type)
            if rep_mime_type and 'webm' in rep_mime_type.lower():
                continue
            
            rep = self._parse_representation(
                rep_elem, adapt_set, adapt_seg_template,
                adapt_base, mime_type, lang, period_duration,
                adapt_width, adapt_height
            )
            
            if rep:
                rep_frame_rate = rep_elem.get('frameRate') or adapt_frame_rate
                rep['frame_rate'] = self.metadata_extractor.parse_frame_rate(rep_frame_rate)
                rep['channels'] = self.metadata_extractor.get_audio_channels(rep_elem, adapt_set)
                rep_protected = adapt_protected or self.protection_handler.is_protected(rep_elem)
                rep['protected'] = bool(rep_protected)
                rep_default_kid = self.protection_handler.extract_default_kid(rep_elem) or adapt_default_kid
                rep['default_kid'] = rep_default_kid
                rep_encryption_method = self.protection_handler.get_encryption_method(rep_elem) or adapt_encryption_method
                rep['encryption_method'] = rep_encryption_method
                
                # Get all DRM types and primary DRM type
                rep_drm_types = self.protection_handler.get_drm_types(rep_elem) or adapt_drm_types
                rep_drm_type = self.protection_handler.get_primary_drm_type(rep_elem) or adapt_drm_type
                rep['drm_types'] = rep_drm_types
                rep['drm_type'] = rep_drm_type
                
                if content_type:
                    rep['type'] = content_type
                
                representations.append(rep)
        
        return representations
    
    def _parse_representation(self, rep_elem: etree._Element, adapt_set: etree._Element, 
                             adapt_seg_template: Optional[etree._Element], base_url: str, 
                             mime_type: str, lang: str, period_duration: int,
                             adapt_width: int = 0, adapt_height: int = 0) -> Optional[Dict[str, Any]]:
        """Parse single representation"""
        rep_id = rep_elem.get('id')
        bandwidth = int(rep_elem.get('bandwidth', 0))
        codecs = rep_elem.get('codecs')
  
        width = int(rep_elem.get('width') or adapt_width or 0)
        height = int(rep_elem.get('height') or adapt_height or 0)
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
    
    def _parse_segment_base(self, rep_elem: etree._Element, base_url: str, rep_id: str, 
                           bandwidth: int, codecs: str, width: int, height: int, 
                           audio_sampling_rate: int, mime_type: str, lang: str) -> Optional[Dict[str, Any]]:
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