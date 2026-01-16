# 04.01.25

import re


PERCENT_RE = re.compile(r"(\d+\.\d+)%")
SPEED_RE = re.compile(r"(\d+\.\d+(?:MB|KB|GB)ps)")
SIZE_RE = re.compile(r"(\d+\.\d+(?:MB|GB|KB))/(\d+\.\d+(?:MB|GB|KB))")
SEGMENT_RE = re.compile(r"(\d+)/(\d+)")
VIDEO_LINE_RE = re.compile(r"Vid\s+(\d+x\d+)")
AUDIO_LINE_RE = re.compile(r"Aud\s+([^|]+?)\s*\|\s*([\w-]+)")
SUBTITLE_LINE_RE = re.compile(r"Sub\s+([\w-]+)\s*\|\s*([^|━ \-]+)")
SUBTITLE_SIMPLE_RE = re.compile(r"Sub\s+([\w-]+)\s+-+")
SUBTITLE_FINAL_SIZE_RE = re.compile(r"(\d+\.\d+(?:B|KB|MB|GB))\s+\-\s+00:00:00")