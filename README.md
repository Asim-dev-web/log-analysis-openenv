---
title: Log Analysis Environment
emoji: 🔍
colorFrom: blue
colorTo: red
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# Log Analysis Environment

An AI agent environment for investigating system incidents. The agent analyzes logs and metrics from multiple services to diagnose root causes of production failures.

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
- Example: Database max connections reached
- Expected score: 0.8

### Medium: Cascading Failure with Red Herrings
- Multiple services affected
- Some unrelated errors present
- Requires correlating logs across services
- Example: Redis OOM causing downstream timeouts
- Expected score: 0.6

### Hard: Intermittent Failure
- Symptoms appear in one service, cause is elsewhere
- Health checks pass despite failures
- Requires understanding system interactions
- Example: Batch job saturating thread pool
- Expected score: 0.4

## Action Space

Three action types:

1. fetch_logs: Get logs from a service
   - Required: service

2. fetch_metrics: Get metrics from a service
   - Required: service, metric

3. submit_diagnosis: Submit final answer
   - Required: root_cause, severity, affected_services, recommended_action

## Reward Structure

Step Rewards:
- Fetch from relevant service: +0.05
- Fetch from irrelevant service: -0.02
- Invalid action: -0.05

Diagnosis Scoring (Total 1.0):
- Root cause: 40%
- Severity: 20%
- Affected services: 25% (F1 score)
- Recommended action: 15%

## Setup

Local Development:
    uv sync
    uvicorn server.app:app --reload --port 8000

Docker:
    docker build -t log-analysis-env:latest -f server/Dockerfile .
    docker run -p 8000:8000 log-analysis-env:latest