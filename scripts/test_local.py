"""Run regressions; optionally include isolation checks on the local development database."""

import argparse
import os
import subprocess
import sys
from .dev_database import ROOT, dsn, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres", action="store_true")
    args = parser.parse_args()
    env = os.environ.copy()
    env["AGROSHIFT_CONTEXT_OFFLINE"] = "1"
    if args.postgres:
        env["AGROSHIFT_TEST_PG_ADMIN"] = dsn(settings(), "admin")
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "pytest", "--tb=short"], cwd=ROOT, env=env
        )
    )


if __name__ == "__main__":
    main()
