#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "$0")/../../.." && pwd)"
remote_root=/home/calvin/workspace/strata-validation/integration/strata-ninfer-phase8-20261017
scp "$repo/include/strata/core/verify.hpp" \
    "maestro1:$remote_root/source/include/strata/core/verify.hpp"
scp "$repo/src/core/verify.cpp" \
    "maestro1:$remote_root/source/src/core/verify.cpp"
scp "$repo/src/program/generate.cpp" \
    "maestro1:$remote_root/source/src/program/generate.cpp"
scp "$repo/bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/build_maestro1.sh" \
    maestro1:/home/calvin/build_graph_limit.sh
ssh maestro1 'bash /home/calvin/build_graph_limit.sh'
out="$repo/bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/backend-builds-maestro1-graph-limit"
mkdir -p "$out"
scp -r "maestro1:$remote_root/logs/graph-limit-20261022/." "$out/"
