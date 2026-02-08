# 23.11.24

from datetime import datetime
from typing import Any, List, Optional


# Internal utilities
from StreamingCommunity.utils import config_manager, tmdb_client


# Variable
TMDB_KEY = config_manager.login.get('TMDB', 'api_key')


class Episode:
    def __init__(self, id: Optional[Any] = None, video_id: Optional[str] = None, number: Optional[Any] = None, name: Optional[str] = None, 
        duration: Optional[Any] = None, url: Optional[str] = None, mpd_id: Optional[str] = None, channel: Optional[str] = None, category: Optional[str] = None,
        description: Optional[str] = None, image: Optional[str] = None, poster: Optional[str] = None, year: Optional[Any] = None, is_special: Optional[bool] = None,
        **kwargs
    ):
        self.id = id
        self.video_id = video_id
        self.number = number
        self.name = name
        self.duration = duration
        self.url = url
        self.mpd_id = mpd_id
        self.channel = channel
        self.category = category
        self.description = description
        self.image = image
        self.poster = poster
        self.year = year
        self.is_special = is_special
        
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> dict:
        """Convert the episode to a dictionary."""
        return self.__dict__.copy()

    def __str__(self):
        return f"Episode(id={self.id}, number={self.number}, name='{self.name}', duration={self.duration} sec)"

class EpisodeManager:
    def __init__(self):
        self.episodes: List[Episode] = []

    def add(self, episode: Episode):
        """
        Add a new episode to the manager.
        """
        self.episodes.append(episode)

    def get(self, index: int) -> Episode:
        """
        Retrieve an episode by its index in the episodes list.
        """
        return self.episodes[index]
    
    def clear(self) -> None:
        """
        This method clears the episodes list.
        """
        self.episodes.clear()

    def __len__(self) -> int:
        """
        Get the number of episodes in the manager.
        """
        return len(self.episodes)

    def __str__(self):
        return f"EpisodeManager(num_episodes={len(self.episodes)})"


class Season:
    def __init__(self, id: Optional[int] = None, number: Optional[int] = None, name: Optional[str] = None, slug: Optional[str] = None, type: Optional[str] = None, **kwargs):
        self.id = id
        self.number = number
        self.name = name
        self.slug = slug
        self.type = type
        self.episodes: EpisodeManager = EpisodeManager()
        
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f"Season(id={self.id}, number={self.number}, name='{self.name}', episodes={self.episodes.__len__()})"

class SeasonManager:
    def __init__(self):
        self.seasons: List[Season] = []
    
    def add(self, season: Season) -> Season:
        """
        Add a new season to the manager and return it.
        """
        self.seasons.append(season)
        self.seasons.sort(key=lambda x: x.number)
        return season
        
    def get_season_by_number(self, number: int) -> Optional[Season]:
        """
        Get a season by its number.
        """
        if len(self.seasons) == 1:
            return self.seasons[0]
        
        for season in self.seasons:
            if season.number == number:
                return season
            
        return None
    
    def __len__(self) -> int:
        """
        Return the number of seasons managed.
        """
        return len(self.seasons)

    
class EntriesMeta(type):
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

class Entries(metaclass=EntriesMeta):
    id: int
    name: str
    type: str
    url: str
    size: str
    score: str
    desc: str
    slug: str
    year: str
    provider_language: str

    def to_dict(self):
        """Convert the entries to a dictionary."""
        return self.__dict__.copy()

    @property
    def is_movie(self) -> bool:
        """Check if the entries is a movie."""
        return str(getattr(self, 'type', '')).lower() in ['film', 'movie', 'ova']

    @property
    def poster(self) -> str:
        """Get the poster image url."""
        return getattr(self, 'image', '') or getattr(self, 'poster_url', '')

class EntriesManager:
    def __init__(self):
        self.media_list: List[Entries] = []

    def add(self, media) -> None:
        """
        Add media to the list.

        Args:
            media (Entries): Media item to add.
        """
        # Logic to fetch year if 9999
        if media.year == "9999":
            if (TMDB_KEY != '' and TMDB_KEY is not None):
                if (media.slug and media.slug != ''):
                    print(f"Fetching year for slug: {media.slug}, type: {media.type}")
                    media.year = str(tmdb_client.get_year_by_slug_and_type(media.slug, media.type) or "9999")
                    if media.year == "9999":
                        print("Cant fetch year setting current year.")
                        media.year = str(datetime.now().year)

                elif (media.name and media.name != ''):
                    print(f"Fetching year for name: {media.name}, type: {media.type}")
                    media.year = str(tmdb_client.get_year_by_slug_and_type(media.name.replace(' ', '-').lower(), media.type) or "9999")
                    if media.year == "9999":
                        print("Cant fetch year setting current year.")
                        media.year = str(datetime.now().year)

        self.media_list.append(media)

    def get(self, index: int) -> Entries:
        """
        Get a media item from the list by index.
        """
        return self.media_list[index]

    def __len__(self) -> int:
        """
        Get the number of media items in the list.
        """
        return len(self.media_list)

    def clear(self) -> None:
        """
        This method clears the media list.
        """
        self.media_list.clear()

    def __str__(self):
        return f"EntriesManager(num_media={len(self.media_list)})"