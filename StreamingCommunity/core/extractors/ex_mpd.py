# 10.01.26

import xml.etree.ElementTree as ET
import base64
import binascii
from typing import Optional, List, Dict


# External libraries
from curl_cffi_smart import requests
from rich.console import Console


# Variable
console = Console()


class DRMSystem:
    """DRM system constants and utilities"""
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


class NamespaceManager:
    def __init__(self, root: ET.Element):
        self.nsmap = self._extract_namespaces(root)
        for prefix, uri in self.nsmap.items():
            if prefix and prefix != 'mpd':
                ET.register_namespace(prefix, uri)
    
    @staticmethod
    def _extract_namespaces(root: ET.Element) -> Dict[str, str]:
        nsmap = {
            'mpd': 'urn:mpeg:dash:schema:mpd:2011',
            'cenc': 'urn:mpeg:cenc:2013',
            'mspr': 'urn:microsoft:playready'
        }
        
        for elem in root.iter():
            tag = elem.tag
            if '}' in tag:
                ns = tag.split('}')[0].strip('{')
                if ns and ns not in nsmap.values():
                    # Prova a identificare il namespace
                    if 'dash' in ns.lower() or 'mpd' in ns.lower():
                        nsmap['mpd'] = ns
                    elif 'cenc' in ns.lower():
                        nsmap['cenc'] = ns
                    elif 'playready' in ns.lower():
                        nsmap['mspr'] = ns
        
        return nsmap
    
    def find(self, element: ET.Element, path: str) -> Optional[ET.Element]:
        xpath = self._convert_path(path)
        return element.find(xpath, namespaces=self.nsmap)
    
    def findall(self, element: ET.Element, path: str) -> List[ET.Element]:
        xpath = self._convert_path(path)
        return element.findall(xpath, namespaces=self.nsmap)
    
    def _convert_path(self, path: str) -> str:
        for prefix, uri in self.nsmap.items():
            path = path.replace(f'{prefix}:', f'{{{uri}}}')
        return path


class ContentProtectionHandler:
    """Handles DRM and content protection"""
    def __init__(self, ns_manager: NamespaceManager):
        self.ns = ns_manager
    
    def is_protected(self, element: ET.Element) -> bool:
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            sid = (cp.get('schemeIdUri') or '').lower()
            if DRMSystem.CENC_SCHEME in sid or DRMSystem.from_uuid(sid):
                return True
        return False
    
    def get_default_kid(self, element: ET.Element) -> Optional[str]:
        """Extract default_KID from ContentProtection elements"""
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            if DRMSystem.CENC_SCHEME in (cp.get('schemeIdUri') or '').lower():
                return cp.get(f'{{{self.ns.nsmap["cenc"]}}}default_KID') or cp.get('default_KID')
        
        return None
    
    def get_drm_types(self, element: ET.Element) -> List[str]:
        drm_types = []
        
        for cp in self.ns.findall(element, 'mpd:ContentProtection'):
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            drm_type = DRMSystem.from_uuid(scheme_id)
            
            if drm_type and drm_type not in drm_types:
                if self._has_pssh_data(cp, drm_type):
                    drm_types.append(drm_type)
        
        return drm_types
    
    def _has_pssh_data(self, cp_element: ET.Element, drm_type: str) -> bool:
        pssh = self.ns.find(cp_element, 'cenc:pssh')
        if pssh is not None and pssh.text and pssh.text.strip():
            if self._is_valid_pssh(pssh.text.strip(), drm_type):
                return True
        
        if drm_type == DRMSystem.PLAYREADY:
            pro = self.ns.find(cp_element, 'mspr:pro')
            if pro is not None and pro.text and pro.text.strip():
                if self._is_valid_pro(pro.text.strip()):
                    return True
        
        return False
    
    def _is_valid_pssh(self, pssh_b64: str, drm_type: str) -> bool:
        """Verify if the PSSH is valid for the given DRM type"""
        try:
            data = base64.b64decode(pssh_b64)
            if len(data) < 32:
                return False
            if data[4:8] != b'pssh': 
                return False
            
            target_uuid = DRMSystem.get_uuid(drm_type)
            if not target_uuid: 
                return False
            
            target_bytes = binascii.unhexlify(target_uuid.replace('-', ''))
            return data[12:28] == target_bytes
        except Exception:
            return False

    def _is_valid_pro(self, pro_b64: str) -> bool:
        """Verify if the PlayReady Object is valid"""
        try:
            data = base64.b64decode(pro_b64)
            if len(data) < 10: 
                return False
            
            length = int.from_bytes(data[:4], byteorder='little')
            return len(data) == length
        except Exception:
            return False

    def extract_pssh(self, root: ET.Element, drm_type: str = DRMSystem.WIDEVINE) -> List[str]:
        target_uuid = DRMSystem.get_uuid(drm_type)
        if not target_uuid:
            return []
        
        pssh_list = []
        for elem in root.iter():
            if 'ContentProtection' in elem.tag:
                scheme_id = (elem.get('schemeIdUri') or '').lower()
                if target_uuid in scheme_id:
                    for child in elem:
                        text = (child.text or "").strip()
                        if not text:
                            continue

                        if 'pssh' in child.tag:
                            if self._is_valid_pssh(text, drm_type):
                                if text not in pssh_list:
                                    pssh_list.append(text)
                        elif drm_type == DRMSystem.PLAYREADY and 'pro' in child.tag:
                            if self._is_valid_pro(text):
                                if text not in pssh_list:
                                    pssh_list.append(text)
        
        return pssh_list

    def extract_pssh_full(self, root: ET.Element, drm_type: str = DRMSystem.WIDEVINE) -> List[Dict[str, str]]:
        target_uuid = DRMSystem.get_uuid(drm_type)
        if not target_uuid:
            return []
        
        pssh_list = []
        observed = set()

        # Check AdaptationSets
        for period in self.ns.findall(root, 'mpd:Period'):
            for adapt_set in self.ns.findall(period, 'mpd:AdaptationSet'):
                content_type = adapt_set.get('contentType') or adapt_set.get('mimeType', 'unknown')
                if 'video' in content_type.lower(): 
                    content_type = 'video'
                elif 'audio' in content_type.lower():
                    content_type = 'audio'
                
                default_kid = self.get_default_kid(adapt_set)
                
                # Check directly in AdaptationSet
                for cp in self.ns.findall(adapt_set, 'mpd:ContentProtection'):
                    scheme_id = (cp.get('schemeIdUri') or '').lower()
                    if target_uuid in scheme_id:
                        for child in cp:
                            text = (child.text or "").strip()
                            if not text: 
                                continue

                            is_valid = False
                            if 'pssh' in child.tag:
                                is_valid = self._is_valid_pssh(text, drm_type)
                            elif drm_type == DRMSystem.PLAYREADY and 'pro' in child.tag:
                                is_valid = self._is_valid_pro(text)

                            if is_valid:
                                if text not in observed:
                                    observed.add(text)
                                    pssh_list.append({'pssh': text, 'kid': default_kid or 'N/A', 'type': content_type})
                
                # Check in Representations
                for rep in self.ns.findall(adapt_set, 'mpd:Representation'):
                    for cp in self.ns.findall(rep, 'mpd:ContentProtection'):
                         scheme_id = (cp.get('schemeIdUri') or '').lower()
                         if target_uuid in scheme_id:
                             for child in cp:
                                text = (child.text or "").strip()
                                if not text: 
                                    continue

                                is_valid = False
                                if 'pssh' in child.tag:
                                    is_valid = self._is_valid_pssh(text, drm_type)
                                elif drm_type == DRMSystem.PLAYREADY and 'pro' in child.tag:
                                    is_valid = self._is_valid_pro(text)

                                if is_valid:
                                    if text not in observed:
                                        observed.add(text)
                                        pssh_list.append({'pssh': text, 'kid': default_kid or 'N/A', 'type': content_type})

        # Fallback for generic PSSHs not in AdaptationSets
        if not pssh_list:
            for elem in root.iter():
                if 'ContentProtection' in elem.tag:
                    scheme_id = (elem.get('schemeIdUri') or '').lower()
                    if target_uuid in scheme_id:
                        for child in elem:
                            text = (child.text or "").strip()
                            if not text: 
                                continue

                            is_valid = False
                            if 'pssh' in child.tag:
                                is_valid = self._is_valid_pssh(text, drm_type)
                            elif drm_type == DRMSystem.PLAYREADY and 'pro' in child.tag:
                                is_valid = self._is_valid_pro(text)

                            if is_valid:
                                if text not in observed:
                                    observed.add(text)
                                    pssh_list.append({'pssh': text, 'kid': 'N/A', 'type': 'global'})
        
        return pssh_list


class MPDParser:
    def __init__(self, mpd_url: str, headers: Dict[str, str] = None, timeout: int = 30):
        self.mpd_url, self.headers, self.timeout = mpd_url, headers or {}, timeout
        self.root = self.ns_manager = self.protection_handler = None
    
    def _set_root(self, root: ET.Element):
        self.root = root
        self.ns_manager = NamespaceManager(self.root)
        self.protection_handler = ContentProtectionHandler(self.ns_manager)

    def parse(self) -> bool:
        """Parse MPD and setup handlers"""
        try:
            r = requests.get(self.mpd_url, headers=self.headers, timeout=self.timeout, impersonate="chrome99")
            r.raise_for_status()
            self._set_root(ET.fromstring(r.content))
            return True
        except Exception as e:
            console.print(f"[red]Error parsing MPD: {e}")
            return False
    
    def parse_from_file(self, file_path: str) -> bool:
        """Parse MPD from a local file"""
        try:
            self._set_root(ET.parse(file_path).getroot())
            return True
        except Exception as e:
            console.print(f"[red]Error parsing MPD: {e}")
            return False
    
    def get_adaptation_sets_info(self) -> List[Dict[str, any]]:
        """Get information about all AdaptationSets including KID"""
        if self.root is None or self.ns_manager is None:
            return []
        
        adaptation_sets = []
        
        for period in self.ns_manager.findall(self.root, 'mpd:Period'):
            for adapt_set in self.ns_manager.findall(period, 'mpd:AdaptationSet'):
                adapt_id = adapt_set.get('id', 'N/A')
                content_type = adapt_set.get('contentType', 'N/A')
                lang = adapt_set.get('lang', 'N/A')
                
                # Get default_KID
                default_kid = self.protection_handler.get_default_kid(adapt_set)
                
                # Get DRM types
                drm_types = self.protection_handler.get_drm_types(adapt_set)
                
                adaptation_sets.append({
                    'id': adapt_id,
                    'content_type': content_type,
                    'language': lang,
                    'default_kid': default_kid,
                    'drm_types': drm_types,
                    'is_protected': self.protection_handler.is_protected(adapt_set)
                })
        
        return adaptation_sets
    
    def print_adaptation_sets_info(self):
        """Print AdaptationSets information in a simplified format"""
        sets = [s for s in self.get_adaptation_sets_info() if s['content_type'] not in ('image', 'text')]
        if not sets: 
            return

        groups = {}
        for s in sets:
            groups.setdefault(s['content_type'], []).append(s)

        for c_type, items in groups.items():
            is_uni = len({i['default_kid'] for i in items}) == 1
            for i in ([items[0]] if is_uni else items):
                kid = i['default_kid'] or 'Not found'
                prot = (', '.join(i['drm_types']) or 'Unknown') if i['is_protected'] else 'No'
                label = f"all {c_type}" if is_uni else f"{c_type} {i['language'] if i['language'] != 'N/A' else ''}".strip()
                
                console.print(f"    [red]- {label}[white], [cyan]Kid: [yellow]{kid}, [cyan]Protection: [yellow]{prot}")

    def get_drm_info(self, drm_preference: str = 'widevine') -> Dict[str, any]:
        """Extract DRM information from MPD"""
        if not self.root: 
            return {
                'available_drm_types': [], 
                'selected_drm_type': None, 
                'widevine_pssh': [],
                'playready_pssh': [],
                'fairplay_pssh': []
            }
        
        pssh_data = {t: self.protection_handler.extract_pssh_full(self.root, t) 
                     for t in [DRMSystem.WIDEVINE, DRMSystem.PLAYREADY, DRMSystem.FAIRPLAY]}
        
        avail = [t for t, v in pssh_data.items() if v]
        sel_type = drm_preference if drm_preference in avail else (avail[0] if avail else None)
        
        self.print_adaptation_sets_info()
        print("")
        return {
            'available_drm_types': avail,
            'selected_drm_type': sel_type,
            'widevine_pssh': pssh_data.get(DRMSystem.WIDEVINE, []),
            'playready_pssh': pssh_data.get(DRMSystem.PLAYREADY, []),
            'fairplay_pssh': pssh_data.get(DRMSystem.FAIRPLAY, []),
        }