import asyncio
import csv
from datetime import datetime
import logging
import os

from aiohttp import ClientSession

from config import (
    ANKERCOUNTRY,
    ANKER_DEVICE_SN,
    ANKER_IDLE_POWER_W,
    ANKERPASSWORD,
    ANKER_POWER_150_W,
    ANKER_POWER_200_W,
    ANKER_POWER_400_W,
    ANKER_POWER_800_W,
    ANKER_SITE_ID,
    ANKERUSER,
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

# --- Logfile mit Start-Zeitstempel ---
start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = f"battery_log_{start_time}.csv"


# --- Header nur einmal schreiben ---
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "power_shelly_raw_w",
            "battery_output_set_w",
            "battery_output_measured_w",
            "current_state"
        ])


def log_battery(
    power_shelly_raw: float,
    battery_output_measured: float | None,
    battery_output_set: float | None,
    current_state: str | None
):
    timestamp = datetime.now().isoformat(timespec="milliseconds")

    with open(LOG_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            round(power_shelly_raw, 2),
            round(battery_output_set or 0, 2),
            round(battery_output_measured or 0, 2),
            current_state
        ])


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger(__name__)

STATE_OFF = "OFF"
STATE_DISCHARGE_150W = "DISCHARGE_150W"
STATE_DISCHARGE_200W = "DISCHARGE_200W"
STATE_DISCHARGE_400W = "DISCHARGE_400W"
STATE_DISCHARGE_800W = "DISCHARGE_800W"


def get_battery_soc(device: dict) -> float | None:
    for key in ["battery_soc", "soc", "battery_percentage", "battery_level"]:
        value = device.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None
def get_battery_real_output_power(device: dict) -> float | None:
    value = device.get("output_power")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return None
def get_battery_set_output_power(device: dict) -> float | None:
    value = device.get("set_output_power")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return None
def set_battery_state(battery_power_set: float):
    
    if battery_power_set >= ANKER_POWER_800_W:
        LOGGER.info("Setze Batterie State initial mit Wert: %.2f W auf ANKER_POWER_800_W", battery_power_set)
        return STATE_DISCHARGE_800W
    if battery_power_set >= ANKER_POWER_400_W:
        LOGGER.info("Setze Batterie State initial mit Wert: %.2f W auf ANKER_POWER_400_W", battery_power_set)
        return STATE_DISCHARGE_400W
    if battery_power_set >= ANKER_POWER_200_W:
        LOGGER.info("Setze Batterie State initial mit Wert: %.2f W auf ANKER_POWER_200_W", battery_power_set)
        return STATE_DISCHARGE_200W
    if battery_power_set >= ANKER_POWER_150_W:
        LOGGER.info("Setze Batterie State initial mit Wert: %.2f W auf ANKER_POWER_150_W", battery_power_set)
        return STATE_DISCHARGE_150W

    LOGGER.info("Setze Batterie State initial mit Wert: %.2f W aber kein wert gefunden wird auf STATE_OFF gesetzt", battery_power_set)
    return STATE_OFF
def choose_target_state(
    power_shelly_raw: float,
    battery_soc: float | None,
    battery_output_measured: float | None,
    battery_output_set: float | None,
    current_state: str | None,
    low_power_since: float | None,
    now: float,
) -> tuple[str | None, float | None]:

    battery_power = battery_output_measured or 0
    grid_power = power_shelly_raw + battery_power

    # --- Logging ---
    log_battery(
        power_shelly_raw=power_shelly_raw,
        battery_output_measured=battery_output_measured,
        battery_output_set=battery_output_set,
        current_state=current_state
    )

    LOGGER.info(
        "FLOW grid=%.0fW battery_output_measured=%s soc=%s state=%s low_power_since=%s battery_output_set=%s",
        grid_power,
        battery_output_measured,
        battery_soc,
        current_state,
        low_power_since,
        battery_output_set
    )

    # --- SOC Schutz (nur Notfall) ---
    if battery_soc is not None and battery_soc < MIN_BATTERY_SOC_PERCENT:
        LOGGER.warning("SOC LOW -> OFF (%.1f%%)", battery_soc)
        return STATE_OFF, None


    LOGGER.info(
        "SUMME Power:=%.0fW, Shelly Power:=%.0fW, Output Power Battery:=%.0fW, state=%s, battery=%.1f%%",
        grid_power, 
        power_shelly_raw, 
        battery_power,
        current_state,
        battery_soc
        )
    
    if power_shelly_raw < -10:
        LOGGER.warning("Starker Export erkannt (%.2f W) Shelly im negativen Bereich -> eine stufe tiefer", power_shelly_raw)
        if current_state == STATE_DISCHARGE_800W:
            return STATE_DISCHARGE_400W, now
        if current_state == STATE_DISCHARGE_400W:
            return STATE_DISCHARGE_200W, now
        if current_state == STATE_DISCHARGE_200W:
            return STATE_DISCHARGE_150W, now
        return STATE_OFF, now
    # --- Stufenweise runterregeln ---
    if grid_power < 0:
        if current_state != STATE_OFF:
            LOGGER.info("→ OFF (strong export)")
        return STATE_OFF, now

    if grid_power > 800:
        if current_state != STATE_DISCHARGE_800W:
            LOGGER.info("→ 800W ")
        return STATE_DISCHARGE_800W, now

    if grid_power > 400:
        if current_state != STATE_DISCHARGE_400W:
            LOGGER.info("→ 400W")
        return STATE_DISCHARGE_400W, now

    if grid_power > 200:
        if current_state != STATE_DISCHARGE_200W:
            LOGGER.info("→ 200W (slight export)")
        return STATE_DISCHARGE_200W, now
    
    if grid_power > 150:
        if current_state != STATE_DISCHARGE_150W:
            LOGGER.info("→ 150W (slight export)")
        return STATE_DISCHARGE_150W, now
    if grid_power < 150:
        if current_state != STATE_OFF:
            LOGGER.info("State OFF")
        return STATE_OFF, now
    
    LOGGER.info(
        "kein neuer State gewählt gib zurück current_state=%s low_power_since=%s",
        current_state,
        low_power_since
    )

    return current_state, low_power_since


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
    elif target_state == STATE_DISCHARGE_150W:
        LOGGER.info("Setze Batterie auf 150 W Einspeisung.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_POWER_150_W,
            allow_export=True,
        )
    elif target_state == STATE_DISCHARGE_200W:
        LOGGER.info("Setze Batterie auf 200 W Einspeisung.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_POWER_200_W,
            allow_export=True,
        )
    elif target_state == STATE_DISCHARGE_400W:
        LOGGER.info("Setze Batterie auf 400 W Einspeisung.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_POWER_400_W,
            allow_export=True,
        )
    elif target_state == STATE_DISCHARGE_800W:
        LOGGER.info("Setze Batterie auf 800 W Einspeisung.")
        result = await set_anker_home_load(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            power_w=ANKER_POWER_800_W,
            allow_export=True,
        )
    #LOGGER.info("Anker Antwort: %s", result)


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
        await refresh_anker_data(myapi)
        device = myapi.devices.get(device_sn, {})
        battery_power_set = get_battery_set_output_power(device)
        current_state = set_battery_state(battery_power_set)
        LOGGER.info("Wechsle initial zu %s", current_state)
        await apply_state(
            myapi=myapi,
            site_id=site_id,
            device_sn=device_sn,
            target_state=current_state,
        )

        while True:
            try:
                #1.  Daten holen
                power_shelly_raw = get_shelly_power(SHELLY_URL)

                await refresh_anker_data(myapi)
                device = myapi.devices.get(device_sn, {})
               # LOGGER.info("Anker Gerätedaten: %s", device)
                battery_soc = get_battery_soc(device)
                battery_power_output = get_battery_real_output_power(device)
                battery_power_set = get_battery_set_output_power(device)

                now = asyncio.get_running_loop().time()

                LOGGER.info(
                    "Sh_pwr= %.2f W | by_soc = %s | b_pwr_out = %s | b_pwr_set = %s | state = %s",
                    power_shelly_raw,
                    battery_soc,
                    battery_power_output,
                    battery_power_set,
                    current_state,
                )
                # 2. Zielzustand bestimmen
                target_state, low_power_since = choose_target_state(
                    power_shelly_raw=power_shelly_raw,
                    battery_soc=battery_soc,
                    battery_output_measured=battery_power_output,
                    battery_output_set=battery_power_set,
                    current_state=current_state,
                    low_power_since=low_power_since,
                    now=now,
                )
                # 3. Zielzustand anwenden
                if target_state != current_state and target_state is not None:
                    LOGGER.info("Wechsle von State %s zu %s", current_state, target_state)
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