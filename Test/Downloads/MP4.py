# 23.06.24
# ruff: noqa: E402

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.utils import start_message
from StreamingCommunity.core.downloader import MP4_Downloader


start_message()
path, kill_handler = MP4_Downloader(
    url="https://148-251-75-109.top/Getintopc.com/IDA_Pro_2020.mp4",
    path=r".\Video\Prova.mp4"
)

thereIsError = path is None
print(thereIsError)