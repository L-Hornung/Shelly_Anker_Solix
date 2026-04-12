
import requests

url = "http://192.168.10.45/emeter/0"

response = requests.get(url, timeout=5)
response.raise_for_status()

data = response.json()
print(data)
print("Power:", data["power"], "W")