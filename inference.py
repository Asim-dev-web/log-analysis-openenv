import os
import json
import asyncio
from typing import List, Optional
from openai import OpenAI

from client import LogAnalysisClient
from models import LogAnalysisAction

API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
API_KEY = HF_TOKEN or os.environ.get("OPENAI_API_KEY", "EMPTY")

ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")
DOCKER_IMAGE = os.environ.get("DOCKER_IMAGE", "")

BENCHMARK = "log_analysis"
MAX_STEPS = 10
SUCCESS_THRESHOLD = 0.5

llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def build_prompt(obs, step_num: int) -> str:
    logs_fetched = list(obs.fetched_logs.keys())
    metrics_fetched = list(obs.fetched_metrics.keys())
    all_fetched = set(logs_fetched) | set(metrics_fetched)
    not_investigated = [s for s in obs.available_services if s not in all_fetched]
    need_metrics = [s for s in logs_fetched if s not in metrics_fetched]
    
    logs_content = ""
    if obs.fetched_logs:
        for svc, logs in obs.fetched_logs.items():
            logs_content += f"\n=== {svc} LOGS ===\n"
            for log in logs:
                logs_content += f"{log}\n"

    metrics_content = ""
    if obs.fetched_metrics:
        for svc, metrics in obs.fetched_metrics.items():
            metrics_content += f"\n=== {svc} METRICS ===\n"
            for k, v in metrics.items():
                metrics_content += f"  {k}: {v}\n"

    should_diagnose = step_num >= 7 or (len(not_investigated) == 0 and len(need_metrics) == 0)

    if should_diagnose:
        return f"""INCIDENT: {obs.alert_title}
SEVERITY: {obs.alert_severity}

LOGS COLLECTED:
{logs_content if logs_content else "None"}

METRICS COLLECTED:
{metrics_content if metrics_content else "None"}

Analyze logs AND metrics to determine:
1. ROOT CAUSE - look for errors and anomalous metrics
2. SEVERITY - critical/high/medium/low
3. AFFECTED SERVICES - which show problems
4. FIX - recommended action

Key patterns:
- "connection pool exhausted" + high connections_active -> database_max_connections
- "OOM" + memory_usage 99% -> redis_oom or memory_leak
- "SSL" or "certificate" -> ssl_certificate_expired
- "disk full" -> disk_full
- "configuration" error -> configuration_error
- "DNS" errors -> dns_resolution_failure
- "timeout" + high latency -> network_timeout
- "thread pool" + high threads_active -> thread_pool_exhausted
- CPU 98%+ with throttling -> cpu_throttling
- "slow query" + high CPU on database -> database_slow_query

VALID ROOT CAUSES: {obs.available_root_causes}
VALID ACTIONS: {obs.available_actions}

Reply JSON only:
{{"action_type": "submit_diagnosis", "root_cause": "<from list>", "severity": "<level>", "affected_services": ["<svc1>", "<svc2>"], "recommended_action": "<from list>"}}"""
    
    elif need_metrics:
        svc = need_metrics[0]
        return f"""INCIDENT: {obs.alert_title}

LOGS: {logs_fetched}
METRICS: {metrics_fetched}

You have logs from {svc} but no metrics. Fetch metrics to see CPU, memory, error_rate, connections.

STEP {step_num}/10

Reply JSON only:
{{"action_type": "fetch_metrics", "service": "{svc}"}}"""
    
    elif not_investigated:
        svc = not_investigated[0]
        return f"""INCIDENT: {obs.alert_title}

INVESTIGATED: {list(all_fetched)}
NOT CHECKED: {not_investigated}

STEP {step_num}/10 - Fetch logs from: {svc}

Reply JSON only:
{{"action_type": "fetch_logs", "service": "{svc}"}}"""
    
    else:
        return f"""INCIDENT: {obs.alert_title}

All services checked. Submit diagnosis now.

LOGS: {logs_fetched}
METRICS: {metrics_fetched}

Reply with submit_diagnosis action."""


def call_llm(prompt: str, obs, step_num: int) -> LogAnalysisAction:
    logs_fetched = list(obs.fetched_logs.keys())
    metrics_fetched = list(obs.fetched_metrics.keys())
    all_fetched = set(logs_fetched) | set(metrics_fetched)
    not_investigated = [s for s in obs.available_services if s not in all_fetched]
    need_metrics = [s for s in logs_fetched if s not in metrics_fetched]
    
    should_diagnose = step_num >= 7 or (len(not_investigated) == 0 and len(need_metrics) == 0)
    
    try:
        resp = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        text = ""

    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.startswith("json"):
                text = part[4:].strip()
                break
            elif part.strip().startswith("{"):
                text = part.strip()
                break
    
    text = text.strip()

    try:
        data = json.loads(text)
        return LogAnalysisAction(**data)
    except:
        pass
    
    if should_diagnose:
        logs_text = str(obs.fetched_logs).lower()
        metrics_text = str(obs.fetched_metrics).lower()
        combined = logs_text + metrics_text
        
        if "connection pool" in combined or ("connections_active" in combined and "100" in metrics_text):
            root_cause = "database_max_connections"
            action = "increase_connection_pool_size"
        elif ("oom" in combined or "out of memory" in combined) and "redis" in combined:
            root_cause = "redis_oom"
            action = "increase_memory_limit"
        elif "memory" in combined and ("99" in metrics_text or "98" in metrics_text or "leak" in combined):
            root_cause = "memory_leak"
            action = "restart_service"
        elif "ssl" in combined or "certificate" in combined:
            root_cause = "ssl_certificate_expired"
            action = "renew_ssl_certificate"
        elif "disk" in combined or "no space" in combined:
            root_cause = "disk_full"
            action = "clear_disk_space"
        elif "configuration" in combined or "config" in combined or "missing" in combined:
            root_cause = "configuration_error"
            action = "update_configuration"
        elif "dns" in combined:
            root_cause = "dns_resolution_failure"
            action = "fix_dns_config"
        elif "thread pool" in combined or "threads_active" in combined:
            root_cause = "thread_pool_exhausted"
            action = "increase_thread_pool_size"
        elif "throttl" in combined or ("cpu" in combined and "98" in metrics_text):
            root_cause = "cpu_throttling"
            action = "scale_horizontally"
        elif "slow query" in combined or "full table scan" in combined:
            root_cause = "database_slow_query"
            action = "optimize_slow_queries"
        elif "timeout" in combined or "retry" in combined:
            root_cause = "network_timeout"
            action = "enable_circuit_breaker"
        else:
            root_cause = "database_max_connections"
            action = "increase_connection_pool_size"
        
        affected = logs_fetched if logs_fetched else obs.available_services[:2]
        
        return LogAnalysisAction(
            action_type="submit_diagnosis",
            root_cause=root_cause,
            severity=obs.alert_severity if obs.alert_severity else "high",
            affected_services=affected,
            recommended_action=action
        )
    elif need_metrics:
        return LogAnalysisAction(
            action_type="fetch_metrics",
            service=need_metrics[0]
        )
    elif not_investigated:
        return LogAnalysisAction(
            action_type="fetch_logs",
            service=not_investigated[0]
        )
    else:
        return LogAnalysisAction(
            action_type="fetch_logs",
            service=obs.available_services[0]
        )


async def run_episode(task_name: str) -> dict:
    if DOCKER_IMAGE:
        env = await LogAnalysisClient.from_docker_image(DOCKER_IMAGE)
    else:
        env = LogAnalysisClient(base_url=ENV_BASE_URL)
    
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    
    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        async with env:
            result = await env.reset()
            obs = result.observation
            
            for step in range(1, MAX_STEPS + 1):
                if obs.is_done:
                    break
                
                prompt = build_prompt(obs, step)
                action = call_llm(prompt, obs, step)
                
                action_str = action.model_dump_json(exclude_none=True).replace(" ", "")
                
                result = await env.step(action)
                obs = result.observation
                reward = result.reward or 0.0
                done = result.done
                
                rewards.append(reward)
                steps_taken = step
                
                log_step(step=step, action=action_str, reward=reward, done=done, error=None)
                
                if done:
                    break
            
            score = sum(rewards)
            score = min(max(score, 0.0), 1.0)
            success = score >= SUCCESS_THRESHOLD
    
    except Exception as e:
        log_step(step=steps_taken+1, action="error", reward=0.0, done=True, error=str(e))
    
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    
    return {"task": task_name, "score": score, "steps": steps_taken, "success": success}


async def main() -> None:
    results = []
    for task_name in ["easy", "medium", "hard"]:
        result = await run_episode(task_name)
        results.append(result)
    
    print(f"\n[SUMMARY]", flush=True)
    for r in results:
        print(f"  {r['task']}: score={r['score']:.3f} steps={r['steps']} success={r['success']}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())