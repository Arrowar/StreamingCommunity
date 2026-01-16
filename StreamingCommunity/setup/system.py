# 18.07.25


from .checker import check_bento4, check_ffmpeg, check_megatools, check_n_m3u8dl_re, check_shaka_packager
from .device_install import check_device_wvd_path, check_device_prd_path


ffmpeg_path, ffprobe_path = check_ffmpeg()
bento4_decrypt_path = check_bento4()
wvd_path = check_device_wvd_path()
prd_path = check_device_prd_path()
megatools_path = check_megatools()
n_m3u8dl_re_path = check_n_m3u8dl_re()
shaka_packager = check_shaka_packager()


def get_ffmpeg_path() -> str:
    return ffmpeg_path

def get_ffprobe_path() -> str:
    return ffprobe_path

def get_bento4_decrypt_path() -> str:
    return bento4_decrypt_path

def get_wvd_path() -> str:
    return wvd_path

def get_prd_path() -> str:
    return prd_path

def get_megatools_path() -> str:
    return megatools_path

def get_n_m3u8dl_re_path() -> str:
    return n_m3u8dl_re_path

def get_shaka_packager_path() -> str:
    return shaka_packager

def get_info_wvd(cdm_device_path):
    if cdm_device_path is not None:
        from pywidevine.device import Device

        device = Device.load(cdm_device_path)

        # Extract client info
        info = {ci.name: ci.value for ci in device.client_id.client_info}
        model = info.get("model_name", "N/A")

        device_name = info.get("device_name", "").lower()
        build_info = info.get("build_info", "").lower()

        # Extract device type
        is_emulator = any(x in device_name for x in [
            "generic", "sdk", "emulator", "x86"
        ]) or "test-keys" in build_info or "userdebug" in build_info
        
        if "tv" in model.lower():
            dev_type = "Android TV"
        elif is_emulator:
            dev_type = "Android Emulator"
        else:
            dev_type = "Android Phone"

        return (
            f"[cyan]Load WVD: "
            f"[red]L{device.security_level} [cyan]| [red]{dev_type} [cyan]| "
            f"[cyan]SysID: [red]{device.system_id}"
        )

def get_info_prd(cdm_device_path):
    if cdm_device_path is not None:
        from pyplayready.device import Device

        device = Device.load(cdm_device_path)
        cert_chain = device.group_certificate
        leaf_cert = cert_chain.get(0)

        return (
            f"[cyan]Load PRD: "
            f"[red]SL{device.security_level} [cyan]| "
            f"[yellow]{leaf_cert.get_name()} "
        )