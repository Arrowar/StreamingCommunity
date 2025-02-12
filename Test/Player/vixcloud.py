# 23.11.24

# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)



# Import
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity.Api.Player.vixcloud import VideoSource


# Test
start_message()
logger = Logger()
video_source = VideoSource("streamingcommunity")
video_source.setup("1171b9202c71489193f5fed2bc7b43bb", "computer", 778)
video_source.get_iframe()
video_source.get_content()
master_playlist = video_source.get_playlist()

print(master_playlist)