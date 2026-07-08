import time, json
from kubernetes import client
from notifier import notify_slack
from grafana_annotator import push_annotation

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

SAFE_ACTIONS = {"restart", "patch_memory"}
MAX_FIXES_PER_HOUR = 5
fix_count = {"count": 0, "hour": time.time()}

def remediate(diagnosis, pod, namespace, reason):
    log_action(diagnosis, pod)
    push_annotation(pod.metadata.name, reason, diagnosis)

    if diagnosis["risk_level"] == "safe" and diagnosis["action_type"] in SAFE_ACTIONS:
        if rate_limit_ok():
            apply_fix(diagnosis, pod, namespace)
            notify_slack(f"✅ Auto-fixed {pod.metadata.name}: {diagnosis['root_cause']}")
        else:
            notify_slack(f"⚠️ Rate limit hit — manual review needed for {pod.metadata.name}")
    else:
        notify_slack(
            f"🔍 Needs human review: {pod.metadata.name}\n"
            f"Root cause: {diagnosis['root_cause']}\n"
            f"Suggested fix: {diagnosis['kubectl_command']}"
        )

def rate_limit_ok():
    if time.time() - fix_count["hour"] > 3600:
        fix_count["count"] = 0
        fix_count["hour"] = time.time()
    fix_count["count"] += 1
    return fix_count["count"] <= MAX_FIXES_PER_HOUR

def apply_fix(diagnosis, pod, namespace):
    if diagnosis["action_type"] == "restart":
        v1.delete_namespaced_pod(pod.metadata.name, namespace)
    elif diagnosis["action_type"] == "patch_memory":
        pass  # optional: implement patch_namespaced_deployment here later

def log_action(diagnosis, pod):
    with open("remediation_history.jsonl", "a") as f:
        f.write(json.dumps({"time": time.time(), "pod": pod.metadata.name, **diagnosis}) + "\n")