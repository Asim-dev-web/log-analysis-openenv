---
title: Log Analysis Environment
emoji: 🔍
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
app_port: 8000
tags:
  - openenv
---

# Log Analysis Environment

An OpenEnv environment for investigating system incidents. The agent analyzes logs and metrics from multiple services to diagnose root causes of production failures.

## Real-World Task

This environment simulates what Site Reliability Engineers (SREs) do daily:
- Receive an alert about a system failure
- Investigate logs and metrics from various services
- Trace cascading failures across services
- Identify the root cause
- Recommend a fix

## Tasks (3 Difficulty Levels)

### Easy: Single Service Failure
- Direct failure with obvious error messages
- Single causal chain
- Examples: Database max connections, SSL certificate expired, Disk full
- Expected score: 0.7-0.9

### Medium: Cascading Failure with Red Herrings
- Multiple services affected
- Some unrelated errors present
- Requires correlating logs across services
- Examples: Redis OOM causing downstream timeouts, Memory leak, DNS failure
- Expected score: 0.5-0.7

### Hard: Intermittent Failure
- Symptoms appear in one service, cause is elsewhere
- Health checks pass despite failures
- Requires understanding system interactions
- Examples: Batch job saturating thread pool, Connection pool leak, Retry storm
- Expected score: 0.3-0.5

## Action Space

Three action types:

Fetch logs:
{"action_type": "fetch_logs", "service": "<service_name>"}

Fetch metrics:
{"action_type": "fetch_metrics", "service": "<service_name>"}

Submit diagnosis:
{"action_type": "submit_diagnosis", "root_cause": "<from list>", "severity": "<critical|high|medium|low>", "affected_services": ["<svc1>"], "recommended_action": "<from list>"}

## Observation Space

Each observation contains:
- alert_title: Description of the incident
- alert_severity: Initial severity level
- available_services: List of services to investigate
- fetched_logs: Logs collected so far
- fetched_metrics: Metrics collected so far
- steps_taken: Current step count
- max_steps: Maximum allowed steps (10)
- available_root_causes: Valid root cause options
- available_actions: Valid recommended actions
- message: Feedback from environment
- is_done: Whether episode has ended

## Reward Structure

Step Rewards:
- Fetch from affected service: +0.02
- Fetch from unaffected service: +0.01
- Invalid or duplicate action: 0.0

Diagnosis Scoring (max 0.75):
- Root cause correct: +0.30
- Severity correct: +0.15
- Affected services F1 score: up to +0.20
- Recommended action correct: +0.10

Total possible score: 0.85-0.90

## Baseline Scores

Task   | Score | Steps
-------|-------|------
Easy   | 0.81  | 4
Medium | 0.39  | 5
Hard   | 0.42  | 6

## Setup

Local Development:
pip install -r requirements.txt
uvicorn server.app:app --port 8000

Docker:
docker build -t log-analysis-env .
docker run -p 8000:8000 log-analysis-env

Test:
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d "{}"

## API Endpoints

- POST /reset - Start new episode
- POST /step - Execute action
- GET /state - Get current state
- GET /health - Health check

## Environment Variables

For inference script:
- API_BASE_URL: LLM API endpoint
- MODEL_NAME: Model identifier
- HF_TOKEN: HuggingFace API key
- ENV_BASE_URL: Environment URL (default http://localhost:8000)