import asyncio
import logging

from aiohttp import ClientSession

from config import (
    ANKERCOUNTRY,
    ANKER_DEVICE_SN,
    ANKER_IDLE_POWER_W,
    ANKERPASSWORD,
    ANKER_POWER_200_W,
    ANKER_POWER_400_W,
    ANKER_SITE_ID,
    ANKERUSER,
    GRID_OFF_THRESHOLD_W,
    GRID_ON_200_THRESHOLD_W,
    GRID_ON_400_THRESHOLD_W,
    LOW_POWER_DURATION_SECONDS,
    MIN_BATTERY_SOC_PERCENT,
    POLL_INTERVAL_SECONDS,
    SHELLY_URL,
)
from read import get_shelly_power
from write import (
    create_anker_api,
    find_solarbank_device,
    refresh_anker_data,
    set_anker_home_load,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)

STATE_OFF = "OFF"
STATE_DISCHARGE_200W = "DISCHARGE_200W"
STATE_DISCHARGE_400W = "DISCHARGE_400W"


def get_battery_soc(device: dict) -> float | None:
    for key in ["battery_soc", "soc", "battery_percentage", "battery_level"]:
        value = device.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def choose_target_state(
    power: float,
    battery_soc: float | None,
    current_state: str | None,
    low_power_since: float | None,
    now: float,
) -> tuple[str | None, float | None]:
    if battery_soc is not None and battery_soc < MIN_BATTERY_SOC_PERCENT:
        return STATE_OFF, None

    if power > GRID_ON_400_THRESHOLD_W:
        return STATE_DISCHARGE_400W, None

    if power > GRID_ON_200_THRESHOLD_W:
        return STATE_DISCHARGE_200W, None

    if power < GRID_OFF_THRESHOLD_W:
        if low_power_since is None:
            return current_state, now
        if now - low_power_since >= LOW_POWER_DURATION_SECONDS:
            return STATE_OFF, low_power_since
        return current_state, low_power_since

    return current_state, None


async def apply_state(myapi, site_id: str, device_sn: str, target_state: str) -> None:
    if target_state == STATE_OFF:
        LOGGER.info("Schalte Batterie AUS.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_IDLE_POWER_W,
            allow_export=False,
        )
        LOGGER.info("Anker Antwort: %s", result)

    elif target_state == STATE_DISCHARGE_200W:
        LOGGER.info("Setze Batterie auf 200 W Einspeisung.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_POWER_200_W,
            allow_export=True,
        )
        LOGGER.info("Anker Antwort: %s", result)

    elif target_state == STATE_DISCHARGE_400W:
        LOGGER.info("Setze Batterie auf 400 W Einspeisung.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_POWER_400_W,
            allow_export=True,
        )
        LOGGER.info("Anker Antwort: %s", result)


async def main() -> None:
    async with ClientSession() as session:
        myapi = await create_anker_api(
            user=ANKERUSER,
            password=ANKERPASSWORD,
            country=ANKERCOUNTRY,
            session=session,
        )

        LOGGER.info("Lade Anker-Geräte...")
        await refresh_anker_data(myapi)

        site_id, device_sn = find_solarbank_device(
            myapi=myapi,
            configured_site_id=ANKER_SITE_ID,
            configured_device_sn=ANKER_DEVICE_SN,
        )

        LOGGER.info("Solarbank gefunden: site_id=%s | device_sn=%s", site_id, device_sn)

        current_state: str | None = None
        low_power_since: float | None = None

        while True:
            try:
                power = get_shelly_power(SHELLY_URL)

                await refresh_anker_data(myapi)
                device = myapi.devices.get(device_sn, {})
                battery_soc = get_battery_soc(device)

                now = asyncio.get_running_loop().time()

                LOGGER.info(
                    "Shelly power = %.2f W | battery_soc = %s | state = %s",
                    power,
                    battery_soc,
                    current_state,
                )

                target_state, low_power_since = choose_target_state(
                    power=power,
                    battery_soc=battery_soc,
                    current_state=current_state,
                    low_power_since=low_power_since,
                    now=now,
                )

                if target_state != current_state and target_state is not None:
                    await apply_state(
                        myapi=myapi,
                        site_id=site_id,
                        device_sn=device_sn,
                        target_state=target_state,
                    )
                    current_state = target_state

            except Exception as exc:
                LOGGER.exception("Fehler in main loop: %s", exc)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())