# Important libraries
import os
from dotenv import load_dotenv
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from models.models import Song, Playlist

class SpotifyHandler():

    c_id: str
    c_secret: str
    c_playlist: str
    access_token: str
    
    def __init__(self, playlist):
        self.c_playlist = playlist
    
    def startService(self):
        self.getClientEnvironmentDetails()
        self.getPlaylist()
        
    def getClientEnvironmentDetails(self):
        
        load_dotenv()

        self.c_id = os.getenv('CLIENT_ID')
        self.c_secret = os.getenv('CLIENT_SECRET')
        
    def getPlaylist(self):
        sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=self.c_id,
                client_secret=self.c_secret,
                redirect_uri="http://127.0.0.1:8888/callback",
                scope="playlist-read-private playlist-read-collaborative",
                cache_path=".spotify_token_cache",
                show_dialog=True
            )
        )

        playlist_id = self.c_playlist
        
        spotipy_playlist = sp.playlist(
            playlist_id,
            additional_types=("track",)
        )
        print(spotipy_playlist['name'])
        items = spotipy_playlist["items"]["items"]
        songs: list[Song] = []

        for item in items:
            track = item["item"]

            artist = track["artists"][0]["name"]
            title = track["name"]
            duration = track["duration_ms"]
            explicit = track["explicit"]
            album = track["album"]["name"]

            song = Song(title, artist, album, explicit, duration)
            songs.append(song)

            print(f"{artist} - {title} - {duration} - {explicit} - {album}")

        playlist = Playlist(spotipy_playlist["name"], songs)
        print(playlist.songs[0])
        return playlist
                    
        
                        
