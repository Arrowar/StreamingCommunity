# 23.06.24

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity import HLS_Downloader


start_message()
Logger()
hls_process =  HLS_Downloader(
    output_path=".\\Video\\test.mp4",
    m3u8_url="https://acdn.ak-stream-videoplatform.sky.it/hls/2024/11/21/968275/master.m3u8"
).start()

thereIsError = hls_process['error'] is not None
print(thereIsError)