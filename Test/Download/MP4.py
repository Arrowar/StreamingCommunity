# 23.06.24

import os
import sys
import unittest


# Fix import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.os import os_summary
os_summary.get_system_summary()
from StreamingCommunity.Util.logger import Logger
from StreamingCommunity import MP4_downloader



class TestMP4Downloader(unittest.TestCase):
    def setUp(self):
        os_summary.get_system_summary()
        self.logger = Logger()
        
    def test_mp4_download(self):
        path, kill_handler = MP4_downloader(
            url="https://148-251-75-109.top/Getintopc.com/IDA_Pro_2020.mp4",
            path=r".\\Video\\undefined.mp4"
        )
        
        thereIsError = path is None
        self.assertFalse(thereIsError, "MP4 download resulted in an error")

if __name__ == '__main__':
    unittest.main()