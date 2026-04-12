import asyncio
import logging
import os

from aiohttp import ClientSession
from dotenv import load_dotenv
from api import api

# =========================
# CONFIG
# =========================
TARGET_POWER = 180
ALLOW_EXPORT = False

# =========================
# Setup
# =========================
load_dotenv()
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

ANKERUSER = os.getenv("ANKERUSER")
ANKERPASSWORD = os.getenv("ANKERPASSWORD")
ANKERCOUNTRY = os.getenv("ANKERCOUNTRY", "DE")

# Optional setzen (empfohlen!)
SITE_ID = os.getenv("ANKER_SITE_ID")
DEVICE_SN = os.getenv("ANKER_DEVICE_SN")


async def main():
    async with ClientSession() as session:
        myapi = api.AnkerSolixApi(
            ANKERUSER,
            ANKERPASSWORD,
            ANKERCOUNTRY,
            session,
            LOGGER,
        )

        print("→ Lade Daten...")
        await myapi.update_sites()
        await myapi.update_device_details()

        # Falls nicht gesetzt → automatisch erste Solarbank nehmen
        site_id = SITE_ID
        device_sn = DEVICE_SN

        if not site_id or not device_sn:
            print("→ Suche Solarbank automatisch...")

            for sn, dev in myapi.devices.items():
                if "solarbank" in str(dev).lower():
                    site_id = dev.get("site_id")
                    device_sn = sn
                    break

        if not site_id or not device_sn:
            raise RuntimeError("Keine Solarbank gefunden!")

        print(f"→ Verwende device_sn={device_sn}")
        print(f"→ site_id={site_id}")

        print("\n→ Setze Werte:")
        print(f"   power = {TARGET_POWER}")
        print(f"   export = {ALLOW_EXPORT}")

        result = await myapi.set_home_load(
            siteId=site_id,
            deviceSn=device_sn,
            preset=TARGET_POWER,
            export=ALLOW_EXPORT,
        )

        print("\n→ Ergebnis:")
        print(result)

        # Danach nochmal Status holen
        await myapi.update_sites()
        await myapi.update_device_details()

        dev = myapi.devices.get(device_sn, {})

        print("\n→ Neue Werte laut API:")
        print("preset_system_output_power =", dev.get("preset_system_output_power"))
        print("preset_allow_export        =", dev.get("preset_allow_export"))


if __name__ == "__main__":
    asyncio.run(main())