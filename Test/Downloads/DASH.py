# 29.07.25
# ruff: noqa: E402

import os
import sys


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.utils import config_manager, start_message
from StreamingCommunity.core.downloader import DASH_Downloader


start_message()
conf_extension = config_manager.config.get("M3U8_CONVERSION", "extension")


mpd_url = ''
mpd_headers = {}
license_url = ''
license_headers = {}
license_params = {}
license_ley = None

dash_process = DASH_Downloader(
    mpd_url=mpd_url,
    license_url=license_url,
    output_path=fr".\Video\Prova.{conf_extension}"
)

out_path, need_stop = dash_process.start()
print(f"Output path: {out_path}, Need stop: {need_stop}")