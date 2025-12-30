# 29.12.25

from typing import Optional, Dict, List
from urllib.parse import urljoin, urlparse
from pathlib import Path


# External Libraries
from isodate import parse_duration
from lxml import etree
from rich.console import Console
from rich.table import Table


# Logic
from .constants import DRMSystem


# Variables
console = Console()


class DurationUtils:
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


class FileTypeDetector:
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


class NamespaceManager:
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
            nsmap['mspr'] = 'urn:microsoft:playready'

            # Add other namespaces if present
            for prefix, uri in root.nsmap.items():
                if prefix is not None:
                    nsmap[prefix] = uri

        else:
            # Fallback to default DASH namespace
            nsmap['mpd'] = 'urn:mpeg:dash:schema:mpd:2011'
            nsmap['cenc'] = 'urn:mpeg:cenc:2013'
            nsmap['mspr'] = 'urn:microsoft:playready'
        return nsmap
    
    def find(self, element: etree._Element, path: str) -> Optional[etree._Element]:
        """Find element using namespace-aware XPath"""
        return element.find(path, namespaces=self.nsmap)
    
    def findall(self, element: etree._Element, path: str) -> List[etree._Element]:
        """Find all elements using namespace-aware XPath"""
        return element.findall(path, namespaces=self.nsmap)


class BaseURLResolver:
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


class MetadataExtractor:
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


class TablePrinter:
    def __init__(self, mpd_duration: int, mpd_sub_list: list = None):
        self.mpd_duration = mpd_duration
        self.mpd_sub_list = mpd_sub_list or []
    
    def print_table(self, representations: List[Dict], selected_video: Optional[Dict] = None, selected_audio: Optional[Dict] = None, selected_subs: list = None, available_drm_types: list = None):
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
    
    def _get_drm_display(self, rep: Dict) -> str:
        """Generate DRM display string for table (only shows CENC)"""
        content_type = "Vid" if rep['type'] == 'video' else "Aud"
        
        if not rep.get('protected'):
            return content_type
        
        return f"{content_type} *CENC"
    
    def _get_drm_systems_display(self, rep: Dict) -> str:
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
        
        drm_abbrevs = [DRMSystem.get_abbrev(drm) for drm in drm_types]
        return '+'.join(drm_abbrevs)