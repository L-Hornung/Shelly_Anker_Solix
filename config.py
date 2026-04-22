import os
from dotenv import load_dotenv

load_dotenv()

# Shelly
SHELLY_URL = os.getenv("SHELLY_URL", "http://192.168.10.45/emeter/0")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "20"))

LOW_POWER_DURATION_SECONDS = int(os.getenv("LOW_POWER_DURATION_SECONDS", "60"))

# Akku-Schutz
MIN_BATTERY_SOC_PERCENT = int(os.getenv("MIN_BATTERY_SOC_PERCENT", "15"))

# Anker Zielwerte
ANKER_POWER_150_W = int(os.getenv("ANKER_POWER_150_W", "151"))
ANKER_POWER_200_W = int(os.getenv("ANKER_POWER_200_W", "199"))
ANKER_POWER_400_W = int(os.getenv("ANKER_POWER_400_W", "399"))
ANKER_POWER_800_W = int(os.getenv("ANKER_POWER_800_W", "799"))
ANKER_IDLE_POWER_W = int(os.getenv("ANKER_IDLE_POWER_W", "0"))

# Anker Login
ANKERUSER = os.getenv("ANKERUSER")
ANKERPASSWORD = os.getenv("ANKERPASSWORD")
ANKERCOUNTRY = os.getenv("ANKERCOUNTRY", "DE")

ANKER_SITE_ID = os.getenv("ANKER_SITE_ID")
ANKER_DEVICE_SN = os.getenv("ANKER_DEVICE_SN")