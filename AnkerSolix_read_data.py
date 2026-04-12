import asyncio
import json
import logging
import os

from aiohttp import ClientSession
from dotenv import load_dotenv

from api import api


load_dotenv()

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def pretty(title: str, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))


async def main():
    user = os.getenv("ANKERUSER")
    password = os.getenv("ANKERPASSWORD")
    country = os.getenv("ANKERCOUNTRY", "DE")

    if not user or not password:
        raise RuntimeError("ANKERUSER oder ANKERPASSWORD fehlt in der .env")

    async with ClientSession() as websession:
        myapi = api.AnkerSolixApi(
            user,
            password,
            country,
            websession,
            LOGGER,
        )

        # Basisdaten aus der Cloud holen
        await myapi.update_sites()

        # Optional, aber meist hilfreich:
        await myapi.update_device_details()

        pretty("Account", myapi.account)
        pretty("Sites", myapi.sites)
        pretty("Devices", myapi.devices)

        # Wichtig: Solarbank-SN finden
        for device_sn, device in myapi.devices.items():
            dev_type = device.get("type")
            name = device.get("name")
            model = device.get("device_pn") or device.get("product_code")
            print(
                f"SN={device_sn} | type={dev_type} | name={name} | model={model}"
            )


if __name__ == "__main__":
    asyncio.run(main())