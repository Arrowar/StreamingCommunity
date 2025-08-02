# 29.07.25

# Fix import
import sys
import os
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)



# Import
from StreamingCommunity.Util.message import start_message
from StreamingCommunity.Util.os import os_summary, get_wvd_path
os_summary.get_system_summary()
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity.Lib.Downloader.DASH.downloader import DASH_Download


start_message()
logger = Logger()

license_url = ""
mpd_url = ""


r_proc = DASH_Download(
    cdm_device=get_wvd_path(),
    license_url=license_url,
    mpd_url=mpd_url,
    output_path="out.mp4",
)
r_proc.parse_manifest()

if r_proc.download_and_decrypt():
    r_proc.finalize_output()

status = r_proc.get_status()
print(status)