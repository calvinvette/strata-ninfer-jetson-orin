# Runs the repo's own run_cell.py workload (172/557/1069-token prompts x 3 rounds, 64 tokens, greedy) with our config.
import sys
from pathlib import Path
sys.path.insert(0, "/home/training/strata/strata-ninfer-jetson-orin/bench/results/2026-10-25-flashnext-context-capacity-sweep")
import run_cell
run_cell.TEMPLATES["coder-q2_0"] = Path(sys.argv[1])
sys.argv = ["run_cell.py", "--model", "coder-q2_0", "--context", "8192", "--out", sys.argv[2], "--port", "18885"]
run_cell.main()
