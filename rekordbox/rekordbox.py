from rekordbox_mcp.database import RekordboxDatabase
from rekordbox_mcp.models import Playlist, Track, SearchOptions
import asyncio
from utils.title_normalisation import normalise_track_metadata

class Rekordbox:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db = RekordboxDatabase()
            cls._instance.connected = False
        return cls._instance

    async def start_rekordbox_connection(self):
        if not self.connected:
            await self.db.connect()
            self.connected = True
    
    async def process_tracks(self):
        possible_duplicates = []
        playlists = await self.db.get_playlists()
        for playlist in playlists:
            tracks = await self.db.get_playlist_tracks(playlist.id)
            for track in tracks:
                artist, title = normalise_track_metadata(track)

                print(
                    f"""
                ORIGINAL:
                    Artist: {track.artist}
                    Title : {track.title}
                PROPOSED:
                    Artist: {artist or track.artist}
                    Title : {title}
                """
                )

    
    async def update_track(self, track_id: str, new_title: str, new_artist: str):
        def _inner():
            self.db._create_backup()

            content = self.db.db.get_content(ID=int(track_id))
            if not content:
                raise ValueError("Track not found")

            content.Title = new_title
            content.Artist = new_artist
            self.db.db.commit()
            self.db._invalidate_content_cache()

        await asyncio.to_thread(_inner)