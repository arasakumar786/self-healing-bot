from kubernetes import client, config, watch
from context_collector import collect_context
from llm_diagnosis import ask_llm
from remediation import remediate
import time

config.load_incluster_config()
v1 = client.CoreV1Api()

recent_failures = {}
COOLDOWN_SECONDS = 300  # 5 minutes - won't re-alert on the same pod within this window

def watch_pod_failures(namespace="self-healing-demo"):
    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_pod, namespace=namespace):
        pod = event['object']
        status = pod.status
        if status.container_statuses:
            for cs in status.container_statuses:
                waiting = cs.state.waiting
                terminated = cs.state.terminated
                if waiting and waiting.reason in ["CrashLoopBackOff", "ImagePullBackOff"]:
                    handle_failure(pod, waiting.reason, namespace)
                if terminated and terminated.reason == "OOMKilled":
                    handle_failure(pod, "OOMKilled", namespace)

def handle_failure(pod, reason, namespace):
    key = f"{pod.metadata.name}:{reason}"
    now = time.time()

    if key in recent_failures and now - recent_failures[key] < COOLDOWN_SECONDS:
        return  # already alerted recently, skip silently

    recent_failures[key] = now

    try:
        print(f"Detected {reason} on pod {pod.metadata.name}")
        context = collect_context(pod, namespace)
        diagnosis = ask_llm(context, reason)
        remediate(diagnosis, pod, namespace, reason, context)
    except Exception as e:
        print(f"Error handling failure for {pod.metadata.name}: {e}")

if __name__ == "__main__":
    watch_pod_failures()
