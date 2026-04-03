"""
Baseline inference script for Log Analysis Environment.

Required environment variables:
    - API_BASE_URL: The API endpoint for the LLM (default: OpenAI)
    - MODEL_NAME: The model identifier to use
    - HF_TOKEN: Your Hugging Face API key (used as LLM API key)
    - ENV_BASE_URL: Base URL of the running environment server
                    e.g. "http://localhost:8000"  (local Docker)
                    e.g. "https://as-im-log-analysis.hf.space" (HF Space)
    - DOCKER_IMAGE: (optional) Docker image name — if set, spins up a local
                    container instead of using ENV_BASE_URL.
"""

import os
import json
import asyncio
from openai import OpenAI

from client import LogAnalysisClient
from models import LogAnalysisAction

# ── LLM config ────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "gpt-4")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

# ── Environment config ─────────────────────────────────────────────────────────
ENV_BASE_URL  = os.environ.get("ENV_BASE_URL",  "http://localhost:8000")
DOCKER_IMAGE  = os.environ.get("DOCKER_IMAGE",  "")  # e.g. "log-analysis-env:latest"

MAX_STEPS          = 10
SUCCESS_THRESHOLD  = 0.5

# ── OpenAI-compatible client (works with any provider) ────────────────────────
llm = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or os.environ.get("OPENAI_API_KEY", ""),
)


# ── Prompt builder ─────────────────────────────────────────────────────────────

def observation_to_prompt(obs) -> str:
    """Convert a LogAnalysisObservation to an LLM prompt."""
    return f"""You are an expert SRE investigating a system incident.

## Alert
Title: {obs.alert_title}
Severity: {obs.alert_severity}

## Available Services
{json.dumps(obs.available_services, indent=2)}

## Logs Fetched So Far
{json.dumps(obs.fetched_logs, indent=2) if obs.fetched_logs else "None yet"}

## Metrics Fetched So Far
{json.dumps(obs.fetched_metrics, indent=2) if obs.fetched_metrics else "None yet"}

## Progress
Steps taken: {obs.steps_taken} / {obs.max_steps}

## Valid Options
Root causes: {json.dumps(obs.available_root_causes, indent=2)}
Severities:  {obs.available_severities}
Actions:     {json.dumps(obs.available_actions, indent=2)}

## Your Task
Investigate the incident by fetching logs/metrics, then submit a diagnosis.

Fetch more data:
  {{"action_type": "fetch_logs",    "service": "<name from available_services>"}}
  {{"action_type": "fetch_metrics", "service": "<name>", "metric": "<cpu_usage|memory_usage|error_rate|latency_p99|connections_active|threads_active>"}}

Submit diagnosis:
  {{"action_type": "submit_diagnosis", "root_cause": "<from available_root_causes>",
    "severity": "<from available_severities>",
    "affected_services": ["<svc1>", ...],
    "recommended_action": "<from available_actions>"}}

Respond with ONLY valid JSON, no explanation.
"""


def call_llm(prompt: str) -> LogAnalysisAction:
    """Call the LLM and parse the response into a LogAnalysisAction."""
    try:
        resp = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert SRE. Respond only with valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"[LLM ERROR] {exc}")
        text = ""

    # Strip markdown fences if present
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f"[PARSE ERROR] Could not parse: {text!r}  → defaulting to fetch_logs")
        data = {"action_type": "fetch_logs", "service": "api-gateway"}

    # Build a typed action — Pydantic validates required fields
    return LogAnalysisAction(**data)


# ── Episode runner ─────────────────────────────────────────────────────────────

async def run_episode(env: LogAnalysisClient, task_id: str) -> dict:
    """Run one episode using the OpenEnv client abstraction."""

    # ── Reset ──────────────────────────────────────────────────────────────────
    reset_result = await env.reset()          # returns StepResult
    obs          = reset_result.observation   # LogAnalysisObservation

    print(f"[START] task={task_id}  alert='{obs.alert_title[:50]}'")

    total_reward = 0.0
    steps_taken  = 0

    # ── Agent loop ─────────────────────────────────────────────────────────────
    while not obs.is_done and steps_taken < (obs.max_steps or MAX_STEPS):
        prompt = observation_to_prompt(obs)
        action = call_llm(prompt)

        # env.step() calls _step_payload → HTTP POST → _parse_result internally
        result = await env.step(action)

        obs          = result.observation
        reward       = result.reward or 0.0
        done         = result.done

        total_reward += reward
        steps_taken  += 1

        print(
            f"[STEP {steps_taken:02d}] "
            f"action={action.action_type:<18} "
            f"reward={reward:+.3f}  done={done}  "
            f"msg='{obs.message[:60]}'"
        )

        if done:
            break

    print(f"[END] task={task_id}  total_reward={total_reward:.3f}  steps={steps_taken}")
    return {"task_id": task_id, "total_reward": total_reward, "steps": steps_taken}


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 55)
    print("  Log Analysis Environment — Baseline Inference")
    print("=" * 55)
    print(f"  LLM endpoint : {API_BASE_URL}")
    print(f"  Model        : {MODEL_NAME}")
    if DOCKER_IMAGE:
        print(f"  Mode         : Docker  ({DOCKER_IMAGE})")
    else:
        print(f"  Mode         : Remote  ({ENV_BASE_URL})")
    print("=" * 55)

    results = []

    for task_id in ["episode_1", "episode_2", "episode_3"]:

        # ── Connect to environment ─────────────────────────────────────────────
        # Use from_docker_image when DOCKER_IMAGE is set (local dev / CI).
        # Otherwise connect to a running server (HF Space or local uvicorn).
        if DOCKER_IMAGE:
            env = await LogAnalysisClient.from_docker_image(DOCKER_IMAGE)
        else:
            env = LogAnalysisClient(base_url=ENV_BASE_URL)

        async with env:
            result = await run_episode(env, task_id)
        results.append(result)

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    print("=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    for r in results:
        status = "✓" if r["total_reward"] >= SUCCESS_THRESHOLD else "✗"
        print(f"  {status} {r['task_id']:<12}  score={r['total_reward']:.3f}  steps={r['steps']}")

    avg = sum(r["total_reward"] for r in results) / len(results) if results else 0.0
    print(f"\n  Average score: {avg:.3f}")


if __name__ == "__main__":
    asyncio.run(main())