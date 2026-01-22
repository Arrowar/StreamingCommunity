# 10.01.26

import base64
import binascii
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Tuple


# External libraries
from curl_cffi import requests
from rich.console import Console


# Variable
console = Console()


class DRMSystem:
    """DRM system constants and utilities."""
    WIDEVINE = 'widevine'
    PLAYREADY = 'playready'
    FAIRPLAY = 'fairplay'
    
    UUIDS = {
        WIDEVINE: 'edef8ba9-79d6-4ace-a3c8-27dcd51d21ed',
        PLAYREADY: '9a04f079-9840-4286-ab92-e65be0885f95',
        FAIRPLAY: '94ce86fb-07ff-4f43-adb8-93d2fa968ca2'
    }
    
    ABBREV = {
        WIDEVINE: 'WV',
        PLAYREADY: 'PR',
        FAIRPLAY: 'FP'
    }
    
    PRIORITY = [WIDEVINE, PLAYREADY, FAIRPLAY]
    CENC_SCHEME = 'urn:mpeg:dash:mp4protection:2011'
    
    @classmethod
    def get_uuid(cls, drm_type: str) -> Optional[str]:
        return cls.UUIDS.get(drm_type.lower())
    
    @classmethod
    def get_abbrev(cls, drm_type: str) -> str:
        return cls.ABBREV.get(drm_type.lower(), drm_type.upper()[:2])
    
    @classmethod
    def from_uuid(cls, uuid: str) -> Optional[str]:
        u = uuid.lower()
        return next((t for t, v in cls.UUIDS.items() if v in u), None)


class MPDParser:
    def __init__(self, mpd_url: str, headers: Dict[str, str] = None, timeout: int = 30):
        self.mpd_url = mpd_url
        self.headers = headers or {}
        self.timeout = timeout
        self.root = None
        self.namespace_map = {}
    
    def parse(self) -> bool:
        """Parse MPD from URL."""
        try:
            r = requests.get(self.mpd_url, headers=self.headers, timeout=self.timeout, impersonate="chrome142")
            r.raise_for_status()
            self.root = ET.fromstring(r.content)
            self._extract_namespaces()
            return True
        
        except Exception as e:
            console.print(f"[red]Error parsing MPD: {e}")
            return False
    
    def parse_from_file(self, file_path: str) -> bool:
        """Parse MPD from a local file."""
        try:
            self.root = ET.parse(file_path).getroot()
            self._extract_namespaces()
            return True
        except Exception:
            # Fallback to URL parsing
            return self.parse()
    
    def _extract_namespaces(self):
        """Extract and register namespaces from XML root."""
        self.namespace_map = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
        
        # Common namespaces
        common_ns = {
            'cenc': 'urn:mpeg:cenc:2013',
            'mspr': 'urn:microsoft:playready'
        }
        
        # Register namespaces
        for prefix, uri in {**self.namespace_map, **common_ns}.items():
            ET.register_namespace(prefix, uri)
            self.namespace_map[prefix] = uri
    
    def _xpath(self, path: str) -> str:
        """Convert path with namespace prefixes to full namespace URIs."""
        for prefix, uri in self.namespace_map.items():
            path = path.replace(f'{prefix}:', f'{{{uri}}}')
        return path
    
    def _find(self, element: ET.Element, path: str) -> Optional[ET.Element]:
        """Find element with namespace handling."""
        return element.find(self._xpath(path), self.namespace_map)
    
    def _findall(self, element: ET.Element, path: str) -> List[ET.Element]:
        """Find all elements with namespace handling."""
        return element.findall(self._xpath(path), self.namespace_map)
    
    def _is_protected(self, element: ET.Element) -> bool:
        """Check if element has DRM protection."""
        for cp in self._findall(element, 'mpd:ContentProtection'):
            scheme = cp.get('schemeIdUri', '').lower()
            if (DRMSystem.CENC_SCHEME in scheme or 
                DRMSystem.from_uuid(scheme) is not None):
                return True
        return False
    
    def _get_default_kid(self, element: ET.Element) -> Optional[str]:
        """Extract default_KID from ContentProtection elements."""
        for cp in self._findall(element, 'mpd:ContentProtection'):
            cenc_ns = self.namespace_map.get('cenc', '')
            kid = cp.get(f'{{{cenc_ns}}}default_KID') or cp.get('default_KID')
            if kid:
                return kid
        return None
    
    def _get_drm_types(self, element: ET.Element) -> List[str]:
        """Extract DRM types from element."""
        drm_types = []
        for cp in self._findall(element, 'mpd:ContentProtection'):
            scheme = cp.get('schemeIdUri', '').lower()
            drm_type = DRMSystem.from_uuid(scheme)
            if drm_type and drm_type not in drm_types:
                # Check for PSSH data
                if self._has_pssh_data(cp, drm_type):
                    drm_types.append(drm_type)
        return drm_types
    
    def _has_pssh_data(self, cp_element: ET.Element, drm_type: str) -> bool:
        """Check if element has valid PSSH data."""
        # Check for cenc:pssh
        pssh = self._find(cp_element, 'cenc:pssh')
        if pssh is not None and pssh.text and pssh.text.strip():
            return self._is_valid_pssh(pssh.text.strip(), drm_type)
        
        # Check for playready pro
        if drm_type == DRMSystem.PLAYREADY:
            pro = self._find(cp_element, 'mspr:pro')
            return (pro is not None and pro.text and pro.text.strip() and 
                    self._is_valid_pro(pro.text.strip()))
        
        return False
    
    def _is_valid_pssh(self, pssh_b64: str, drm_type: str) -> bool:
        """Verify if PSSH is valid for given DRM type."""
        try:
            data = base64.b64decode(pssh_b64)
            uuid = DRMSystem.get_uuid(drm_type)
            return (uuid and len(data) >= 32 and 
                    data[4:8] == b'pssh' and 
                    data[12:28] == binascii.unhexlify(uuid.replace('-', '')))
        except Exception:
            return False
    
    def _is_valid_pro(self, pro_b64: str) -> bool:
        """Verify if PlayReady Object is valid."""
        try:
            data = base64.b64decode(pro_b64)
            return len(data) >= 10 and int.from_bytes(data[:4], 'little') == len(data)
        except Exception:
            return False
    
    def _get_content_info(self, adapt_set: ET.Element) -> Tuple[str, str]:
        """Extract content type and language from adaptation set."""
        c_type = (adapt_set.get('contentType') or adapt_set.get('mimeType') or '').lower()
        content_type = 'video' if 'video' in c_type else 'audio' if 'audio' in c_type else 'unknown'
        lang = adapt_set.get('lang', 'N/A')
        return content_type, lang
    
    def get_adaptation_sets_info(self, selected_ids=None, selected_kids=None, selected_langs=None, selected_periods=None):
        """Get information about all AdaptationSets."""
        if not self.root:
            return []
        
        adaptation_sets = []
        idx = 1
        
        # Normalize filter parameters
        norm_selected_ids = [str(i) for i in (selected_ids or [])]
        norm_selected_kids = [k.lower().replace('-', '') for k in (selected_kids or []) if k]
        norm_selected_langs = [lang.lower() for lang in (selected_langs or []) if lang]
        norm_selected_periods = [str(p) for p in (selected_periods or []) if p]
        
        for period in self._findall(self.root, 'mpd:Period'):
            period_id = period.get('id')
            
            # Filter by period if specified
            if norm_selected_periods and period_id and period_id not in norm_selected_periods:
                idx += len(self._findall(period, 'mpd:AdaptationSet'))
                continue
            
            for adapt_set in self._findall(period, 'mpd:AdaptationSet'):
                adapt_id = adapt_set.get('id', 'N/A')
                content_type, lang = self._get_content_info(adapt_set)
                
                # Skip non-media types
                if content_type in ('image', 'text'):
                    idx += 1
                    continue
                
                # Check if this set matches filters
                if not self._matches_filters(adapt_set, adapt_id, idx, content_type, lang,
                                           norm_selected_ids, norm_selected_kids, norm_selected_langs):
                    idx += 1
                    continue
                
                # Extract information
                info = self._extract_adaptation_set_info(adapt_set, adapt_id, content_type, lang, norm_selected_ids)
                adaptation_sets.append(info)
                idx += 1
        
        return adaptation_sets
    
    def _matches_filters(self, adapt_set, adapt_id, idx, content_type, lang, selected_ids, selected_kids, selected_langs):
        """Check if adaptation set matches filter criteria."""
        # Get representation IDs
        rep_ids = [rep.get('id') for rep in self._findall(adapt_set, 'mpd:Representation')]
        
        # Check ID filter
        if selected_ids:
            id_match = (adapt_id in selected_ids or 
                       str(idx) in selected_ids or 
                       any(rid in selected_ids for rid in rep_ids))
            if not id_match:
                return False
        
        # Check KID filter
        if selected_kids:
            adapt_kids = self._get_kids_from_adaptset(adapt_set)
            norm_adapt_kids = [k.lower().replace('-', '') for k in adapt_kids if k]
            kid_match = any(tk in norm_adapt_kids for tk in selected_kids)
            if not kid_match:
                return False
        
        # Check language filter for audio
        if selected_langs and content_type == 'audio':
            if lang.lower() not in selected_langs:
                return False
        
        return True
    
    def _get_kids_from_adaptset(self, adapt_set: ET.Element) -> List[str]:
        """Extract all KIDs from an AdaptationSet."""
        kids = []
        
        # Check adaptation set
        if kid := self._get_default_kid(adapt_set):
            kids.append(kid)
        
        # Check representations
        for rep in self._findall(adapt_set, 'mpd:Representation'):
            if kid := self._get_default_kid(rep):
                kids.append(kid)
        
        return kids
    
    def _extract_adaptation_set_info(self, adapt_set, adapt_id, content_type, lang, selected_ids=None):
        """Extract detailed information from adaptation set."""
        # Get DRM info
        default_kid = self._get_default_kid(adapt_set)
        drm_types = self._get_drm_types(adapt_set)
        
        # Get resolution for video
        height = None
        if content_type == 'video':
            height = self._get_video_height(adapt_set, selected_ids)
        
        return {
            'id': adapt_id,
            'content_type': content_type,
            'language': lang,
            'default_kid': default_kid,
            'drm_types': drm_types,
            'is_protected': self._is_protected(adapt_set),
            'height': height
        }
    
    def _get_video_height(self, adapt_set: ET.Element, selected_ids=None) -> Optional[int]:
        """Get height from video representations, prioritizing selected IDs."""
        max_height = 0
        selected_rep_heights = []
        
        for rep in self._findall(adapt_set, 'mpd:Representation'):
            rid = rep.get('id')
            h = rep.get('height')
            if not h:
                continue
                
            try:
                height_val = int(h)
                if selected_ids and rid in selected_ids:
                    selected_rep_heights.append(height_val)
                max_height = max(max_height, height_val)
            except ValueError:
                pass
        
        if selected_rep_heights:
            return max(selected_rep_heights)
        return max_height if max_height > 0 else None
    
    def print_adaptation_sets_info(self, selected_ids=None, selected_kids=None, selected_langs=None, selected_periods=None):
        """Print AdaptationSets information in simplified format."""
        sets = self.get_adaptation_sets_info(selected_ids, selected_kids, selected_langs, selected_periods)
        
        if not sets:
            return
        
        # Group by content type
        groups = {}
        for s in sets:
            groups.setdefault(s['content_type'], []).append(s)
        
        for c_type, items in groups.items():
            # Check if uniform (all same KID and no specific filter)
            has_filter = any([selected_ids, selected_kids, selected_langs])
            is_uni = len({i['default_kid'] for i in items}) == 1 and not has_filter
            
            seen_items = set()
            for item in ([items[0]] if is_uni else items):
                kid = item['default_kid'] or 'Not found'
                prot = ', '.join(item['drm_types']) if item['drm_types'] else 'No'
                
                if is_uni:
                    label = f"all {c_type}"
                else:
                    parts = [c_type]
                    if item.get('height'):
                        parts.append(f"{item['height']}p")
                    if item.get('language') and item['language'] != 'N/A':
                        parts.append(f"({item['language']})")
                    label = " ".join(parts)
                
                # Deduplicate display
                display_key = f"{label}_{kid}"
                if display_key in seen_items:
                    continue
                seen_items.add(display_key)
                
                console.print(f"    [red]- {label}[white], [cyan]Kid: [yellow]{kid}, [cyan]Protection: [yellow]{prot}")
    
    def _extract_pssh_data(self, drm_type: str, target_kids=None, target_periods=None, target_ids=None, target_langs=None):
        """Extract PSSH data for specific DRM type."""
        pssh_list = []
        observed = set()
        uuid = DRMSystem.get_uuid(drm_type)
        
        if not uuid:
            return pssh_list
        
        # Get adaptation sets matching filters
        adapt_sets_info = self.get_adaptation_sets_info(target_ids, target_kids, target_langs, target_periods)
        
        for info in adapt_sets_info:
            if info['default_kid']:
                # Extract PSSH from root with this KID
                pssh_items = self._find_pssh_by_kid(info['default_kid'], drm_type)
                for pssh_item in pssh_items:
                    if pssh_item['pssh'] not in observed:
                        observed.add(pssh_item['pssh'])
                        pssh_list.append(pssh_item)
        
        # If no filtered PSSH found, try global extraction
        if not pssh_list and not target_kids and not target_periods:
            pssh_list = self._extract_global_pssh(drm_type, observed)
        
        return pssh_list
    
    def _find_pssh_by_kid(self, kid, drm_type):
        """Find PSSH data by KID."""
        pssh_items = []
        uuid = DRMSystem.get_uuid(drm_type)
        
        for elem in self.root.iter():
            if 'ContentProtection' in elem.tag and uuid in (elem.get('schemeIdUri') or '').lower():
                elem_kid = self._get_default_kid(elem)
                if elem_kid and elem_kid.lower().replace('-', '') == kid.lower().replace('-', ''):
                    for child in elem:
                        if child.text and child.text.strip():
                            pssh_items.append({
                                'pssh': child.text.strip(),
                                'kid': kid,
                                'type': drm_type
                            })
        
        return pssh_items
    
    def _extract_global_pssh(self, drm_type, observed):
        """Extract global PSSH data (no filtering)."""
        pssh_list = []
        uuid = DRMSystem.get_uuid(drm_type)
        
        for elem in self.root.iter():
            if 'ContentProtection' in elem.tag and uuid in (elem.get('schemeIdUri') or '').lower():
                for child in elem:
                    txt = (child.text or "").strip()
                    if txt and txt not in observed:
                        observed.add(txt)
                        pssh_list.append({
                            'pssh': txt,
                            'kid': 'N/A',
                            'type': 'global'
                        })
        
        return pssh_list
    
    def get_drm_info(self, drm_preference="widevine", selected_ids=None, selected_kids=None, selected_langs=None, selected_periods=None):
        """Extract DRM information from MPD."""
        if not self.root:
            return {
                "available_drm_types": [],
                "selected_drm_type": None,
                "widevine_pssh": [],
                "playready_pssh": [],
                "fairplay_pssh": []
            }
        
        # Determine target KIDs for exact filtering
        target_kids = []
        if selected_kids:
            target_kids.extend([k.lower().replace("-", "") for k in selected_kids])
        
        # Also include KIDs from matched AdaptationSets
        matched_sets = self.get_adaptation_sets_info(selected_ids, selected_kids, selected_langs, selected_periods)
        for s in matched_sets:
            if s["default_kid"]:
                k = s["default_kid"].lower().replace("-", "")
                if k not in target_kids:
                    target_kids.append(k)
        
        # If filters were provided but no KIDs found, filter for NOTHING
        if not target_kids and (selected_ids or selected_kids or selected_langs or selected_periods):
            target_kids = []
        elif not target_kids:
            target_kids = None
        
        # Extract PSSH data for each DRM type
        pssh_data = {}
        for drm_type in [DRMSystem.WIDEVINE, DRMSystem.PLAYREADY, DRMSystem.FAIRPLAY]:
            pssh_data[drm_type] = self._extract_pssh_data(
                drm_type, target_kids, selected_periods, selected_ids, selected_langs
            )
        
        # Determine available DRM types
        available = [t for t, v in pssh_data.items() if v]
        
        # Select DRM type based on preference
        selected = drm_preference if drm_preference in available else (available[0] if available else None)
        
        # Print adaptation sets info
        self.print_adaptation_sets_info(selected_ids, selected_kids, selected_langs, selected_periods)
        print("")
        
        return {
            'available_drm_types': available,
            'selected_drm_type': selected,
            'widevine_pssh': pssh_data.get(DRMSystem.WIDEVINE, []),
            'playready_pssh': pssh_data.get(DRMSystem.PLAYREADY, []),
            'fairplay_pssh': pssh_data.get(DRMSystem.FAIRPLAY, [])
        }