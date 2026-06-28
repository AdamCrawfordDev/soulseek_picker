import asyncio
from utils.find_duplicates import build_queue
from spotify.spotify import get_playlist
from models.models import Song

asyncio.run(build_queue(get_playlist("3uYQTjfq6QWuKrQCEEkZc2")))