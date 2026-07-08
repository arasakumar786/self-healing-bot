import os, requests, time
from dotenv import load_dotenv

load_dotenv()
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY")

def push_annotation(pod_name, reason, diagnosis):
    text = f"{pod_name}: {reason} -> {diagnosis['action_type']} ({diagnosis['risk_level']})"
    payload = {
        "time": int(time.time() * 1000),
        "tags": ["self-healing-bot", diagnosis["risk_level"]],
        "text": text
    }
    try:
        requests.post(
            f"{GRAFANA_URL}/api/annotations",
            json=payload,
            headers={"Authorization": f"Bearer {GRAFANA_API_KEY}"},
            timeout=5
        )
    except Exception as e:
        print(f"Grafana annotation failed: {e}")