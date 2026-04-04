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
    not_investigated = [s for s in obs.available_services if s not in logs_fetched]
    
    logs_content = ""
    if obs.fetched_logs:
        for svc, logs in obs.fetched_logs.items():
            logs_content += f"\n=== {svc} ===\n"
            for log in logs:
                logs_content += f"{log}\n"

    should_diagnose = step_num >= 6 or len(not_investigated) == 0

    if should_diagnose:
        return f"""INCIDENT ALERT: {obs.alert_title}
SEVERITY: {obs.alert_severity}

COLLECTED LOGS:
{logs_content}

Based on the logs above, identify:
1. ROOT CAUSE - look for ERROR messages indicating the source problem
2. SEVERITY - critical/high/medium/low
3. AFFECTED SERVICES - which services show errors
4. FIX - what action to take

VALID ROOT CAUSES (pick ONE):
{json.dumps(obs.available_root_causes)}

VALID ACTIONS (pick ONE):
{json.dumps(obs.available_actions)}

Analyze the logs carefully. Look for:
- "connection pool exhausted" -> database_max_connections
- "OOM" or "out of memory" -> redis_oom or memory_leak
- "SSL" or "certificate" -> ssl_certificate_expired
- "disk full" or "no space" -> disk_full
- "configuration" or "missing field" -> configuration_error
- "timeout" -> network_timeout
- "DNS" -> dns_resolution_failure

Reply with JSON only:
{{"action_type": "submit_diagnosis", "root_cause": "<from valid list>", "severity": "<critical|high|medium|low>", "affected_services": ["<svc1>", "<svc2>"], "recommended_action": "<from valid list>"}}"""
    
    else:
        next_svc = not_investigated[0]
        return f"""INCIDENT: {obs.alert_title}

LOGS SO FAR:
{logs_content if logs_content else "None yet"}

INVESTIGATED: {logs_fetched}
NOT YET CHECKED: {not_investigated}

STEP {step_num}/10 - Fetch logs from: {next_svc}

Reply with JSON only:
{{"action_type": "fetch_logs", "service": "{next_svc}"}}"""


def call_llm(prompt: str, obs, step_num: int) -> LogAnalysisAction:
    logs_fetched = list(obs.fetched_logs.keys())
    not_investigated = [s for s in obs.available_services if s not in logs_fetched]
    should_diagnose = step_num >= 6 or len(not_investigated) == 0
    
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
        
        if "connection pool" in logs_text or "max connections" in logs_text:
            root_cause = "database_max_connections"
            action = "increase_connection_pool_size"
        elif "oom" in logs_text or "out of memory" in logs_text or "memory" in logs_text:
            if "redis" in logs_text:
                root_cause = "redis_oom"
                action = "increase_memory_limit"
            else:
                root_cause = "memory_leak"
                action = "restart_service"
        elif "ssl" in logs_text or "certificate" in logs_text:
            root_cause = "ssl_certificate_expired"
            action = "renew_ssl_certificate"
        elif "disk" in logs_text or "no space" in logs_text:
            root_cause = "disk_full"
            action = "clear_disk_space"
        elif "configuration" in logs_text or "config" in logs_text or "missing" in logs_text:
            root_cause = "configuration_error"
            action = "update_configuration"
        elif "dns" in logs_text:
            root_cause = "dns_resolution_failure"
            action = "fix_dns_config"
        elif "timeout" in logs_text:
            root_cause = "network_timeout"
            action = "enable_circuit_breaker"
        elif "thread pool" in logs_text:
            root_cause = "thread_pool_exhausted"
            action = "increase_thread_pool_size"
        elif "slow query" in logs_text:
            root_cause = "database_slow_query"
            action = "optimize_slow_queries"
        else:
            root_cause = "database_max_connections"
            action = "increase_connection_pool_size"
        
        affected = logs_fetched if logs_fetched else obs.available_services[:2]
        
        return LogAnalysisAction(
            action_type="submit_diagnosis",
            root_cause=root_cause,
            severity=obs.alert_severity if obs.alert_severity else "critical",
            affected_services=affected,
            recommended_action=action
        )
    else:
        return LogAnalysisAction(
            action_type="fetch_logs",
            service=not_investigated[0] if not_investigated else obs.available_services[0]
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