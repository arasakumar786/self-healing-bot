import time, json, uuid
from notifier import notify_slack
from grafana_annotator import push_annotation

HISTORY_FILE = "/app/data/remediation_history.jsonl"
DASHBOARD_URL = "http://a8ff2408606644d6088f6d594d2ed09e-1995804674.ap-south-1.elb.amazonaws.com"  # 🔧 CHANGE to your real dashboard URL

def remediate(diagnosis, pod, namespace, reason, context):
    record = {
        "id": str(uuid.uuid4())[:8],
        "time": time.time(),
        "pod": pod.metadata.name,
        "namespace": namespace,
        "deployment_name": context.get("deployment_name"),
        "container_name": context.get("container_name"),
        "reason": reason,
        "status": "pending",
        **diagnosis,
        "full_context": context
    }
    log_action(record)
    push_annotation(pod.metadata.name, reason, diagnosis)
    notify_slack_detailed(record, context)

def log_action(record):
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

def notify_slack_detailed(record, context):
    logs_snippet = (context.get("logs") or "")[:300]
    message = (
        f":rotating_light: *New Incident Detected*\n"
        f"*Pod:* `{record['pod']}`\n"
        f"*Namespace:* `{record['namespace']}`\n"
        f"*Failure Reason:* `{record['reason']}`\n"
        f"*Root Cause:* {record['root_cause']}\n"
        f"*Confidence:* {record['confidence']} | *Risk:* {record['risk_level']}\n"
        f"*Suggested Fix:* `{record['kubectl_command']}`\n"
        f"*Why this fix:* {record['explanation']}\n"
        f"*Recent logs:*\n```{logs_snippet}```\n"
        f"👉 Review and approve here: {DASHBOARD_URL}\n"
        f"_Incident ID: {record['id']}_"
    )
    notify_slack(message)
