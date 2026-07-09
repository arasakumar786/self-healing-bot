# Auto Heal - EKS Incident Console

## Self-Healing Kubernetes Cluster with LLM-Assisted Remediation

**Author:** Arasakumar S  
**GitHub:** arasakumar786  
**Stack:** AWS EKS, Kubernetes, Python, Claude API, FastAPI, Prometheus/Grafana, Slack

---

# 1. Overview

AutoHeal is a self-healing platform for Kubernetes that detects pod and node failures in real time, uses Claude to diagnose the root cause and suggest a fix, and routes every suggested fix through a human-in-the-loop approval workflow before anything is applied to the cluster.

It runs on a live AWS EKS cluster (`dev-cluster`, `ap-south-1`) and integrates Slack alerting, Grafana observability, and a custom authenticated web dashboard.

The project was built to demonstrate how AI can meaningfully assist DevOps operations without removing human oversight from infrastructure-changing decisions.

# 2. Problem Statement

Traditional monitoring tools (Prometheus, CloudWatch) are excellent at detecting that something is wrong, but they still require an engineer to manually investigate logs and events, form a hypothesis, and decide on a fix.

AutoHeal compresses that investigation step. The moment a failure is detected, full context (logs, Kubernetes events, resource limits, container image) is automatically collected and sent to Claude, which returns:

- Root cause
- Confidence level
- Risk classification
- Exact suggested fix

All before a human even opens their laptop.

# 3. Architecture

The system runs as a single Kubernetes Deployment with three containers sharing a pod.

### Components

- **bot** – Watches pods for `CrashLoopBackOff`, `ImagePullBackOff`, and `OOMKilled`
- **dashboard** – FastAPI web console and remediation executor
- **node-watcher** – Watches cluster nodes for `NotReady` conditions

All three containers share an in-memory volume holding incident history.

![Architecture](https://github.com/user-attachments/assets/0115ef48-4d97-4b14-b842-6a2eba03f141)

## Incident Flow

1. Watcher detects a pod or node failure via Kubernetes Watch API
2. Context collector gathers logs, events, limits, image, and deployment name
3. Claude receives the context and returns a structured diagnosis
4. Incident is stored with status **Pending**
5. Slack notification is sent
6. Engineer reviews the incident
7. Engineer approves or rejects the fix
8. Approved fixes are executed via Kubernetes API
9. Grafana receives annotations for observability

# 4. Key Design Decisions

## No Blind Auto-Remediation

Every suggested fix requires explicit human approval before any cluster change occurs.

## Node Failures Are Never Auto-Actioned

Node incidents are diagnosed and notified only.

Approving a node incident marks it as **Acknowledged** and does not trigger infrastructure actions.

Node replacement is handled by:

- EKS Managed Node Groups
- Auto Scaling Group Health Checks

## Least-Privilege RBAC

The bot ServiceAccount can:

- Get/List/Watch/Patch Pods
- Get/List/Watch/Patch Deployments
- Get/List/Watch ReplicaSets
- Read Nodes

It cannot:

- Delete resources
- Read Secrets
- Access other namespaces

## Cooldown and Rate Limiting

Per-pod cooldown windows prevent repeated Claude calls and Slack spam.

# 5. Tech Stack

| Category | Technologies |
|-----------|-------------|
| Cloud | AWS EKS, Docker Hub |
| Orchestration | Kubernetes, RBAC, Multi-container Pods |
| AI | Anthropic Claude Haiku |
| Backend | Python, FastAPI, Kubernetes Python Client |
| Authentication | JWT, bcrypt |
| Frontend | HTML, CSS, JavaScript |
| Monitoring | Prometheus, Grafana |
| Alerting | Slack Webhooks |

# 6. Feature Walkthrough

## 6.1 Detection

The bot continuously watches the target namespace.

![Detection](https://github.com/user-attachments/assets/a9569230-9c8a-4134-b76d-93d8c0b9d450)

## 6.2 Diagnosis via Claude

Full pod context is sent to Claude:

- Logs
- Events
- Resource limits
- Container image

Claude returns:

- Root Cause
- Confidence Score
- Risk Level
- Suggested Fix

## 6.3 Slack Notification

A structured Slack message includes:

- Root Cause
- Confidence
- Risk
- Suggested Fix
- Log Snippet
- Dashboard Link

![Slack](https://github.com/user-attachments/assets/1f87cf89-4ed7-4f98-8897-70e2652aea12)

## 6.4 Dashboard - Active Incidents

Authenticated engineers can review pending incidents.

![Dashboard](https://github.com/user-attachments/assets/1df1bc05-e751-4265-ab18-26e000df0ab0)

## 6.5 Expandable Incident Detail

Each incident includes:

- Root Cause
- Explanation
- Suggested Fix
- Deployment Details
- Container Image
- Resource Limits
- Events
- Logs

![Details](https://github.com/user-attachments/assets/2943c37a-5860-4abb-b196-90bc162bdb8a)

## 6.6 Approval and Verified Remediation

Approved incidents trigger real Kubernetes API actions.

The incident moves to the **Resolved** tab.

![Approval](https://github.com/user-attachments/assets/e91b89a4-cddd-4140-b2e0-26ca42dea5b9)

## 6.7 Node-Level Monitoring

Node health is monitored cluster-wide.

NotReady nodes are:

- Diagnosed
- Notified
- Reviewed

No automated infrastructure actions occur.

## 6.8 Grafana Observability

Every processed incident is pushed as a Grafana annotation, creating a timeline of AI-assisted interventions.

## 6.9 Authentication

Dashboard access is secured with:

- JWT Authentication
- bcrypt Password Hashing

![Login](https://github.com/user-attachments/assets/286b2e37-c4f0-4db8-81eb-2db1f0ab1768)

# 7. Notable Engineering Challenges

### Kubernetes Authentication Issue

A module-level Kubernetes client was instantiated before:

```python
config.load_incluster_config()
```

This caused authentication failures and was fixed by moving client initialization inside the function scope.

### Docker Image Caching

Kubernetes was pulling stale images.

Solution:

```yaml
imagePullPolicy: Always
```

and rebuilding with:

```bash
docker build --no-cache
```

### Shared Storage Problem

Containers were reading different local filesystems.

Solution:

```yaml
emptyDir:
```

shared between containers.

### EKS Node Recovery Validation

A node was intentionally degraded by stopping kubelet via SSM.

Results:

- Detected by AutoHeal
- Diagnosed by Claude
- Replaced automatically by EKS Managed Node Group

# 8. Future Improvements

- Replace `emptyDir` with PVC or DynamoDB
- Add HTTPS using ALB Ingress and ACM
- Monitor additional namespaces
- Add protected namespace deny-list
- Optional cordon-only action for node incidents

# 9. Repository

## GitHub

```bash
git clone https://github.com/arasakumar786/self-healing-bot.git
```

Repository:

https://github.com/arasakumar786/self-healing-bot
