import asyncio
from aioslsk.client import SoulSeekClient
from aioslsk.settings import Settings, CredentialsSettings
import os
from dotenv import load_dotenv
import logging

class Soulseek:
    client: SoulSeekClient

    def __init__(self):
        self.client = SoulSeekClient(settings=init_settings())

    async def start_soulseek_connection(self):
        await self.client.start()
        await self.client.login()

    async def stop_soulseek_connection(self):
        await self.client.stop()

    #return list[SearchResult]
    async def soulseek_song_search(self, song:str):
        request = await self.client.searches.search(song)
        await asyncio.sleep(5)
        return request.results
    
        

def init_settings():
    logging.getLogger("aioslsk").setLevel(logging.CRITICAL)

    load_dotenv()

    return Settings(
        credentials=CredentialsSettings(
            username=os.getenv("SOULSEEK_USERNAME"),
            password=os.getenv("SOULSEEK_PASSWORD")
        )
    )
    
