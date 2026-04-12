import logging
from typing import Any

from aiohttp import ClientSession
from api import api


LOGGER = logging.getLogger(__name__)


async def create_anker_api(user: str, password: str, country: str, session: ClientSession) -> Any:
    if not user or not password:
        raise RuntimeError("ANKERUSER oder ANKERPASSWORD fehlt.")

    return api.AnkerSolixApi(
        user,
        password,
        country,
        session,
        LOGGER,
    )


async def refresh_anker_data(myapi: Any) -> None:
    await myapi.update_sites()
    await myapi.update_device_details()


def find_solarbank_device(myapi: Any, configured_site_id: str | None, configured_device_sn: str | None) -> tuple[str, str]:
    if configured_site_id and configured_device_sn:
        return configured_site_id, configured_device_sn

    for device_sn, device in myapi.devices.items():
        text = str(device).lower()
        if "solarbank" in text:
            site_id = device.get("site_id")
            if site_id:
                return str(site_id), str(device_sn)

    raise RuntimeError("Keine Solarbank gefunden.")


async def set_anker_home_load(
    myapi: Any,
    site_id: str,
    device_sn: str,
    power_w: int,
    allow_export: bool,
) -> Any:
    attempts = [
        {
            "siteId": site_id,
            "deviceSn": device_sn,
            "preset": power_w,
            "export": allow_export,
        },
        {
            "site_id": site_id,
            "device_sn": device_sn,
            "preset": power_w,
            "export": allow_export,
        },
        {
            "siteId": site_id,
            "deviceSn": device_sn,
            "preset_system_output_power": power_w,
            "preset_allow_export": allow_export,
        },
        {
            "site_id": site_id,
            "device_sn": device_sn,
            "preset_system_output_power": power_w,
            "preset_allow_export": allow_export,
        },
    ]

    last_error = None

    for kwargs in attempts:
        try:
            LOGGER.info("Sende an Anker: %s", kwargs)
            return await myapi.set_home_load(**kwargs)
        except TypeError as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Keine passende set_home_load-Signatur gefunden: {last_error}")