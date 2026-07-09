from kubernetes import client, config, watch
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import time
import uuid
import requests

load_dotenv()

config.load_incluster_config()
v1 = client.CoreV1Api()

client_ai = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

HISTORY_FILE = "/app/data/remediation_history.jsonl"
COOLDOWN_SECONDS = 600  # 10 minutes
recent_node_alerts = {}


def watch_nodes():
    w = watch.Watch()

    for event in w.stream(v1.list_node):
        node = event["object"]

        conditions = node.status.conditions or []
        ready = next((c for c in conditions if c.type == "Ready"), None)

        if ready and ready.status != "True":
            handle_node_issue(node, ready)


def handle_node_issue(node, ready_condition):
    name = node.metadata.name
    now = time.time()

    if (
        name in recent_node_alerts
        and now - recent_node_alerts[name] < COOLDOWN_SECONDS
    ):
        return

    recent_node_alerts[name] = now

    try:
        print(f"Detected NotReady node: {name}")

        context = collect_node_context(node, ready_condition)
        diagnosis = ask_node_llm(context)

        record_node_incident(node, diagnosis, context)

    except Exception as e:
        print(f"Error handling node issue for {name}: {e}")


def collect_node_context(node, ready_condition):
    conditions = node.status.conditions or []

    return {
        "node_name": node.metadata.name,
        "ready_status": ready_condition.status,
        "ready_reason": ready_condition.reason,
        "ready_message": ready_condition.message,
        "instance_type": node.metadata.labels.get(
            "node.kubernetes.io/instance-type",
            "unknown"
        ),
        "zone": node.metadata.labels.get(
            "topology.kubernetes.io/zone",
            "unknown"
        ),
        "capacity": node.status.capacity,
        "allocatable": node.status.allocatable,
        "conditions": [
            {
                "type": c.type,
                "status": c.status,
                "reason": c.reason,
                "message": c.message
            }
            for c in conditions
        ]
    }


def ask_node_llm(context):
    prompt = f"""
You are a Kubernetes SRE assistant.

A Kubernetes node has entered NotReady state.

Node Context:
{json.dumps(context, indent=2)}

Respond ONLY with valid JSON.

{{
  "root_cause": "short explanation",
  "confidence": "high|medium|low",
  "risk_level": "needs_review",
  "action_type": "manual",
  "kubectl_command": "diagnostic command or null",
  "explanation": "recommended investigation"
}}
"""

    response = client_ai.chat.completions.create(
        model=os.getenv("MODEL", "anthropic/claude-sonnet-4"),
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=500
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)


def record_node_incident(node, diagnosis, context):
    record = {
        "id": str(uuid.uuid4())[:8],
        "time": time.time(),
        "kind": "node",
        "node": node.metadata.name,
        "reason": context["ready_reason"] or "NotReady",
        "status": "pending",
        "full_context": context,
        **diagnosis
    }

    os.makedirs("/app/data", exist_ok=True)

    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    notify_slack_node(record, context)


def notify_slack_node(record, context):
    webhook = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook:
        print("SLACK_WEBHOOK_URL not configured")
        return

    message = {
        "text": (
            f"⚠️ *Node NotReady Alert*\n"
            f"*Node:* `{context['node_name']}`\n"
            f"*Instance Type:* `{context['instance_type']}`\n"
            f"*Zone:* `{context['zone']}`\n"
            f"*Reason:* `{context['ready_reason']}`\n"
            f"*Root Cause:* {record['root_cause']}\n"
            f"*Confidence:* {record['confidence']}\n"
            f"*Investigation:* {record['explanation']}\n"
            f"*Command:* `{record['kubectl_command']}`\n"
            f"*Incident ID:* `{record['id']}`"
        )
    }

    try:
        requests.post(webhook, json=message, timeout=10)
    except Exception as e:
        print(f"Slack notification failed: {e}")


if __name__ == "__main__":
    print("Watching Kubernetes nodes for NotReady state...")

    while True:
        try:
            watch_nodes()
        except Exception as e:
            print(f"Watcher crashed: {e}")
            time.sleep(5)
