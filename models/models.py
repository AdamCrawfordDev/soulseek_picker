from dataclasses import dataclass

@dataclass
class Song:
    name: str
    artist: list[str]
    album: str
    explicit: bool
    duration_ms: int

@dataclass
class Playlist:
    name: str
    songs: list[Song]
    
    