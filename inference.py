"""
Baseline inference script for Log Analysis Environment.

This script runs an LLM agent against the environment and produces
structured logs for evaluation.

Required environment variables:
    - API_BASE_URL: The API endpoint for the LLM
    - MODEL_NAME: The model identifier to use
    - HF_TOKEN: Your Hugging Face API key
"""

import os
import json
from openai import OpenAI

# Import environment and models
from server.my_env_environment import LogAnalysisEnvironment
from server.scenarios import SCENARIOS_BY_DIFFICULTY
from models import LogAnalysisAction

# Get config from environment variables
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Initialize OpenAI client
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or os.environ.get("OPENAI_API_KEY", ""),
)


def observation_to_prompt(obs) -> str:
    """Convert observation to a prompt for the LLM."""
    
    prompt = f"""You are an SRE investigating a system incident.

## Alert
Title: {obs.alert_title}
Severity: {obs.alert_severity}

## Available Services to Investigate
{json.dumps(obs.available_services, indent=2)}

## Logs Fetched So Far
{json.dumps(obs.fetched_logs, indent=2) if obs.fetched_logs else "None yet"}

## Metrics Fetched So Far
{json.dumps(obs.fetched_metrics, indent=2) if obs.fetched_metrics else "None yet"}

## Progress
Steps taken: {obs.steps_taken} / {obs.max_steps}

## Valid Options

Root causes (choose one for diagnosis):
{json.dumps(obs.available_root_causes, indent=2)}

Severities: {obs.available_severities}

Recommended actions:
{json.dumps(obs.available_actions, indent=2)}

## Your Task

Decide your next action. You can either:

1. Fetch more logs:
   {{"action_type": "fetch_logs", "service": "<service_name>"}}

2. Fetch metrics:
   {{"action_type": "fetch_metrics", "service": "<service_name>"}}

3. Submit diagnosis (when ready):
   {{"action_type": "submit_diagnosis", "root_cause": "<cause>", "severity": "<level>", "affected_services": ["<svc1>", "<svc2>"], "recommended_action": "<action>"}}

Respond with ONLY valid JSON, no explanation.
"""
    return prompt


def parse_llm_response(response_text: str) -> dict:
    """Parse LLM response into action dict."""
    
    # Clean up response
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If parsing fails, return a default fetch action
        return {"action_type": "fetch_logs", "service": "api-gateway"}


def run_episode(env: LogAnalysisEnvironment, task_id: str) -> dict:
    """Run a single episode and return results."""
    
    # Reset environment
    obs = env.reset()
    
    print(f"[START] task={task_id} scenario={env._current_scenario['id']}")
    
    total_reward = 0.0
    step_count = 0
    
    while not obs.is_done and step_count < obs.max_steps:
        # Get prompt for LLM
        prompt = observation_to_prompt(obs)
        
        # Call LLM
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are an expert SRE. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=500,
            )
            llm_response = response.choices[0].message.content
        except Exception as e:
            print(f"[STEP] step={step_count} error='{str(e)}'")
            break
        
        # Parse response
        action_dict = parse_llm_response(llm_response)
        
        # Create action
        try:
            action = LogAnalysisAction(
                action_type=action_dict.get("action_type", "fetch_logs"),
                service=action_dict.get("service"),
                metric=action_dict.get("metric"),
                root_cause=action_dict.get("root_cause"),
                severity=action_dict.get("severity"),
                affected_services=action_dict.get("affected_services"),
                recommended_action=action_dict.get("recommended_action"),
            )
        except Exception as e:
            print(f"[STEP] step={step_count} error='Invalid action: {str(e)}'")
            action = LogAnalysisAction(action_type="fetch_logs", service=obs.available_services[0])
        
        # Take step
        obs = env.step(action)
        total_reward += obs.reward
        step_count += 1
        
        print(f"[STEP] step={step_count} action={action.action_type} reward={obs.reward:.3f} done={obs.is_done}")
    
    print(f"[END] task={task_id} total_reward={total_reward:.3f} steps={step_count}")
    
    return {
        "task_id": task_id,
        "scenario_id": env._current_scenario["id"],
        "total_reward": total_reward,
        "steps": step_count,
    }


def main():
    """Run inference on all tasks."""
    
    print("=" * 50)
    print("Log Analysis Environment - Baseline Inference")
    print("=" * 50)
    print(f"API_BASE_URL: {API_BASE_URL}")
    print(f"MODEL_NAME: {MODEL_NAME}")
    print("=" * 50)
    
    env = LogAnalysisEnvironment()
    results = []
    
    # Run one episode per difficulty
    for difficulty in ["easy", "medium", "hard"]:
        scenarios = SCENARIOS_BY_DIFFICULTY.get(difficulty, [])
        
        if not scenarios:
            print(f"No scenarios for difficulty: {difficulty}")
            continue
        
        # Force specific scenario for reproducibility
        env._current_scenario = scenarios[0]
        
        result = run_episode(env, task_id=difficulty)
        results.append(result)
    
    # Summary
    print("")
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for r in results:
        print(f"Task: {r['task_id']:8} | Scenario: {r['scenario_id']:25} | Score: {r['total_reward']:.3f} | Steps: {r['steps']}")
    
    avg_score = sum(r["total_reward"] for r in results) / len(results) if results else 0
    print(f"\nAverage Score: {avg_score:.3f}")


if __name__ == "__main__":
    main()