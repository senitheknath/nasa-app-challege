"""Launch the existing Streamlit app with local PostgreSQL when configured."""

import argparse
import os
import subprocess
import sys
from .dev_database import ROOT, CONFIG, settings, dsn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--cached-context", action="store_true")
    args = parser.parse_args()
    env = os.environ.copy()
    if args.cached_context:
        env["AGROSHIFT_CONTEXT_OFFLINE"] = "1"
    if CONFIG.exists():
        config = settings()
        env.setdefault("AGROSHIFT_DATABASE_URL", dsn(config))
        env.setdefault("AGROSHIFT_PRIVATE_DATABASE_URL", dsn(config, "app"))
    print(f"AgroShift: http://localhost:{args.port}", flush=True)
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.address=127.0.0.1",
                f"--server.port={args.port}",
            ],
            env=env,
            cwd=ROOT,
        )
    )


if __name__ == "__main__":
    main()
