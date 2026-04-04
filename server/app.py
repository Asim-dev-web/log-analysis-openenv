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


def main(port: int = 8000):
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)