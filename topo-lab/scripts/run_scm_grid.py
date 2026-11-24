"""Run 5-repetition grid for SCM benchmark across sequential, parallel, and probeordered topologies."""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON = ROOT / "agentic-ai-guarantees" / "bin" / "python3"
EXECUTE_SCRIPT = ROOT / "topo-lab" / "scripts" / "execute_graph.py"

TOPOLOGIES = [
    ("scm__order-fulfillment.probe.sequential.json", "sequential"),
    ("scm__order-fulfillment.probe.parallel.json", "parallel"),
    ("scm__order-fulfillment.probeordered.parallel.json", "probeordered"),
]

REPS = ["rep2", "rep3", "rep4", "rep5"]

env = os.environ.copy()
# Source key from setup_keys.sh if not set
if "GOOGLE_API_KEY" not in env or not env["GOOGLE_API_KEY"]:
    setup_file = ROOT / "setup_keys.sh"
    if setup_file.exists():
        for line in setup_file.read_text().splitlines():
            if line.startswith("export GOOGLE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                env["GOOGLE_API_KEY"] = key

for graph_file, label in TOPOLOGIES:
    graph_path = ROOT / "topo-lab" / "graphs" / "rendered" / graph_file
    for rep in REPS:
        print(f"\n==========================================")
        print(f"Executing {label} ({rep})...")
        print(f"==========================================")
        cmd = [
            str(PYTHON),
            str(EXECUTE_SCRIPT),
            str(graph_path),
            "--agent",
            "gemini-flash-lite",
            "--tag",
            rep,
        ]
        res = subprocess.run(cmd, env=env)
        if res.returncode != 0:
            print(f"Error running {label} {rep}: returncode {res.returncode}")
        time.sleep(3)  # Respect free tier rate limits

print("\nGrid execution finished.")
