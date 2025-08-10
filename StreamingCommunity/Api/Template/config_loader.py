# 11.02.25

import os
import inspect


# Internal utilities
from StreamingCommunity.Util.config_json import config_manager


def get_site_name_from_stack():
    for frame_info in inspect.stack():
        file_path = frame_info.filename

        # Common case: path contains Api/Site/<site>/__init__.py
        try:
            marker = os.path.join('Api', 'Site') + os.sep
            if marker in file_path and '__init__' in file_path:
                parts = file_path.split(marker)
                if len(parts) > 1:
                    site_name = parts[1].split(os.sep)[0]
                    return site_name
        except Exception:
            pass

        # Fallback: if path contains 'Site' folder, try a more permissive split
        try:
            if 'Site' + os.sep in file_path and '__init__' in file_path:
                parts = file_path.split('Site' + os.sep)
                if len(parts) > 1:
                    site_name = parts[1].split(os.sep)[0]
                    return site_name
        except Exception:
            pass

        # Last-resort: try to infer module/package name from the frame
        try:
            module = inspect.getmodule(frame_info.frame)
            if module is not None and hasattr(module, '__package__') and module.__package__:
                # package typically like 'StreamingCommunity.Api.Site.<site>'
                pkg = module.__package__
                if 'Api.Site.' in pkg:
                    site_name = pkg.split('Api.Site.')[-1].split('.')[0]
                    return site_name
        except Exception:
            pass

    return None


class SiteConstant:
    @property
    def SITE_NAME(self):
        return get_site_name_from_stack()
    
    @property
    def ROOT_PATH(self):
        return config_manager.get('OUT_FOLDER', 'root_path')
    
    @property
    def FULL_URL(self):
        return config_manager.get_site(self.SITE_NAME, 'full_url').rstrip('/')
    
    @property
    def SERIES_FOLDER(self):
        base_path = self.ROOT_PATH
        if config_manager.get_bool("OUT_FOLDER", "add_siteName"):
            base_path = os.path.join(base_path, self.SITE_NAME)
        return os.path.join(base_path, config_manager.get('OUT_FOLDER', 'serie_folder_name'))
    
    @property
    def MOVIE_FOLDER(self):
        base_path = self.ROOT_PATH
        if config_manager.get_bool("OUT_FOLDER", "add_siteName"):
            base_path = os.path.join(base_path, self.SITE_NAME)
        return os.path.join(base_path, config_manager.get('OUT_FOLDER', 'movie_folder_name'))
    
    @property
    def ANIME_FOLDER(self):
        base_path = self.ROOT_PATH
        if config_manager.get_bool("OUT_FOLDER", "add_siteName"):
            base_path = os.path.join(base_path, self.SITE_NAME)
        return os.path.join(base_path, config_manager.get('OUT_FOLDER', 'anime_folder_name'))
    
    @property
    def COOKIE(self):
        try:
            return config_manager.get_dict('SITE_EXTRA', self.SITE_NAME)
        except KeyError:
            return None
    
    @property
    def TELEGRAM_BOT(self):
        return config_manager.get_bool('DEFAULT', 'telegram_bot')


site_constant = SiteConstant()