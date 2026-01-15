# 10.01.26

import xml.etree.ElementTree as ET
from typing import Optional, List, Dict


# External libraries
from curl_cffi import requests
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
        uuid_lower = uuid.lower()
        for drm_type, drm_uuid in cls.UUIDS.items():
            if drm_uuid in uuid_lower:
                return drm_type
        return None


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
            scheme_id = (cp.get('schemeIdUri') or '').lower()
            value = (cp.get('value') or '').lower()
            
            if DRMSystem.CENC_SCHEME in scheme_id and ('cenc' in value or value):
                return True
            
            if DRMSystem.from_uuid(scheme_id):
                return True
        
        return False
    
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
            return True
        
        if drm_type == DRMSystem.PLAYREADY:
            pro = self.ns.find(cp_element, 'mspr:pro')
            if pro is not None and pro.text and pro.text.strip():
                return True
        return False
    
    def extract_pssh(self, root: ET.Element, drm_type: str = DRMSystem.WIDEVINE) -> Optional[str]:
        target_uuid = DRMSystem.get_uuid(drm_type)
        if not target_uuid:
            return None
        
        for elem in root.iter():
            if 'ContentProtection' in elem.tag:
                scheme_id = (elem.get('schemeIdUri') or '').lower()
                if target_uuid in scheme_id:
                    for child in elem:
                        if 'pssh' in child.tag:
                            if child.text and child.text.strip():
                                return child.text.strip()
                        
                        if drm_type == DRMSystem.PLAYREADY and 'pro' in child.tag:
                            if child.text and child.text.strip():
                                return child.text.strip()
        
        return None


class MPDParser:
    def __init__(self, mpd_url: str, headers: Dict[str, str] = None, timeout: int = 30):
        self.mpd_url = mpd_url
        self.headers = headers or {}
        self.timeout = timeout
        self.root = None
        self.ns_manager = None
        self.protection_handler = None
    
    def parse(self) -> bool:
        """Parse MPD and setup handlers"""
        try:
            response = requests.get(
                self.mpd_url, 
                headers=self.headers,
                timeout=self.timeout,
                impersonate="chrome124"
            )
            response.raise_for_status()
            
            self.root = ET.fromstring(response.content)
            self.ns_manager = NamespaceManager(self.root)
            self.protection_handler = ContentProtectionHandler(self.ns_manager)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error parsing MPD: {e}")
            return False
    
    def parse_from_file(self, file_path: str) -> bool:
        """Parse MPD from a local file (e.g., raw.mpd from m3u8dl)"""
        try:
            tree = ET.parse(file_path)
            self.root = tree.getroot()
            self.ns_manager = NamespaceManager(self.root)
            self.protection_handler = ContentProtectionHandler(self.ns_manager)
            return True
            
        except Exception as e:
            console.print(f"[red]Error parsing MPD: {e}")
            return False
    
    def get_drm_info(self, drm_preference: str = 'widevine') -> Dict[str, any]:
        """Extract DRM information from MPD"""
        if self.root is None or self.protection_handler is None:
            return {
                'available_drm_types': [],
                'selected_drm_type': None,
                'pssh': None
            }
        
        # Get PSSH for all DRM types
        pssh_data = {}
        for drm_type in [DRMSystem.WIDEVINE, DRMSystem.PLAYREADY, DRMSystem.FAIRPLAY]:
            pssh = self.protection_handler.extract_pssh(self.root, drm_type)
            if pssh:
                pssh_data[drm_type] = pssh
        
        available_drm_types = list(pssh_data.keys())
        
        # Select DRM type based on preference
        selected_drm_type = None
        selected_pssh = None
        
        if drm_preference == 'auto':
            selected_drm_type = available_drm_types[0] if available_drm_types else None
        elif drm_preference in available_drm_types:
            selected_drm_type = drm_preference
        else:
            selected_drm_type = available_drm_types[0] if available_drm_types else None
        
        if selected_drm_type:
            selected_pssh = pssh_data.get(selected_drm_type)
        
        if available_drm_types:
            console.print(f"\n[cyan]Detected DRM types [[red]{', '.join(available_drm_types)}[white]]")
        
        return {
            'available_drm_types': available_drm_types,
            'selected_drm_type': selected_drm_type,
            'pssh': selected_pssh,
            'all_pssh': pssh_data
        }