# 25-06-2020
# ruff: noqa: E402

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity import Mega_Downloader


start_message()
Logger()
mega = Mega_Downloader()
m = mega.login()

output_path = m.download_url(
    url="https://mega.nz/file/0kgCWZZB#7u....",
    dest_path=".\\prova.mp4"
)