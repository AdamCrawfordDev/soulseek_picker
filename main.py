import asyncio
from rekordbox_mcp.database import RekordboxDatabase
from rekordbox.rekordbox import Rekordbox
rb = Rekordbox()
asyncio.run(rb.start_rekordbox_connection())
asyncio.run(rb.process_tracks())