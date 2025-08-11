
import os
import sys


# Fix path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.logger import Logger
from StreamingCommunity.Api.Player.mixdrop import VideoSource


# Test
Logger()
video_source = VideoSource("https://cb01net.uno/pino-daniele-nero-a-meta-hd-2024/")
master_playlist = video_source.get_playlist()
print(master_playlist)