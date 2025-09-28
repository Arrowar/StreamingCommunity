# 07.07.24

from typing import List, TypedDict


class MediaItemData(TypedDict, total=False):
    id: int                 # GENERAL
    name: str               # GENERAL     
    type: str               # GENERAL
    url: str                # GENERAL
    size: str               # GENERAL
    score: str              # GENERAL
    date: str               # GENERAL
    desc: str               # GENERAL

    seeder: int             # TOR
    leecher: int            # TOR

    slug: str               # SC
    

class MediaItemMeta(type):
    def __new__(cls, name, bases, dct):
        def init(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        dct['__init__'] = init

        def get_attr(self, item):
            return self.__dict__.get(item, None)

        dct['__getattr__'] = get_attr

        def set_attr(self, key, value):
            self.__dict__[key] = value

        dct['__setattr__'] = set_attr

        return super().__new__(cls, name, bases, dct)


class MediaItem(metaclass=MediaItemMeta):
    id: int                 # GENERAL
    name: str               # GENERAL     
    type: str               # GENERAL
    url: str                # GENERAL
    size: str               # GENERAL
    score: str              # GENERAL
    date: str               # GENERAL
    desc: str               # GENERAL

    seeder: int             # TOR
    leecher: int            # TOR

    slug: str               # SC

    
class MediaManager:
    def __init__(self):
        self.media_list: List[MediaItem] = []

    def add_media(self, data: dict) -> None:
        """
        Add media to the list.

        Args:
            data (dict): Media data to add.
        """
        self.media_list.append(MediaItem(**data))

    def get(self, index: int) -> MediaItem:
        """
        Get a media item from the list by index.

        Args:
            index (int): The index of the media item to retrieve.

        Returns:
            MediaItem: The media item at the specified index.
        """
        return self.media_list[index]

    def get_length(self) -> int:
        """
        Get the number of media items in the list.

        Returns:
            int: Number of media items.
        """
        return len(self.media_list)

    def clear(self) -> None:
        """
        This method clears the media list.
        """
        self.media_list.clear()

    def __str__(self):
        return f"MediaManager(num_media={len(self.media_list)})"