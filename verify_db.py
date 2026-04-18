import asyncio
from database.db import init_db

asyncio.run(init_db())
print("OK")