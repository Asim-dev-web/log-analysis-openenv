from uuid import uuid4
from typing import Dict, List, Any
import random

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import LogAnalysisAction, LogAnalysisObservation
except ImportError:
    from models import LogAnalysisAction, LogAnalysisObservation

try:
    from .scenarios import ALL_SCENARIOS, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS
except ImportError:
    from scenarios import ALL_SCENARIOS, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS


class LogAnalysisEnvironment(Environment):
    """Log Analysis Environment for incident investigation."""
    
    SUPPORTS_CONCURRENT_SESSIONS: bool = True
    MAX_STEPS: int = 10
    
    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_scenario = None
        self._fetched_logs: Dict[str, List[str]] = {}
        self._fetched_metrics: Dict[str, Dict[str, Any]] = {}
        self._is_done = False
        self._last_reward = 0.0
        self._diagnosis_submitted = False

    def reset(self) -> LogAnalysisObservation:
        """Start a new investigation episode."""
        # Reset state
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._fetched_logs = {}
        self._fetched_metrics = {}
        self._is_done = False
        self._last_reward = 0.0
        self._diagnosis_submitted = False
        
        # Pick a random scenario
        self._current_scenario = random.choice(ALL_SCENARIOS)
        
        # Return initial observation
        return LogAnalysisObservation(
            alert_title=self._current_scenario["alert"]["title"],
            alert_severity=self._current_scenario["alert"]["severity"],
            available_services=self._current_scenario["services"],
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

    def step(self, action: LogAnalysisAction) -> LogAnalysisObservation:
        """Process agent's action and return new observation."""
        self._state.step_count += 1
        reward = 0.0
        message = ""
        
        # Check if already done
        if self._is_done:
            return self._make_observation("Episode already ended.", reward)
        
        # Handle different action types
        if action.action_type == "fetch_logs":
            reward, message = self._handle_fetch_logs(action)
            
        elif action.action_type == "fetch_metrics":
            reward, message = self._handle_fetch_metrics(action)
            
        elif action.action_type == "submit_diagnosis":
            reward, message = self._handle_submit_diagnosis(action)
            
        else:
            message = f"Invalid action_type: {action.action_type}"
            reward = -0.1
        
        # Check if max steps reached
        if self._state.step_count >= self.MAX_STEPS and not self._is_done:
            self._is_done = True
            message += " Max steps reached. Episode ended."
        
        self._last_reward = reward
        return self._make_observation(message, reward)

    def _handle_fetch_logs(self, action: LogAnalysisAction) -> tuple:
        """Handle fetch_logs action."""
        service = action.service
        
        # Validate service
        if not service:
            return -0.05, "Error: service field is required for fetch_logs"
        
        if service not in self._current_scenario["services"]:
            return -0.05, f"Error: Unknown service '{service}'"
        
        # Check if already fetched
        if service in self._fetched_logs:
            return -0.02, f"Logs for '{service}' already fetched"
        
        # Fetch logs
        logs = self._current_scenario["logs"].get(service, [])
        self._fetched_logs[service] = logs
        
        # Small reward for fetching relevant service
        relevant_services = self._current_scenario["ground_truth"]["affected_services"]
        if service in relevant_services:
            return 0.05, f"Fetched {len(logs)} log lines from '{service}'"
        else:
            return -0.02, f"Fetched {len(logs)} log lines from '{service}'"

    def _handle_fetch_metrics(self, action: LogAnalysisAction) -> tuple:
        """Handle fetch_metrics action."""
        service = action.service
        
        # Validate
        if not service:
            return -0.05, "Error: service field is required for fetch_metrics"
        
        if service not in self._current_scenario["services"]:
            return -0.05, f"Error: Unknown service '{service}'"
        
        # Check if already fetched
        if service in self._fetched_metrics:
            return -0.02, f"Metrics for '{service}' already fetched"
        
        # Fetch metrics
        metrics = self._current_scenario["metrics"].get(service, {})
        self._fetched_metrics[service] = metrics
        
        # Small reward for relevant service
        relevant_services = self._current_scenario["ground_truth"]["affected_services"]
        if service in relevant_services:
            return 0.03, f"Fetched metrics from '{service}'"
        else:
            return -0.02, f"Fetched metrics from '{service}'"

    def _handle_submit_diagnosis(self, action: LogAnalysisAction) -> tuple:
        """Handle submit_diagnosis action and compute final score."""
        self._is_done = True
        self._diagnosis_submitted = True
        
        ground_truth = self._current_scenario["ground_truth"]
        score = 0.0
        feedback = []
        
        # Root cause (40%)
        if action.root_cause == ground_truth["root_cause"]:
            score += 0.4
            feedback.append("Root cause: CORRECT")
        else:
            feedback.append(f"Root cause: WRONG (expected {ground_truth['root_cause']})")
        
        # Severity (20%)
        if action.severity == ground_truth["severity"]:
            score += 0.2
            feedback.append("Severity: CORRECT")
        else:
            feedback.append(f"Severity: WRONG (expected {ground_truth['severity']})")
        
        # Affected services (25%) - F1 score
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
        
        # Recommended action (15%)
        if action.recommended_action == ground_truth["recommended_action"]:
            score += 0.15
            feedback.append("Recommended action: CORRECT")
        else:
            feedback.append(f"Recommended action: WRONG (expected {ground_truth['recommended_action']})")
        
        message = f"Investigation complete! Score: {score:.2f}. " + " | ".join(feedback)
        return score, message

    def _make_observation(self, message: str, reward: float) -> LogAnalysisObservation:
        """Create observation with current state."""
        return LogAnalysisObservation(
            alert_title=self._current_scenario["alert"]["title"],
            alert_severity=self._current_scenario["alert"]["severity"],
            available_services=self._current_scenario["services"],
            fetched_logs=self._fetched_logs,
            fetched_metrics=self._fetched_metrics,
            steps_taken=self._state.step_count,
            max_steps=self.MAX_STEPS,
            available_root_causes=ALL_ROOT_CAUSES,
            available_severities=["critical", "high", "medium", "low"],
            available_actions=ALL_RECOMMENDED_ACTIONS,
            is_done=self._is_done,
            message=message,
            done=self._is_done,
            reward=reward,
        )

    @property
    def state(self) -> State:
        return self._state