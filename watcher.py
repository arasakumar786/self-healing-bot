from kubernetes import client, config, watch
from context_collector import collect_context
from llm_diagnosis import ask_llm
from remediation import remediate

config.load_kube_config()   # 🔧 change to config.load_incluster_config() when running INSIDE the EKS cluster (Step 15)
v1 = client.CoreV1Api()

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
    print(f"Detected {reason} on pod {pod.metadata.name}")
    context = collect_context(pod, namespace)
    diagnosis = ask_llm(context, reason)
    remediate(diagnosis, pod, namespace, reason)

if __name__ == "__main__":
    watch_pod_failures()