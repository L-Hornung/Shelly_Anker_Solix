import asyncio
import logging
import os

from aiohttp import ClientSession
from dotenv import load_dotenv
from api import api

load_dotenv()
logging.basicConfig(level=logging.INFO)

async def main():
    async with ClientSession() as session:
        myapi = api.AnkerSolixApi(
            os.getenv("ANKERUSER"),
            os.getenv("ANKERPASSWORD"),
            os.getenv("ANKERCOUNTRY", "DE"),
            session,
            logging.getLogger(__name__),
        )

        await myapi.update_sites()
        await myapi.update_device_details()

        print("\n=== DEVICES ===")
        for sn, dev in myapi.devices.items():
            print("device_sn:", sn)
            print("site_id :", dev.get("site_id"))
            print("name    :", dev.get("name"))
            print("type    :", dev.get("type"))
            print("-" * 40)

asyncio.run(main())