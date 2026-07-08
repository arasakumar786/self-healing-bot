import requests, os
from dotenv import load_dotenv

load_dotenv()
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")

def notify_slack(message):
    requests.post(SLACK_WEBHOOK, json={"text": message})