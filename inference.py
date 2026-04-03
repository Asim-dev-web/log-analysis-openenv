"""
Baseline inference script for Log Analysis Environment.

Required environment variables:
    - API_BASE_URL: The API endpoint for the LLM
    - MODEL_NAME: The model identifier to use
    - HF_TOKEN: Your Hugging Face API key
"""

import os
import json
import asyncio
import websockets
from openai import OpenAI

# Get config from environment variables
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Environment WebSocket URL
ENV_WS_URL = os.environ.get("ENV_WS_URL", "wss://as-im-log-analysis.hf.space/ws")

# Initialize OpenAI client
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN or os.environ.get("OPENAI_API_KEY", ""),
)


def observation_to_prompt(obs: dict) -> str:
    """Convert observation to a prompt for the LLM."""
    
    prompt = f"""You are an expert SRE investigating a system incident.

## Alert
Title: {obs.get('alert_title', 'N/A')}
Severity: {obs.get('alert_severity', 'N/A')}

## Available Services to Investigate
{json.dumps(obs.get('available_services', []), indent=2)}

## Logs Fetched So Far
{json.dumps(obs.get('fetched_logs', {}), indent=2) if obs.get('fetched_logs') else "None yet"}

## Metrics Fetched So Far
{json.dumps(obs.get('fetched_metrics', {}), indent=2) if obs.get('fetched_metrics') else "None yet"}

## Progress
Steps taken: {obs.get('steps_taken', 0)} / {obs.get('max_steps', 10)}

## Valid Options

Root causes (choose one for diagnosis):
{json.dumps(obs.get('available_root_causes', []), indent=2)}

Severities: {obs.get('available_severities', [])}

Recommended actions:
{json.dumps(obs.get('available_actions', []), indent=2)}

## Your Task

Analyze the logs and metrics to diagnose the incident.

If you need more information, fetch logs or metrics:
{{"action_type": "fetch_logs", "service": "<service_name>"}}
{{"action_type": "fetch_metrics", "service": "<service_name>"}}

When ready to diagnose:
{{"action_type": "submit_diagnosis", "root_cause": "<cause>", "severity": "<level>", "affected_services": ["<svc1>", "<svc2>"], "recommended_action": "<action>"}}

Respond with ONLY valid JSON, no explanation.
"""
    return prompt


def parse_llm_response(response_text: str) -> dict:
    """Parse LLM response into action dict."""
    text = response_text.strip()
    
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
        return {"action_type": "fetch_logs", "service": "api-gateway"}


async def run_episode(ws_url: str, task_id: str) -> dict:
    """Run a single episode via WebSocket."""
    
    async with websockets.connect(ws_url) as ws:
        # Reset
        await ws.send(json.dumps({"type": "reset", "data": {}}))
        response = await ws.recv()
        data = json.loads(response)
        
        obs = data.get("data", {}).get("observation", {})
        scenario_id = obs.get("alert_title", "unknown")[:30]
        
        print(f"[START] task={task_id} scenario={scenario_id}")
        
        total_reward = 0.0
        step_count = 0
        done = False
        
        while not done and step_count < obs.get("max_steps", 10):
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
            
            # Send action
            await ws.send(json.dumps({"type": "step", "data": action_dict}))
            response = await ws.recv()
            data = json.loads(response)
            
            obs = data.get("data", {}).get("observation", {})
            reward = data.get("data", {}).get("reward", 0)
            done = data.get("data", {}).get("done", False)
            
            total_reward += reward
            step_count += 1
            
            action_type = action_dict.get("action_type", "unknown")
            print(f"[STEP] step={step_count} action={action_type} reward={reward:.3f} done={done}")
        
        print(f"[END] task={task_id} total_reward={total_reward:.3f} steps={step_count}")
        
        return {
            "task_id": task_id,
            "total_reward": total_reward,
            "steps": step_count,
        }


async def main_async():
    """Run inference on all tasks."""
    
    print("=" * 50)
    print("Log Analysis Environment - Baseline Inference")
    print("=" * 50)
    print(f"API_BASE_URL: {API_BASE_URL}")
    print(f"MODEL_NAME: {MODEL_NAME}")
    print(f"ENV_WS_URL: {ENV_WS_URL}")
    print("=" * 50)
    
    results = []
    
    # Run 3 episodes (environment randomly picks scenarios)
    for i, task_id in enumerate(["episode_1", "episode_2", "episode_3"]):
        result = await run_episode(ENV_WS_URL, task_id)
        results.append(result)
    
    # Summary
    print("")
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for r in results:
        print(f"Task: {r['task_id']:12} | Score: {r['total_reward']:.3f} | Steps: {r['steps']}")
    
    avg_score = sum(r["total_reward"] for r in results) / len(results) if results else 0
    print(f"\nAverage Score: {avg_score:.3f}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()