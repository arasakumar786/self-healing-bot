from kubernetes import client

def get_deployment_name(pod, namespace):
    apps_v1 = client.AppsV1Api()
    try:
        owner = pod.metadata.owner_references[0]  # ReplicaSet
        rs = apps_v1.read_namespaced_replica_set(owner.name, namespace)
        rs_owner = rs.metadata.owner_references[0]  # Deployment
        return rs_owner.name
    except Exception:
        return None

def collect_context(pod, namespace):
    v1 = client.CoreV1Api()

    logs = ""
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod.metadata.name, namespace=namespace,
            previous=True, tail_lines=50
        )
    except Exception:
        logs = "No previous logs available"

    events = v1.list_namespaced_event(namespace=namespace)
    related_events = [
        e.message for e in events.items
        if e.involved_object.name == pod.metadata.name
    ]

    return {
        "pod_name": pod.metadata.name,
        "namespace": namespace,
        "logs": logs,
        "events": related_events,
        "resource_limits": pod.spec.containers[0].resources.limits,
        "image": pod.spec.containers[0].image,
        "container_name": pod.spec.containers[0].name,
        "deployment_name": get_deployment_name(pod, namespace),
    }
