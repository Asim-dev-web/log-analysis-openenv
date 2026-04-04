from uuid import uuid4
from typing import Dict
import random

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
    from .scenarios import SCENARIOS_BY_DIFFICULTY, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS
except ImportError:
    from scenarios import SCENARIOS_BY_DIFFICULTY, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS


_SHARED_STATE = {
    "scenario": None,
    "fetched_logs": {},
    "fetched_metrics": {},
    "is_done": False,
    "step_count": 0,
    "diagnosis_submitted": False,
    "episode_count": 0,
    "difficulty": "easy",
}


class LogAnalysisEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = False
    MAX_STEPS: int = 10

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self) -> LogAnalysisObservation:
        _SHARED_STATE["episode_count"] += 1
        
        difficulties = ["easy", "medium", "hard"]
        _SHARED_STATE["difficulty"] = difficulties[(_SHARED_STATE["episode_count"] - 1) % 3]
        
        _SHARED_STATE["fetched_logs"] = {}
        _SHARED_STATE["fetched_metrics"] = {}
        _SHARED_STATE["is_done"] = False
        _SHARED_STATE["step_count"] = 0
        _SHARED_STATE["diagnosis_submitted"] = False
        
        scenarios = SCENARIOS_BY_DIFFICULTY.get(_SHARED_STATE["difficulty"], SCENARIOS_BY_DIFFICULTY["easy"])
        _SHARED_STATE["scenario"] = random.choice(scenarios)
        
        self._state = State(episode_id=str(uuid4()), step_count=0)

        services = _SHARED_STATE["scenario"]["services"]
        return self._make_observation(
            f"Investigation started. Alert received. Available services to investigate: {services}. Use fetch_logs or fetch_metrics to gather evidence, then submit_diagnosis.",
            0.0
        )

    def step(self, action: LogAnalysisAction) -> LogAnalysisObservation:
        if _SHARED_STATE["scenario"] is None:
            return LogAnalysisObservation(
                alert_title="",
                alert_severity="",
                available_services=[],
                fetched_logs={},
                fetched_metrics={},
                steps_taken=0,
                max_steps=self.MAX_STEPS,
                available_root_causes=[],
                available_severities=[],
                available_actions=[],
                is_done=True,
                message="Error: Call reset() first",
                done=True,
                reward=0.0,
            )
        
        _SHARED_STATE["step_count"] += 1
        self._state.step_count = _SHARED_STATE["step_count"]
        reward = 0.0
        message = ""

        if _SHARED_STATE["is_done"]:
            return self._make_observation("Episode already ended. Call reset() to start new episode.", 0.0)

        if action.action_type == "fetch_logs":
            reward, message = self._handle_fetch_logs(action)
        elif action.action_type == "fetch_metrics":
            reward, message = self._handle_fetch_metrics(action)
        elif action.action_type == "submit_diagnosis":
            reward, message = self._handle_submit_diagnosis(action)
        else:
            valid_actions = "fetch_logs, fetch_metrics, submit_diagnosis"
            message = f"Invalid action_type: '{action.action_type}'. Must be one of: {valid_actions}"
            reward = 0.0

        if _SHARED_STATE["step_count"] >= self.MAX_STEPS and not _SHARED_STATE["is_done"]:
            _SHARED_STATE["is_done"] = True
            if not _SHARED_STATE["diagnosis_submitted"]:
                message += " Max steps reached without diagnosis. Use submit_diagnosis action with root_cause, severity, affected_services, and recommended_action fields."

        return self._make_observation(message, reward)

    def _handle_fetch_logs(self, action: LogAnalysisAction) -> tuple:
        service = action.service
        services = _SHARED_STATE["scenario"]["services"]
        
        if not service:
            return 0.0, f"Error: 'service' field required. Available services: {services}"
        
        if service not in services:
            return 0.0, f"Error: Unknown service '{service}'. Available services: {services}"
        
        if service in _SHARED_STATE["fetched_logs"]:
            not_fetched = [s for s in services if s not in _SHARED_STATE["fetched_logs"]]
            if not_fetched:
                return 0.0, f"Already fetched logs from '{service}'. Services not yet investigated: {not_fetched}"
            return 0.0, f"Already fetched logs from '{service}'. All services investigated. Use submit_diagnosis now with root_cause, severity, affected_services, recommended_action."

        logs = _SHARED_STATE["scenario"]["logs"].get(service, [])
        _SHARED_STATE["fetched_logs"][service] = logs

        not_fetched = [s for s in services if s not in _SHARED_STATE["fetched_logs"]]
        affected = _SHARED_STATE["scenario"]["ground_truth"]["affected_services"]
        
        if service in affected:
            if not_fetched:
                return 0.02, f"Fetched {len(logs)} logs from '{service}'. Found errors. Services remaining: {not_fetched}"
            return 0.02, f"Fetched {len(logs)} logs from '{service}'. Found errors. All services investigated. Ready for submit_diagnosis."
        else:
            if not_fetched:
                return 0.01, f"Fetched {len(logs)} logs from '{service}'. No critical issues. Try: {not_fetched}"
            return 0.01, f"Fetched {len(logs)} logs from '{service}'. All services investigated. Ready for submit_diagnosis."

    def _handle_fetch_metrics(self, action: LogAnalysisAction) -> tuple:
        service = action.service
        services = _SHARED_STATE["scenario"]["services"]
        
        if not service:
            return 0.0, f"Error: 'service' field required. Available services: {services}"
        
        if service not in services:
            return 0.0, f"Error: Unknown service '{service}'. Available services: {services}"
        
        if service in _SHARED_STATE["fetched_metrics"]:
            not_fetched = [s for s in services if s not in _SHARED_STATE["fetched_metrics"]]
            if not_fetched:
                return 0.0, f"Already fetched metrics from '{service}'. Services not yet checked: {not_fetched}"
            return 0.0, f"Already fetched metrics from '{service}'. All checked. Use submit_diagnosis now."

        metrics = _SHARED_STATE["scenario"]["metrics"].get(service, {})
        _SHARED_STATE["fetched_metrics"][service] = metrics

        not_fetched = [s for s in services if s not in _SHARED_STATE["fetched_metrics"]]
        affected = _SHARED_STATE["scenario"]["ground_truth"]["affected_services"]
        
        if service in affected:
            if not_fetched:
                return 0.02, f"Fetched metrics from '{service}'. Anomalies detected. Remaining: {not_fetched}"
            return 0.02, f"Fetched metrics from '{service}'. Anomalies detected. Ready for submit_diagnosis."
        else:
            if not_fetched:
                return 0.01, f"Fetched metrics from '{service}'. Values normal. Try: {not_fetched}"
            return 0.01, f"Fetched metrics from '{service}'. All checked. Ready for submit_diagnosis."

    def _handle_submit_diagnosis(self, action: LogAnalysisAction) -> tuple:
        _SHARED_STATE["is_done"] = True
        _SHARED_STATE["diagnosis_submitted"] = True

        investigated = len(_SHARED_STATE["fetched_logs"]) + len(_SHARED_STATE["fetched_metrics"])
        
        if investigated < 2:
            return 0.05, "Diagnosis submitted with insufficient investigation. Investigate more services for better score."

        ground_truth = _SHARED_STATE["scenario"]["ground_truth"]
        score = 0.0
        feedback = []

        if action.root_cause == ground_truth["root_cause"]:
            score += 0.30
            feedback.append("Root cause: CORRECT")
        else:
            feedback.append(f"Root cause: INCORRECT (was: {ground_truth['root_cause']})")

        if action.severity == ground_truth["severity"]:
            score += 0.15
            feedback.append("Severity: CORRECT")
        else:
            feedback.append(f"Severity: INCORRECT (was: {ground_truth['severity']})")

        if action.affected_services:
            predicted = set(action.affected_services)
            actual = set(ground_truth["affected_services"])
            intersection = len(predicted & actual)
            precision = intersection / len(predicted) if predicted else 0
            recall = intersection / len(actual) if actual else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            service_score = 0.20 * f1
            score += service_score
            feedback.append(f"Affected services: {f1:.0%} match")
        else:
            feedback.append("Affected services: NOT PROVIDED")

        if action.recommended_action == ground_truth["recommended_action"]:
            score += 0.10
            feedback.append("Recommended action: CORRECT")
        else:
            feedback.append(f"Recommended action: INCORRECT (was: {ground_truth['recommended_action']})")

        message = f"Diagnosis complete. Score: {score:.2f}/0.75. " + " | ".join(feedback)
        return score, message

    def _make_observation(self, message: str, reward: float) -> LogAnalysisObservation:
        scenario = _SHARED_STATE["scenario"]
        
        logs_fetched = list(_SHARED_STATE["fetched_logs"].keys())
        metrics_fetched = list(_SHARED_STATE["fetched_metrics"].keys())
        all_investigated = set(logs_fetched) | set(metrics_fetched)
        not_investigated = [s for s in scenario["services"] if s not in all_investigated]
        
        steps_remaining = self.MAX_STEPS - _SHARED_STATE["step_count"]
        
        if not _SHARED_STATE["is_done"]:
            if steps_remaining <= 2 and not _SHARED_STATE["diagnosis_submitted"]:
                message += f" URGENT: Only {steps_remaining} steps left! Submit diagnosis now using: submit_diagnosis with root_cause, severity, affected_services, recommended_action."
            elif not not_investigated and not _SHARED_STATE["diagnosis_submitted"]:
                message += " All services investigated. Submit your diagnosis."
        
        return LogAnalysisObservation(
            alert_title=scenario["alert"]["title"],
            alert_severity=scenario["alert"]["severity"],
            available_services=scenario["services"],
            fetched_logs=_SHARED_STATE["fetched_logs"],
            fetched_metrics=_SHARED_STATE["fetched_metrics"],
            steps_taken=_SHARED_STATE["step_count"],
            max_steps=self.MAX_STEPS,
            available_root_causes=ALL_ROOT_CAUSES,
            available_severities=["critical", "high", "medium", "low"],
            available_actions=ALL_RECOMMENDED_ACTIONS,
            is_done=_SHARED_STATE["is_done"],
            message=message,
            done=_SHARED_STATE["is_done"],
            reward=reward,
        )

    @property
    def state(self) -> State:
        return self._state