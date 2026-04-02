from openenv.core.env_server.types import Action, Observation
from pydantic import Field
from typing import List, Optional


class LogAnalysisAction(Action):
    """
    Action for the Log Analysis environment.
    
    Agent can do one of three things:
    1. fetch_logs - get logs from a service
    2. fetch_metrics - get metrics from a service  
    3. submit_diagnosis - submit final answer
    
    Valid values for each field are provided in the Observation under:
    - available_services
    - available_root_causes  
    - available_severities
    - available_actions
    """
    
    # What type of action is this? (REQUIRED)
    action_type: str = Field(
        ..., 
        description="MUST be exactly one of: fetch_logs, fetch_metrics, submit_diagnosis"
    )
    
    # === Fields for fetch_logs and fetch_metrics ===
    service: Optional[str] = Field(
        default=None, 
        description="Service to fetch from. MUST be a value from available_services in the observation."
    )
    
    # === Fields for fetch_metrics only ===
    metric: Optional[str] = Field(
        default=None,
        description="MUST be exactly one of: cpu_usage, memory_usage, error_rate, latency_p99, connections_active, threads_active"
    )
    
    # === Fields for submit_diagnosis only ===
    root_cause: Optional[str] = Field(
        default=None,
        description="Root cause of incident. MUST be a value from available_root_causes in the observation."
    )
    
    severity: Optional[str] = Field(
        default=None,
        description="MUST be exactly one of: critical, high, medium, low"
    )
    
    affected_services: Optional[List[str]] = Field(
        default=None,
        description="List of affected services. Each value MUST be from available_services in the observation."
    )
    
    recommended_action: Optional[str] = Field(
        default=None,
        description="Action to fix the issue. MUST be a value from available_actions in the observation."
    )


class LogAnalysisObservation(Observation):
    """
    Observation for the Log Analysis environment.
    
    This is what the agent sees at each step.
    """
    
    # === The Alert (What triggered this investigation) ===
    alert_title: str = Field(
        default="",
        description="Title of the alert that triggered this investigation"
    )
    
    alert_severity: str = Field(
        default="",
        description="Initial severity of the alert: critical, high, medium, low"
    )
    
    # === Available Services ===
    available_services: List[str] = Field(
        default_factory=list,
        description="List of services the agent can investigate"
    )
    
    # === What agent has discovered so far ===
    fetched_logs: dict = Field(
        default_factory=dict,
        description="Logs fetched so far. Format: {service_name: [log_lines]}"
    )
    
    fetched_metrics: dict = Field(
        default_factory=dict,
        description="Metrics fetched so far. Format: {service_name: {metric_name: value}}"
    )
    
    # === Step tracking ===
    steps_taken: int = Field(
        default=0,
        description="Number of steps taken so far in this episode"
    )
    
    max_steps: int = Field(
        default=10,
        description="Maximum steps allowed before episode ends"
    )
    
    # === Valid options (agent MUST choose from these) ===
    available_root_causes: List[str] = Field(
        default_factory=list,
        description="Valid root causes the agent can diagnose"
    )
    
    available_severities: List[str] = Field(
        default_factory=lambda: ["critical", "high", "medium", "low"],
        description="Valid severity levels"
    )
    
    available_actions: List[str] = Field(
        default_factory=list,
        description="Valid recommended actions the agent can suggest"
    )
    
    # === Episode status ===
    is_done: bool = Field(
        default=False,
        description="Whether the episode has ended"
    )
    
    message: str = Field(
        default="",
        description="Feedback message to the agent"
    )
