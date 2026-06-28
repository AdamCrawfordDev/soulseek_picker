from dataclasses import dataclass

@dataclass
class Song:
    title: str
    artist: list[str]
    album: str
    explicit: bool
    duration: int

@dataclass
class InternalPlaylist:
    name: str
    songs: list[Song]

@dataclass
class SongQueueItem:
    song: Song
    normal: bool
    intro: bool
    clean: bool
    clean_intro: bool
    extended: bool