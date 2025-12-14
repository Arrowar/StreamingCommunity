# 29.07.25
# ruff: noqa: E402

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity import DASH_Downloader


start_message()
logger = Logger()


mpd_url = ""
mpd_headers = {}
license_url = ""
license_params = {}
license_headers = {}

dash_process = DASH_Downloader(
    license_url=license_url,
    mpd_url=mpd_url,
    output_path="out.mp4",
)
dash_process.parse_manifest(custom_headers=mpd_headers)

if dash_process.download_and_decrypt(custom_headers=license_headers, query_params=license_params):
    dash_process.finalize_output()

status = dash_process.get_status()
print(status)