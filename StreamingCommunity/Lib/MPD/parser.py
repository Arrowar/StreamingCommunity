# 29.12.25

import json
import logging
from urllib.parse import urljoin
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime


# External Libraries
from lxml import etree
from curl_cffi import requests
from rich.console import Console


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager


# Logic
from .constants import DRMSystem
from .utils import (DurationUtils, NamespaceManager, BaseURLResolver, FileTypeDetector, TablePrinter)
from .handlers import (ContentProtectionHandler, RepresentationParser, RepresentationFilter, SegmentTimelineParser)


# Variables
console = Console()
max_timeout = config_manager.config.get_int('REQUESTS', 'timeout')
FILTER_CUSTOM_RESOLUTION = str(config_manager.config.get('M3U8_CONVERSION', 'force_resolution')).strip().lower()
DOWNLOAD_SPECIFIC_AUDIO = config_manager.config.get_list('M3U8_DOWNLOAD', 'specific_list_audio')


class MPD_Parser:
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
        self.encryption_method = None
        
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
        
        # Extract PSSH for all DRM types
        self.pssh_widevine = self.protection_handler.extract_pssh(self.root, DRMSystem.WIDEVINE)
        self.pssh_playready = self.protection_handler.extract_pssh(self.root, DRMSystem.PLAYREADY)
        self.pssh_fairplay = self.protection_handler.extract_pssh(self.root, DRMSystem.FAIRPLAY)
        self.encryption_method = self.protection_handler.get_encryption_method(self.root)
        
        # Get all available DRM types
        self.available_drm_types = []
        if self.pssh_widevine:
            self.available_drm_types.append(DRMSystem.WIDEVINE)
        if self.pssh_playready:
            self.available_drm_types.append(DRMSystem.PLAYREADY)
        if self.pssh_fairplay:
            self.available_drm_types.append(DRMSystem.FAIRPLAY)
        
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
            period_base_url = self.url_resolver.resolve_base_url(period, base_url)
            
            # Get period duration and protection info
            period_duration_str = period.get('duration')
            period_duration = DurationUtils.parse_duration(period_duration_str) or self.mpd_duration
            period_protected = self.protection_handler.is_protected(period)
            period_drm_types = self.protection_handler.get_drm_types(period)
            period_drm_type = self.protection_handler.get_primary_drm_type(period)
            period_encryption_method = self.protection_handler.get_encryption_method(period)
            
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
                    if not rep.get('encryption_method') and period_encryption_method:
                        rep['encryption_method'] = period_encryption_method
                
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
        from .utils import URLBuilder
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