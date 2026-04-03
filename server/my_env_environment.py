from uuid import uuid4
from typing import Dict, List, Any
import random
import traceback

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import LogAnalysisAction, LogAnalysisObservation
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import LogAnalysisAction, LogAnalysisObservation

try:
    from .scenarios import ALL_SCENARIOS, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS
except ImportError:
    from scenarios import ALL_SCENARIOS, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS


class LogAnalysisEnvironment(Environment):
    """Log Analysis Environment for incident investigation."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = False
    MAX_STEPS: int = 10

    # ── Class-level state ──────────────────────────────────────────────────────
    # The framework may instantiate a fresh object per request, so we store
    # all mutable episode state at the class level so it survives across calls.
    _current_scenario = None
    _fetched_logs: Dict = {}
    _fetched_metrics: Dict = {}
    _is_done: bool = False
    _last_reward: float = 0.0
    _diagnosis_submitted: bool = False
    _step_count: int = 0

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)

    # ── Reset ──────────────────────────────────────────────────────────────────

    def reset(self) -> LogAnalysisObservation:
        """Start a new investigation episode."""
        try:
            LogAnalysisEnvironment._fetched_logs = {}
            LogAnalysisEnvironment._fetched_metrics = {}
            LogAnalysisEnvironment._is_done = False
            LogAnalysisEnvironment._last_reward = 0.0
            LogAnalysisEnvironment._diagnosis_submitted = False
            LogAnalysisEnvironment._step_count = 0
            LogAnalysisEnvironment._current_scenario = random.choice(ALL_SCENARIOS)

            self._state = State(episode_id=str(uuid4()), step_count=0)

            return LogAnalysisObservation(
                alert_title=LogAnalysisEnvironment._current_scenario["alert"]["title"],
                alert_severity=LogAnalysisEnvironment._current_scenario["alert"]["severity"],
                available_services=LogAnalysisEnvironment._current_scenario["services"],
                fetched_logs={},
                fetched_metrics={},
                steps_taken=0,
                max_steps=self.MAX_STEPS,
                available_root_causes=ALL_ROOT_CAUSES,
                available_severities=["critical", "high", "medium", "low"],
                available_actions=ALL_RECOMMENDED_ACTIONS,
                is_done=False,
                message="Investigation started. Analyze the alert and fetch logs/metrics to diagnose the issue.",
                done=False,
                reward=0.0,
            )
        except Exception as e:
            print(f"ERROR in reset(): {e}")
            traceback.print_exc()
            raise e

    # ── Step ───────────────────────────────────────────────────────────────────

    def step(self, action: LogAnalysisAction) -> LogAnalysisObservation:
        """Process agent's action and return new observation."""
        try:
            print(f"DEBUG step() action={action.action_type} service={action.service}")

            LogAnalysisEnvironment._step_count += 1
            self._state.step_count = LogAnalysisEnvironment._step_count
            reward = 0.0
            message = ""

            if LogAnalysisEnvironment._is_done:
                return self._make_observation("Episode already ended.", reward)

            if action.action_type == "fetch_logs":
                reward, message = self._handle_fetch_logs(action)
            elif action.action_type == "fetch_metrics":
                reward, message = self._handle_fetch_metrics(action)
            elif action.action_type == "submit_diagnosis":
                reward, message = self._handle_submit_diagnosis(action)
            else:
                message = f"Invalid action_type: {action.action_type}"
                reward = -0.1

            if LogAnalysisEnvironment._step_count >= self.MAX_STEPS and not LogAnalysisEnvironment._is_done:
                LogAnalysisEnvironment._is_done = True
                message += " Max steps reached. Episode ended."

            LogAnalysisEnvironment._last_reward = reward
            return self._make_observation(message, reward)

        except Exception as e:
            print(f"ERROR in step(): {e}")
            traceback.print_exc()
            raise e

    # ── Action handlers ────────────────────────────────────────────────────────

    def _handle_fetch_logs(self, action: LogAnalysisAction) -> tuple:
        service = action.service
        if not service:
            return -0.05, "Error: service field is required for fetch_logs"
        if service not in LogAnalysisEnvironment._current_scenario["services"]:
            return -0.05, f"Error: Unknown service '{service}'"
        if service in LogAnalysisEnvironment._fetched_logs:
            return -0.02, f"Logs for '{service}' already fetched"

        logs = LogAnalysisEnvironment._current_scenario["logs"].get(service, [])
        LogAnalysisEnvironment._fetched_logs[service] = logs

        relevant = LogAnalysisEnvironment._current_scenario["ground_truth"]["affected_services"]
        if service in relevant:
            return 0.05, f"Fetched {len(logs)} log lines from '{service}'"
        return -0.02, f"Fetched {len(logs)} log lines from '{service}'"

    def _handle_fetch_metrics(self, action: LogAnalysisAction) -> tuple:
        service = action.service
        if not service:
            return -0.05, "Error: service field is required for fetch_metrics"
        if service not in LogAnalysisEnvironment._current_scenario["services"]:
            return -0.05, f"Error: Unknown service '{service}'"
        if service in LogAnalysisEnvironment._fetched_metrics:
            return -0.02, f"Metrics for '{service}' already fetched"

        metrics = LogAnalysisEnvironment._current_scenario["metrics"].get(service, {})
        LogAnalysisEnvironment._fetched_metrics[service] = metrics

        relevant = LogAnalysisEnvironment._current_scenario["ground_truth"]["affected_services"]
        if service in relevant:
            return 0.03, f"Fetched metrics from '{service}'"
        return -0.02, f"Fetched metrics from '{service}'"

    def _handle_submit_diagnosis(self, action: LogAnalysisAction) -> tuple:
        LogAnalysisEnvironment._is_done = True
        LogAnalysisEnvironment._diagnosis_submitted = True

        ground_truth = LogAnalysisEnvironment._current_scenario["ground_truth"]
        score = 0.0
        feedback = []

        if action.root_cause == ground_truth["root_cause"]:
            score += 0.4
            feedback.append("Root cause: CORRECT")
        else:
            feedback.append(f"Root cause: WRONG (expected {ground_truth['root_cause']})")

        if action.severity == ground_truth["severity"]:
            score += 0.2
            feedback.append("Severity: CORRECT")
        else:
            feedback.append(f"Severity: WRONG (expected {ground_truth['severity']})")

        if action.affected_services:
            predicted = set(action.affected_services)
            actual = set(ground_truth["affected_services"])
            if predicted and actual:
                precision = len(predicted & actual) / len(predicted)
                recall = len(predicted & actual) / len(actual)
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                score += 0.25 * f1
                feedback.append(f"Affected services: {f1:.0%} match")
            else:
                feedback.append("Affected services: no match")
        else:
            feedback.append("Affected services: not provided")

        if action.recommended_action == ground_truth["recommended_action"]:
            score += 0.15
            feedback.append("Recommended action: CORRECT")
        else:
            feedback.append(f"Recommended action: WRONG (expected {ground_truth['recommended_action']})")

        message = f"Investigation complete! Score: {score:.2f}. " + " | ".join(feedback)
        return score, message

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _make_observation(self, message: str, reward: float) -> LogAnalysisObservation:
        scenario = LogAnalysisEnvironment._current_scenario
        return LogAnalysisObservation(
            alert_title=scenario["alert"]["title"],
            alert_severity=scenario["alert"]["severity"],
            available_services=scenario["services"],
            fetched_logs=LogAnalysisEnvironment._fetched_logs,
            fetched_metrics=LogAnalysisEnvironment._fetched_metrics,
            steps_taken=LogAnalysisEnvironment._step_count,
            max_steps=self.MAX_STEPS,
            available_root_causes=ALL_ROOT_CAUSES,
            available_severities=["critical", "high", "medium", "low"],
            available_actions=ALL_RECOMMENDED_ACTIONS,
            is_done=LogAnalysisEnvironment._is_done,
            message=message,
            done=LogAnalysisEnvironment._is_done,
            reward=reward,
        )

    @property
    def state(self) -> State:
        return self._state