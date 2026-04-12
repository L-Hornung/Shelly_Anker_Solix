import requests
from typing import Any


def get_shelly_data(url: str) -> dict:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


def get_shelly_power(url: str) -> float:
    data = get_shelly_data(url)

    if "power" not in data:
        raise ValueError(f"Kein 'power' Feld in Shelly-Antwort: {data}")

    return float(data["power"])


def get_battery_soc(device: dict[str, Any]) -> float | None:
    candidates = [
        "battery_soc",
        "battery_percentage",
        "battery_level",
        "soc",
        "bat_charge_power",
    ]

    for key in candidates:
        value = device.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    # Manche Libraries legen den Wert verschachtelt ab
    battery = device.get("battery")
    if isinstance(battery, dict):
        for key in ["soc", "percentage", "level"]:
            value = battery.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue

    return None