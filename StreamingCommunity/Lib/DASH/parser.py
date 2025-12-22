# 25.07.25

import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

# External library
from curl_cffi import requests
from rich.console import Console


# Variable
console = Console()

_ISO8601_RE = re.compile(
    r"^P" r"(?:(?P<days>\d+)D)?" r"(?:T" r"(?:(?P<hours>\d+)H)?" r"(?:(?P<minutes>\d+)M)?" r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?" r")?$"
)


@dataclass
class _Part:
    base_url: str
    rep_id: str
    bandwidth: Optional[int]
    init_tmpl: str
    media_tmpl: str
    start_number: int
    segments: int
    seg_timeline_el: Optional[ET.Element]


@dataclass
class _Stream:
    kind: str
    encrypted: bool
    width: Optional[int]
    height: Optional[int]
    bandwidth: Optional[int]
    rep_id: str
    fps: Optional[float]
    codecs: str
    lang: str
    channels: Optional[int]
    role: str
    segments: int = 0
    seconds: float = 0.0
    pssh_set: Set[str] = field(default_factory=set)
    parts: List[_Part] = field(default_factory=list)



def parse_iso8601_duration_seconds(value: Optional[str]) -> float:
    if not value:
        return 0.0
    m = _ISO8601_RE.match(value.strip())
    if not m:
        return 0.0
    days = int(m.group('days') or 0)
    hours = int(m.group('hours') or 0)
    minutes = int(m.group('minutes') or 0)
    seconds = float(m.group('seconds') or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours:02d}h{minutes:02d}m{secs:02d}s"
    return f"{minutes:02d}m{secs:02d}s"


def _parse_frame_rate(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    v = value.strip()
    if '/' in v:
        a, b = v.split('/', 1)
        try:
            num = float(a)
            den = float(b)
            return None if den == 0 else num / den
        except ValueError:
            return None
    try:
        return float(v)
    except ValueError:
        return None


def _format_fps(value: Optional[float]) -> str:
    if value is None:
        return ''
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip('0').rstrip('.')


def _replace_number(template: str, number: int) -> str:
    def _match(m: re.Match[str]) -> str:
        fmt = m.group(1)
        if fmt:
            mm = re.match(r'%0(\d+)d', fmt)
            if mm:
                return str(number).zfill(int(mm.group(1)))
        return str(number)

    return re.sub(r'\$Number(\%0\d+d)?\$', _match, template)


def build_url(base: str, template: str, *, rep_id: Optional[str], bandwidth: Optional[int], number: Optional[int] = None, time: Optional[int] = None) -> Optional[str]:
    if not template:
        return None
    
    out = template
    if rep_id is not None:
        out = out.replace('$RepresentationID$', rep_id)
    if bandwidth is not None:
        out = out.replace('$Bandwidth$', str(bandwidth))
    if '$Number' in out and number is not None:
        out = _replace_number(out, number)
    if '$Time$' in out and time is not None:
        out = out.replace('$Time$', str(time))

    split = out.split('#', 1)
    path_and_query = split[0]
    frag = ('#' + split[1]) if len(split) == 2 else ''
    if '?' in path_and_query:
        path_part, query_part = path_and_query.split('?', 1)
        abs_path = urljoin(base, path_part)
        return abs_path + '?' + query_part + frag
    return urljoin(base, path_and_query) + frag


def _timeline_count_and_units(seg_timeline_el: Optional[ET.Element], ns: Dict[str, str]) -> Tuple[int, int]:
    if seg_timeline_el is None:
        return (0, 0)
    
    count = 0
    units = 0
    for s_el in seg_timeline_el.findall('mpd:S', ns):
        d = s_el.get('d')
        if d is None:
            continue

        d_i = int(d)
        r = int(s_el.get('r', 0) or 0)
        if r < 0:
            r = 0
        n = r + 1
        count += n
        units += d_i * n

    return (count, units)


def _timeline_iter_times(seg_timeline_el: Optional[ET.Element], ns: Dict[str, str]) -> Iterable[int]:
    if seg_timeline_el is None:
        return
    
    current_time = 0
    for s_el in seg_timeline_el.findall('mpd:S', ns):
        d = s_el.get('d')
        if d is None:
            continue

        d_i = int(d)
        if s_el.get('t') is not None:
            current_time = int(s_el.get('t') or 0)

        r = int(s_el.get('r', 0) or 0)
        if r < 0:
            r = 0
        for _ in range(r + 1):
            yield current_time
            current_time += d_i


class MPD_Parser:
    def __init__(self, mpd_url: str):
        self.mpd_url = mpd_url
        self.root: Optional[ET.Element] = None
        self.ns: Dict[str, str] = {}

        self.min_duration_seconds: float = 120.0
        self.streams: List[_Stream] = []

        self._selected_best_video: Optional[_Stream] = None
        self.merge_same_id: bool = False

    def parse(self, custom_headers: Optional[Dict[str, str]] = None, *, min_duration_seconds: float = 120.0, merge_same_id: bool = False) -> None:
        self.min_duration_seconds = float(min_duration_seconds)
        self.merge_same_id = bool(merge_same_id)
        self._load_mpd(custom_headers or {})
        self._extract_namespaces()
        self.streams = self._parse_streams()

    def bestVideo(self) -> Dict[str, Any]:
        s = self._pick_best(kind='video')
        if s is None:
            raise RuntimeError('No video streams found')
        self._selected_best_video = s
        return self._stream_payload(s)

    def bestAudio(self) -> Dict[str, Any]:
        s = self._pick_best_audio_following_video()
        if s is None:
            raise RuntimeError('No audio streams found')
        return self._stream_payload(s)

    def _pick_best_audio_following_video(self) -> Optional[_Stream]:
        audios = [s for s in self.streams if s.kind == 'audio']
        if not audios:
            return None

        ref = self._selected_best_video
        if ref is None:
            return max(audios, key=lambda s: (s.seconds, s.bandwidth or 0))

        same_enc = [a for a in audios if a.encrypted == ref.encrypted]
        candidates = same_enc if same_enc else audios

        return min(
            candidates,
            key=lambda a: (abs(a.seconds - ref.seconds), -(a.bandwidth or 0), -a.segments),
        )

    def _load_mpd(self, headers: Dict[str, str]) -> None:
        resp = requests.get(self.mpd_url, headers=headers, timeout=15, impersonate='chrome124')
        console.log(f"[cyan]Response status from MPD URL: [red]{resp.status_code}")
        resp.raise_for_status()
        self.root = ET.fromstring(resp.content)

    def _extract_namespaces(self) -> None:
        if self.root is None:
            return
        if self.root.tag.startswith('{'):
            self.ns['mpd'] = self.root.tag[1:].split('}')[0]
        self.ns.setdefault('cenc', 'urn:mpeg:cenc:2013')

    def _initial_base_url(self) -> str:
        if os.path.exists(self.mpd_url):
            return urljoin('file:', os.path.abspath(self.mpd_url)).rsplit('/', 1)[0] + '/'
        return self.mpd_url.rsplit('/', 1)[0] + '/'

    def _resolve_base_url(self, base: str, node: ET.Element) -> str:
        base_el = node.find('mpd:BaseURL', self.ns)
        if base_el is not None and base_el.text and base_el.text.strip():
            bt = base_el.text.strip()
            return bt if bt.startswith('http') else urljoin(base, bt)
        return base

    def _is_encrypted(self, node: Optional[ET.Element]) -> bool:
        if node is None:
            return False
        for cp in node.findall('.//mpd:ContentProtection', self.ns):
            scheme = (cp.get('schemeIdUri') or '').lower()
            value = (cp.get('value') or '').lower()
            if 'mp4protection' in scheme and 'cenc' in value:
                return True
            if 'cenc' in scheme:
                return True
            if 'edef8ba9-79d6-4ace-a3c8-27dcd51d21ed' in scheme:
                return True
            if '9a04f079-9840-4286-ab92-e65be0885f95' in scheme:
                return True
        return False

    def _collect_pssh(self, node: Optional[ET.Element]) -> Set[str]:
        out: Set[str] = set()
        if node is None:
            return out
        for cp in node.findall('.//mpd:ContentProtection', self.ns):
            pssh_el = cp.find('cenc:pssh', self.ns)
            if pssh_el is not None and pssh_el.text and pssh_el.text.strip():
                out.add(pssh_el.text.strip())
        return out

    def _role(self, adapt: ET.Element) -> str:
        role = adapt.find('mpd:Role', self.ns)
        v = (role.get('value') if role is not None else '') or ''
        return 'Main' if not v or v.strip().lower() == 'main' else v

    def _channels(self, adapt: ET.Element) -> Optional[int]:
        acc = adapt.find('mpd:AudioChannelConfiguration', self.ns)
        if acc is None:
            return None
        try:
            return int(acc.get('value') or '')
        except ValueError:
            return None

    def _segment_count_and_seconds(self, seg_tmpl: ET.Element, *, period_seconds: float, mpd_seconds: float) -> Tuple[int, float]:
        timescale = int(seg_tmpl.get('timescale', 1) or 1)
        if timescale <= 0:
            timescale = 1
        timeline_el = seg_tmpl.find('mpd:SegmentTimeline', self.ns)
        if timeline_el is not None:
            count, units = _timeline_count_and_units(timeline_el, self.ns)
            seconds = (units / timescale) if units > 0 else 0.0
            return (count, seconds if seconds > 0 else period_seconds)

        dur_units = seg_tmpl.get('duration')
        if not dur_units:
            return (0, period_seconds)
        
        seg_units = int(dur_units)
        if seg_units <= 0:
            return (0, period_seconds)
        
        seg_seconds = seg_units / timescale
        total = period_seconds if period_seconds > 0 else mpd_seconds
        return (int(math.ceil((total if total > 0 else 0.0) / seg_seconds)), total)

    def _parse_streams(self) -> List[_Stream]:
        if self.root is None:
            return []

        base = self._initial_base_url()
        base = self._resolve_base_url(base, self.root)

        mpd_seconds = parse_iso8601_duration_seconds(self.root.get('mediaPresentationDuration'))
        periods = self.root.findall('.//mpd:Period', self.ns)

        streams_by_key: Dict[Tuple[Any, ...], _Stream] = {}

        for period in periods:
            period_seconds = parse_iso8601_duration_seconds(period.get('duration'))
            period_base = self._resolve_base_url(base, period)
            period_pssh = self._collect_pssh(period)
            period_enc = self._is_encrypted(period)

            for adapt in period.findall('mpd:AdaptationSet', self.ns):
                role = self._role(adapt)
                lang = (adapt.get('lang') or '').strip()
                fps = _parse_frame_rate(adapt.get('frameRate'))
                channels = self._channels(adapt)

                mime = (adapt.get('mimeType') or '').strip().lower()
                ctype = (adapt.get('contentType') or '').strip().lower()
                if not ctype:
                    if mime.startswith('video/'):
                        ctype = 'video'
                    elif mime.startswith('audio/'):
                        ctype = 'audio'
                    elif mime.startswith('image/'):
                        ctype = 'image'
                    elif mime.startswith('application/'):
                        ctype = 'text'
                kind = 'subtitle' if ctype == 'text' else ctype

                adapt_base = self._resolve_base_url(period_base, adapt)
                adapt_pssh = self._collect_pssh(adapt)
                adapt_enc = self._is_encrypted(adapt)

                adapt_tmpl = adapt.find('mpd:SegmentTemplate', self.ns)

                for rep in adapt.findall('mpd:Representation', self.ns):
                    rep_id = rep.get('id') or ''
                    bw_s = rep.get('bandwidth')
                    bandwidth = int(bw_s) if bw_s and bw_s.isdigit() else None
                    codecs = (rep.get('codecs') or adapt.get('codecs') or '').strip()
                    rep_mime = (rep.get('mimeType') or mime).strip().lower()
                    rep_kind = kind
                    if codecs.lower() in ('wvtt', 'stpp') or rep_mime.startswith('text/'):
                        rep_kind = 'subtitle'

                    w_s = rep.get('width')
                    h_s = rep.get('height')
                    width = int(w_s) if w_s and w_s.isdigit() else None
                    height = int(h_s) if h_s and h_s.isdigit() else None

                    rep_base = self._resolve_base_url(adapt_base, rep)
                    rep_pssh = self._collect_pssh(rep)
                    rep_enc = self._is_encrypted(rep)

                    seg_tmpl = rep.find('mpd:SegmentTemplate', self.ns) or adapt_tmpl
                    if seg_tmpl is None:
                        continue

                    init_tmpl = seg_tmpl.get('initialization') or ''
                    media_tmpl = seg_tmpl.get('media') or ''
                    start_number = int(seg_tmpl.get('startNumber', 1) or 1)
                    timeline_el = seg_tmpl.find('mpd:SegmentTimeline', self.ns)

                    segs, secs = self._segment_count_and_seconds(seg_tmpl, period_seconds=period_seconds, mpd_seconds=mpd_seconds)

                    encrypted = bool(period_enc or adapt_enc or rep_enc or 'widevineplayready' in rep_base.lower())
                    pssh_set: Set[str] = set()
                    pssh_set.update(period_pssh)
                    pssh_set.update(adapt_pssh)
                    pssh_set.update(rep_pssh)
                    fps_key = _format_fps(fps)

                    if self.merge_same_id:
                        key = (rep_kind, encrypted, width, height, rep_id, codecs, fps_key, lang,
                            channels if rep_kind == 'audio' else None, role)
                    else:
                        key = (rep_kind, encrypted, width, height, bandwidth, rep_id, codecs, fps_key, lang,
                            channels if rep_kind == 'audio' else None, role)

                    s = streams_by_key.get(key)
                    if s is None:
                        s = _Stream(
                            kind=rep_kind,
                            encrypted=encrypted,
                            width=width,
                            height=height,
                            bandwidth=bandwidth,
                            rep_id=rep_id,
                            fps=fps,
                            codecs=codecs,
                            lang=lang,
                            channels=channels if rep_kind == 'audio' else None,
                            role=role,
                        )
                        streams_by_key[key] = s
                    else:
                        if bandwidth is not None:
                            s.bandwidth = bandwidth if s.bandwidth is None else max(s.bandwidth, bandwidth)

                    s.segments += int(segs)
                    s.seconds += float(secs)
                    s.pssh_set.update(pssh_set)
                    s.parts.append(
                        _Part(
                            base_url=rep_base,
                            rep_id=rep_id,
                            bandwidth=bandwidth,
                            init_tmpl=init_tmpl,
                            media_tmpl=media_tmpl,
                            start_number=start_number,
                            segments=int(segs),
                            seg_timeline_el=timeline_el,
                        )
                    )

        streams = list(streams_by_key.values())
        if self.min_duration_seconds > 0:
            streams = [s for s in streams if s.seconds >= self.min_duration_seconds]

        return streams

    def _pick_best(self, *, kind: str) -> Optional[_Stream]:
        items = [s for s in self.streams if s.kind == kind]
        if not items:
            return None
        if kind == 'video':
            return max(items, key=lambda s: (s.height or 0, s.width or 0, s.bandwidth or 0))
        return max(items, key=lambda s: (s.bandwidth or 0))

    def _stream_payload(self, s: _Stream) -> Dict[str, Any]:
        init_urls: List[str] = []
        media_urls: List[str] = []

        for part in s.parts:
            init_u = build_url(part.base_url, part.init_tmpl, rep_id=part.rep_id, bandwidth=part.bandwidth)
            if init_u:
                init_urls.append(init_u)

            if not part.media_tmpl:
                continue

            if '$Time$' in part.media_tmpl:
                for t in _timeline_iter_times(part.seg_timeline_el, self.ns):
                    u = build_url(part.base_url, part.media_tmpl, rep_id=part.rep_id, bandwidth=part.bandwidth, time=t)
                    if u:
                        media_urls.append(u)
            elif '$Number' in part.media_tmpl:
                for i in range(part.segments):
                    n = part.start_number + i
                    u = build_url(part.base_url, part.media_tmpl, rep_id=part.rep_id, bandwidth=part.bandwidth, number=n)
                    if u:
                        media_urls.append(u)
            else:
                u = build_url(part.base_url, part.media_tmpl, rep_id=part.rep_id, bandwidth=part.bandwidth)
                if u:
                    media_urls.append(u)

        payload: Dict[str, Any] = {
            'type': s.kind,
            'id': s.rep_id,
            'bandwidth': s.bandwidth or 0,
            'width': s.width or 0,
            'height': s.height or 0,
            'fps': s.fps,
            'codecs': s.codecs,
            'language': s.lang,
            'channels': s.channels,
            'role': s.role,
            'has_drm': s.encrypted,
            'pssh_list': sorted(s.pssh_set),
            'pssh': (sorted(s.pssh_set)[0] if s.pssh_set else ''),
            'expected_segments': s.segments,
            'init_url': (init_urls[0] if init_urls else ''),
            'init_urls': init_urls,
            'media_urls': media_urls,
            'media_url_count': len(media_urls),
            'duration_seconds': s.seconds,
        }
        return payload