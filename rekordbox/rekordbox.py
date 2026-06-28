from rekordbox_mcp.database import RekordboxDatabase
from rekordbox_mcp.models import Playlist, Track, SearchOptions
import asyncio

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
    
    async def get_playlists(self):        
        playlists = await self.db.get_playlists()
        return playlists
    
    async def get_tracks(self, playlist: Playlist):
        return await self.db.get_playlist_tracks(playlist.id)

    async def search_tracks(self, title : str | None, artist : str | None):            
        if title and artist:
            return await self.db.search_tracks(SearchOptions(title = title, artist=artist))
        if artist:
            return await self.db.search_tracks(SearchOptions(artist = artist))
        if title:
            return await self.db.search_tracks(SearchOptions(title=title))
    async def update_track(self, track_id, new_title, new_artist=None):
        def _inner():
            content = self.db.db.get_content(ID=int(track_id))

            if not content:
                return

            # safe scalar update
            content.Title = new_title

            # proper artist update
            if new_artist:
                existing = self.db.db.get_artist(Name=new_artist)

                artist = None
                if hasattr(existing, "first"):
                    artist = existing.first()
                else:
                    artist = next(iter(existing), None)

                if artist is None:
                    artist = self.db.db.add_artist(new_artist)

                content.ArtistID = artist.ID

            self.db.db.commit()

        await asyncio.to_thread(_inner)