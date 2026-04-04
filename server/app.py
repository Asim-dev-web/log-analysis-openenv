try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required. Install with 'uv sync'"
    ) from e

try:
    from ..models import LogAnalysisAction, LogAnalysisObservation
    from .my_env_environment import LogAnalysisEnvironment
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from models import LogAnalysisAction, LogAnalysisObservation
    from server.my_env_environment import LogAnalysisEnvironment


app = create_app(
    LogAnalysisEnvironment,
    LogAnalysisAction,
    LogAnalysisObservation,
    env_name="log_analysis",
    max_concurrent_envs=1,
)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()