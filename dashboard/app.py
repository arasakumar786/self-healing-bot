from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
import json, os, time
from auth import create_token, verify_token
from users import ensure_default_admin, verify_user, create_user

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HISTORY_FILE = "/app/data/remediation_history.jsonl"

config.load_incluster_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

ensure_default_admin()

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    username = verify_token(token)
    if not username:
        raise HTTPException(401, "Invalid or expired token")
    return username

@app.post("/api/login")
def login(credentials: dict):
    username = credentials.get("username")
    password = credentials.get("password")
    if not verify_user(username, password):
        raise HTTPException(401, "Invalid username or password")
    return {"token": create_token(username), "username": username}

@app.post("/api/register")
def register(credentials: dict, user: str = Depends(get_current_user)):
    username = credentials.get("username")
    password = credentials.get("password")
    if create_user(username, password):
        return {"status": "created"}
    raise HTTPException(400, "Username already exists")

def read_all():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]

def write_all(records):
    with open(HISTORY_FILE, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

@app.get("/api/alerts")
def get_active_alerts(user: str = Depends(get_current_user)):
    records = read_all()
    active = [r for r in records if r.get("status") == "pending"]
    return sorted(active, key=lambda r: r["time"], reverse=True)

@app.get("/api/resolved")
def get_resolved_alerts(user: str = Depends(get_current_user)):
    records = read_all()
    resolved = [r for r in records if r.get("status") in ("applied", "rejected", "failed", "acknowledged")]
    return sorted(resolved, key=lambda r: r["time"], reverse=True)

@app.post("/api/approve/{alert_id}")
def approve_alert(alert_id: str, user: str = Depends(get_current_user)):
    records = read_all()
    target = next((r for r in records if r["id"] == alert_id), None)
    if not target:
        raise HTTPException(404, "Alert not found")
    if target.get("kind") == "node":
        target["status"] = "acknowledged"
        target["applied_time"] = time.time()
        target["approved_by"] = user
        write_all(records)
        return target
    try:
        apply_fix(target)
        target["status"] = "applied"
        target["applied_time"] = time.time()
        target["approved_by"] = user
    except Exception as e:
        target["status"] = "failed"
        target["error"] = str(e)
    write_all(records)
    return target

@app.post("/api/reject/{alert_id}")
def reject_alert(alert_id: str, user: str = Depends(get_current_user)):
    records = read_all()
    target = next((r for r in records if r["id"] == alert_id), None)
    if not target:
        raise HTTPException(404, "Alert not found")
    target["status"] = "rejected"
    target["rejected_by"] = user
    write_all(records)
    return target

def apply_fix(record):
    namespace = record["namespace"]
    deployment_name = record.get("deployment_name")
    container_name = record.get("container_name")
    action = record.get("action_type")

    if action == "restart":
        v1.delete_namespaced_pod(record["pod"], namespace)
    elif action == "patch_memory" and deployment_name and container_name:
        apps_v1.patch_namespaced_deployment(
            name=deployment_name, namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": [
                {"name": container_name, "resources": {"limits": {"memory": "128Mi"}}}
            ]}}}}
        )
    elif action == "patch_image" and deployment_name and container_name:
        apps_v1.patch_namespaced_deployment(
            name=deployment_name, namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": [
                {"name": container_name, "image": "nginx:latest"}
            ]}}}}
        )
    else:
        raise Exception(f"No automated handler available for action_type={action}")

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")
