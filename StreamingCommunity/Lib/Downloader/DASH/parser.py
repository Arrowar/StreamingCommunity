# 25.07.25

from urllib.parse import urljoin
import xml.etree.ElementTree as ET


# External library
import httpx
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager


# Variable
console = Console()
max_timeout = config_manager.get_int('REQUESTS', 'timeout')


class MPDParser:
    @staticmethod
    def get_best(representations):
        """
        Returns the video representation with the highest resolution/bandwidth, or audio with highest bandwidth.
        """
        videos = [r for r in representations if r['type'] == 'video']
        audios = [r for r in representations if r['type'] == 'audio']
        if videos:
            return max(videos, key=lambda r: (r['height'], r['width'], r['bandwidth']))
        elif audios:
            return max(audios, key=lambda r: r['bandwidth'])
        return None

    @staticmethod
    def get_worst(representations):
        """
        Returns the video representation with the lowest resolution/bandwidth, or audio with lowest bandwidth.
        """
        videos = [r for r in representations if r['type'] == 'video']
        audios = [r for r in representations if r['type'] == 'audio']
        if videos:
            return min(videos, key=lambda r: (r['height'], r['width'], r['bandwidth']))
        elif audios:
            return min(audios, key=lambda r: r['bandwidth'])
        return None

    @staticmethod
    def get_list(representations, type_filter=None):
        """
        Returns the list of representations filtered by type ('video', 'audio', etc.).
        """
        if type_filter:
            return [r for r in representations if r['type'] == type_filter]
        return representations

    def __init__(self, mpd_url):
        self.mpd_url = mpd_url
        self.pssh = None
        self.representations = []
        self.base_url = mpd_url.rsplit('/', 1)[0] + '/'

    def parse(self, custom_headers):
        response = httpx.get(self.mpd_url, headers=custom_headers, timeout=max_timeout, follow_redirects=True)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Properly handle default namespace
        ns = {'': 'urn:mpeg:dash:schema:mpd:2011'}
        ns['mpd'] = ns['']
        ns['cenc'] = 'urn:mpeg:cenc:2013'

        # Extract PSSH dynamically: take the first <cenc:pssh> found
        for protection in root.findall('.//mpd:ContentProtection', ns):
            pssh_element = protection.find('cenc:pssh', ns)
            if pssh_element is not None and pssh_element.text:
                self.pssh = pssh_element.text
                break

        if not self.pssh:
            console.print("[bold red]PSSH not found in MPD![/bold red]")

        # Extract MPD-level BaseURL if available
        mpd_base_url_elem = root.find('mpd:BaseURL', ns)
        if mpd_base_url_elem is not None and mpd_base_url_elem.text:
            self.base_url = urljoin(self.base_url, mpd_base_url_elem.text)

        # Extract representations
        for adapt_set in root.findall('.//mpd:AdaptationSet', ns):
            mime_type = adapt_set.get('mimeType', '')
            lang = adapt_set.get('lang', '')
            content_type = mime_type.split('/')[0] if mime_type else 'unknown'

            # Find SegmentTemplate at AdaptationSet level (DASH spec allows this)
            seg_template = adapt_set.find('mpd:SegmentTemplate', ns)

            # Check for BaseURL at AdaptationSet level
            adapt_base_url_elem = adapt_set.find('mpd:BaseURL', ns)
            adapt_base_url = adapt_base_url_elem.text if adapt_base_url_elem is not None else self.base_url

            for rep in adapt_set.findall('mpd:Representation', ns):
                rep_id = rep.get('id')
                bandwidth = rep.get('bandwidth')
                codecs = rep.get('codecs')
                width = rep.get('width')
                height = rep.get('height')

                # Get representation BaseURL if available, or fallback to adaptation set BaseURL
                rep_base_url_elem = rep.find('mpd:BaseURL', ns)
                base_url = rep_base_url_elem.text if rep_base_url_elem is not None else adapt_base_url
                
                # Make sure base_url is absolute
                if not base_url.startswith('http'):
                    base_url = urljoin(self.base_url, base_url)

                # Try to handle both SegmentTemplate and SegmentBase formats
                init_url = None
                segment_urls = []
                
                # Check for SegmentTemplate (original implementation)
                rep_seg_template = rep.find('mpd:SegmentTemplate', ns)
                seg_tmpl = rep_seg_template if rep_seg_template is not None else seg_template
                
                if seg_tmpl is not None:
                    init = seg_tmpl.get('initialization')
                    media = seg_tmpl.get('media')
                    start_number = int(seg_tmpl.get('startNumber', 1))

                    # Replace $RepresentationID$ in init/media if present
                    if init and '$RepresentationID$' in init:
                        init = init.replace('$RepresentationID$', rep_id)
                    if media and '$RepresentationID$' in media:
                        media = media.replace('$RepresentationID$', rep_id)

                    init_url = urljoin(base_url, init) if init else None

                    # Calculate segments from timeline
                    segments = []
                    seg_timeline = seg_tmpl.find('mpd:SegmentTimeline', ns)
                    if seg_timeline is not None:
                        segment_number = start_number
                        for s in seg_timeline.findall('mpd:S', ns):
                            repeat = int(s.get('r', 0))
                            
                            # Always append at least one segment
                            segments.append(segment_number)
                            segment_number += 1
                            for _ in range(repeat):
                                segments.append(segment_number)
                                segment_number += 1

                    if not segments:
                        segments = list(range(start_number, start_number + 100))

                    # Replace $Number$ and $RepresentationID$ in media URL
                    for n in segments:
                        url = media
                        if '$Number$' in url:
                            url = url.replace('$Number$', str(n))
                        if '$RepresentationID$' in url:
                            url = url.replace('$RepresentationID$', rep_id)
                        segment_urls.append(urljoin(base_url, url))
                
                # Check for SegmentBase (new implementation)
                seg_base = rep.find('mpd:SegmentBase', ns)
                if seg_base is not None:

                    # For SegmentBase, we have a single media file with initialization and index ranges
                    init_elem = seg_base.find('mpd:Initialization', ns)
                    if init_elem is not None:
                        init_range = init_elem.get('range', '0-0')

                        # We'll use the BaseURL + range info for initialization
                        init_url = f"{base_url}#range={init_range}"
                    
                    # For SegmentBase, there's typically just one URL (the BaseURL) for the entire content
                    # We use this as our segment URL
                    segment_urls = [base_url]
                
                # Only add representation if we found either init_url or segment_urls
                if init_url or segment_urls:
                    self.representations.append({
                        'id': rep_id,
                        'type': content_type,
                        'codec': codecs,
                        'bandwidth': int(bandwidth) if bandwidth else 0,
                        'width': int(width) if width else 0,
                        'height': int(height) if height else 0,
                        'language': lang,
                        'init_url': init_url,
                        'segment_urls': segment_urls,
                        'base_url': base_url,
                        'is_segment_base': seg_base is not None
                    })

    def get_resolutions(self):
        """Return list of video representations with their resolutions."""
        return [
            rep for rep in self.representations
            if rep['type'] == 'video'
        ]

    def get_audios(self):
        """Return list of audio representations."""
        return [
            rep for rep in self.representations
            if rep['type'] == 'audio'
        ]

    def get_best_video(self):
        """Return the best video representation (highest resolution, then bandwidth)."""
        videos = self.get_resolutions()
        if not videos:
            return None
        
        # Sort by (height, width, bandwidth)
        return max(videos, key=lambda r: (r['height'], r['width'], r['bandwidth']))

    def get_best_audio(self):
        """Return the best audio representation (highest bandwidth)."""
        audios = self.get_audios()
        if not audios:
            return None
        return max(audios, key=lambda r: r['bandwidth'])

    def select_video(self, force_resolution="Best"):
        """
        Select a video representation based on the requested resolution.
        Returns: (selected_video, list_available_resolution, filter_custom_resolution, downloadable_video)
        """
        video_reps = self.get_resolutions()
        list_available_resolution = [
            f"{rep['width']}x{rep['height']}" for rep in video_reps
        ]
        force_resolution_l = (force_resolution or "Best").lower()

        if force_resolution_l == "best":
            selected_video = self.get_best_video()
            filter_custom_resolution = "Best"

        elif force_resolution_l == "worst":
            selected_video = MPDParser.get_worst(video_reps)
            filter_custom_resolution = "Worst"

        else:
            selected_video = self.get_best_video()
            filter_custom_resolution = "Best"

        downloadable_video = f"{selected_video['width']}x{selected_video['height']}" if selected_video else "N/A"
        return selected_video, list_available_resolution, filter_custom_resolution, downloadable_video

    def select_audio(self, preferred_audio_langs=None):
        """
        Select an audio representation based on preferred languages.
        Returns: (selected_audio, list_available_audio_langs, filter_custom_audio, downloadable_audio)
        """
        audio_reps = self.get_audios()
        list_available_audio_langs = [
            rep['language'] or "None" for rep in audio_reps
        ]

        selected_audio = None
        filter_custom_audio = "First"

        if preferred_audio_langs:
            
            # Search for the first available language in order of preference
            for lang in preferred_audio_langs:
                for rep in audio_reps:
                    if (rep['language'] or "None").lower() == lang.lower():
                        selected_audio = rep
                        filter_custom_audio = lang
                        break
                if selected_audio:
                    break
            if not selected_audio:
                selected_audio = self.get_best_audio()
        else:
            selected_audio = self.get_best_audio()

        downloadable_audio = selected_audio['language'] or "None" if selected_audio else "N/A"
        return selected_audio, list_available_audio_langs, filter_custom_audio, downloadable_audio