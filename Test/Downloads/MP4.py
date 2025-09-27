# 23.06.24

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity import MP4_downloader


start_message()
Logger()
path, kill_handler = MP4_downloader(
    url="https://148-251-75-109.top/Getintopc.com/IDA_Pro_2020.mp4",
    path=r".\\Video\\undefined.mp4"
)

thereIsError = path is None
print(thereIsError)