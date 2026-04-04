from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import LogAnalysisAction, LogAnalysisObservation
except ImportError:
    from models import LogAnalysisAction, LogAnalysisObservation


class LogAnalysisClient(
    EnvClient[LogAnalysisAction, LogAnalysisObservation, State]
):
    def _step_payload(self, action: LogAnalysisAction) -> Dict:
        return {
            "action_type": action.action_type,
            "service": action.service,
            "metric": action.metric,
            "root_cause": action.root_cause,
            "severity": action.severity,
            "affected_services": action.affected_services,
            "recommended_action": action.recommended_action,
        }

    def _parse_result(self, payload: Dict) -> StepResult[LogAnalysisObservation]:
        obs_data = payload.get("observation", {})
        observation = LogAnalysisObservation(
            alert_title=obs_data.get("alert_title", ""),
            alert_severity=obs_data.get("alert_severity", ""),
            available_services=obs_data.get("available_services", []),
            fetched_logs=obs_data.get("fetched_logs", {}),
            fetched_metrics=obs_data.get("fetched_metrics", {}),
            steps_taken=obs_data.get("steps_taken", 0),
            max_steps=obs_data.get("max_steps", 10),
            available_root_causes=obs_data.get("available_root_causes", []),
            available_severities=obs_data.get("available_severities", []),
            available_actions=obs_data.get("available_actions", []),
            is_done=obs_data.get("is_done", False),
            message=obs_data.get("message", ""),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )