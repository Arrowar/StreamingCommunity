import os
import sys


# Fix path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(src_path)


from StreamingCommunity.Util.installer.ffmpeg_install import FFMPEGDownloader


def test_ffmpeg_downloader():
    
    # Create an instance of the downloader
    downloader = FFMPEGDownloader()

    # Check if the download method works and fetches the executables
    ffmpeg, ffprobe, ffplay = downloader.download()

    # Output the destination paths
    print(f"FFmpeg path: {ffmpeg}")
    print(f"FFprobe path: {ffprobe}")
    print(f"FFplay path: {ffplay}")


if __name__ == "__main__":
    test_ffmpeg_downloader()