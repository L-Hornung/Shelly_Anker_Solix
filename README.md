# Shelly + Anker Solix Automation

This project automatically controls an **Anker Solix Solarbank (E1600)** based on real-time power measurements from a **Shelly energy meter**.

The goal is to **reduce grid consumption** and **optimize self-consumption of solar energy** by dynamically adjusting battery output.

---

## 🚀 Features

* 🔌 Reads live power consumption from Shelly
* ⚡ Controls Anker Solarbank output dynamically
* 🧠 Rule-based energy management
* 🔋 Battery protection (minimum SOC limit)
* ⏱ Time-based logic (hysteresis / delay to avoid rapid switching)
* 🔄 Runs continuously on a Raspberry Pi

---

## 🧠 How It Works

The system monitors your current grid consumption and adjusts the Solarbank output accordingly:

| Condition                       | Action                              |
| ------------------------------- | ----------------------------------- |
| Grid consumption > 1000W        | Set output to 400W                  |
| Grid consumption > 200W         | Set output to 200W                  |
| Grid consumption < 100W for 60s | Turn off battery output             |
| Battery SOC < 15%               | Disable output (battery protection) |

This ensures:

* minimal grid usage
* efficient use of solar/battery energy
* protection of battery lifespan

---

## 🛠 Hardware Requirements

* Raspberry Pi Zero 2 W (recommended)
* Shelly energy meter (e.g. Shelly EM / 3EM)
* Anker Solix Solarbank (E1600)
* microSD card (16–32GB)
* 5V / 2A power supply

---

## 📦 Installation

### 1. Clone repository

```bash
git clone https://github.com/L-Hornung/Shelly_Anker_Solix
cd YOUR_REPO
```

---

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux / Mac
# OR
.venv\Scripts\activate     # Windows
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

This project uses a `.env` file for configuration.

⚠️ This file is **NOT included in the repository** for security reasons.

Create a file named:

```bash
.env
```

### Example `.env` file

```env
# Shelly
SHELLY_URL=http://192.168.10.45/emeter/0
POLL_INTERVAL_SECONDS=10

# Power thresholds
GRID_OFF_THRESHOLD_W=100
GRID_ON_200_THRESHOLD_W=200
GRID_ON_400_THRESHOLD_W=500
GRID_ON_800_THRESHOLD_W=1000
LOW_POWER_DURATION_SECONDS=60

# Battery protection
MIN_BATTERY_SOC_PERCENT=15

# Output settings
ANKER_POWER_200_W=200
ANKER_POWER_400_W=400
ANKER_IDLE_POWER_W=0

# Anker credentials
ANKERUSER=your_email@example.com
ANKERPASSWORD=your_password
ANKERCOUNTRY=DE

# Device identification (recommended)
ANKER_SITE_ID=your_site_id
ANKER_DEVICE_SN=your_device_serial
```

---

## 🔑 Important Notes about `.env`

* **Never upload this file to GitHub**
* It contains your **login credentials**
* Always keep it private
* `.gitignore` already excludes it

---

## ▶️ Run the Project

```bash
python main.py
```

---

## 🔄 Autostart (Recommended)

To run the script automatically on boot (Raspberry Pi):

```bash
crontab -e
```

Add:

```bash
@reboot /path/to/project/.venv/bin/python /path/to/project/main.py
```

---

## 📁 Project Structure

```text
.
├── main.py        # Main control loop
├── read.py        # Shelly data reader
├── write.py       # Anker control functions
├── config.py      # Configuration loader
├── requirements.txt
├── .env           # (not included)
└── .gitignore
```

---

## ⚠️ Disclaimer

* This project uses an **unofficial Anker API**
* It may break if Anker changes their backend
* Use at your own risk
* No guarantee for stability or correctness

---

## 🔮 Future Improvements

* Multi-device control (washing machine, EV charger, etc.)
* Smarter load prediction
* Web dashboard
* MQTT integration
* Battery optimization strategies

---

## 🙌 Contributions

Feel free to fork, improve, and submit pull requests.

---

## 📜 License

MIT License
