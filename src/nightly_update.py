#!/usr/bin/env python3
"""
Nightly refresh entrypoint for Terrebonne Parish School Bus Routing.

Re-runs the zone assignment engine against the current student
registrations and route file, so any registrations added/edited during
the day are reflected in tomorrow's assignments. Prints a summary
that the calling automation can relay to the user, and leaves updated
CSVs in data/ ready to be committed and pushed to GitHub.
"""
import subprocess
import sys
import os
import datetime

HERE = os.path.dirname(__file__)


def main():
    print(f"=== Terrebonne school bus nightly update — {datetime.datetime.now().isoformat()} ===")
    result = subprocess.run(
        [sys.executable, os.path.join(HERE, "assign_bus.py")],
        capture_output=True, text=True,
    )
    print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
