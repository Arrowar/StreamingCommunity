# 23.11.24

# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)



# Import
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity.Api.Player.mixdrop import VideoSource


# Test
start_message()
logger = Logger()
video_source = VideoSource("https://cb01net.uno/pino-daniele-nero-a-meta-hd-2024/")
master_playlist = video_source.get_playlist()
print(master_playlist)