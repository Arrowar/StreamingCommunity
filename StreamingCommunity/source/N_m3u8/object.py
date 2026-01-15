# 04.01.25


class StreamInfo:
    def __init__(self, type_: str, language: str = "", resolution: str = "", codec: str = "", bandwidth: str = "", name: str = "", selected: bool = False, encrypted: bool = False, extension: str = "", total_duration: float = 0.0, segment_count: int = 0):
        self.type = type_
        self.language = language
        self.resolution = resolution
        self.codec = codec
        self.bandwidth = bandwidth
        self.name = name
        self.selected = selected
        self.encrypted = encrypted
        self.extension = extension
        self.total_duration = total_duration
        self.segment_count = segment_count
        self.final_size = None