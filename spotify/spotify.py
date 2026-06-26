import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from models.models import Song, Playlist


def create_spotify_client() -> spotipy.Spotify:
    load_dotenv()

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="playlist-read-private playlist-read-collaborative",
            cache_path=".spotify_token_cache",
            show_dialog=True
        )
    )


def get_playlist(playlist_id: str) -> Playlist:
    sp = create_spotify_client()

    spotify_playlist = sp.playlist(
        playlist_id,
        additional_types=("track",)
    )

    songs: list[Song] = []

    for item in spotify_playlist["items"]["items"]:
        track = item["item"]

        song = Song(
            title=track["name"],
            artist=track["artists"][0]["name"],
            album=track["album"]["name"],
            explicit=track["explicit"],
            duration=track["duration_ms"]
        )

        songs.append(song)

    return Playlist(
        name=spotify_playlist["name"],
        songs=songs
    )