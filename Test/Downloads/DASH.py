# 29.07.25

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.os import get_wvd_path
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity import DASH_Downloader


start_message()
logger = Logger()

license_url = ""
mpd_url = ""

dash_process = DASH_Downloader(
    cdm_device=get_wvd_path(),
    license_url=license_url,
    mpd_url=mpd_url,
    output_path="out.mp4",
)
dash_process.parse_manifest()

if dash_process.download_and_decrypt():
    dash_process.finalize_output()

status = dash_process.get_status()
print(status)