#!/usr/bin/env bash
set -euo pipefail
trace_root="$HOME/workspace/strata-integration-validation"
printf 'waiting for verifier-only build\n' > "$trace_root/expanded-build-state.txt"
# The initial script owns its source snapshot until both backends finish.
for attempt in $(seq 1 2160); do
    if ! ps -p 581655 -o args= | grep -Fq "$trace_root/build-trace-backends.sh"; then
        break
    fi
    sleep 10
done
if ps -p 581655 -o args= | grep -Fq "$trace_root/build-trace-backends.sh"; then
    printf 'failed: verifier-only build wait deadline\n' > "$trace_root/expanded-build-state.txt"
    exit 1
fi
if ! test -f "$trace_root/logs/hip-result.txt" || ! test -f "$trace_root/logs/sycl-result.txt"; then
    printf 'failed: verifier-only build did not pass both backends; source untouched\n' > "$trace_root/expanded-build-state.txt"
    exit 1
fi
files=(include/strata/platform/integration_trace.hpp src/core/verify.cpp src/core/mtp.cpp src/prefill/prefill.cpp sycl/src/core/verify.cpp sycl/src/core/mtp.cpp sycl/src/prefill/prefill.cpp)
cd "$trace_root/source"
sha256sum "${files[@]}" > "$trace_root/verifier-only-source-sha256.txt"
sha256sum "$trace_root/build-hip/strata" "$trace_root/build-sycl/strata" > "$trace_root/verifier-only-binary-sha256.txt"
tar -xf "$trace_root/expanded-owner-overlay.tar"
# tar preserves mtimes; force recompilation after applying a newer snapshot.
touch "${files[@]}"
sha256sum "${files[@]}" > "$trace_root/expanded-source-sha256.txt"
mkdir -p "$trace_root/logs-expanded"
sed 's|/logs/|/logs-expanded/|g' "$trace_root/build-trace-backends.sh" > "$trace_root/build-expanded-snapshot.sh"
printf 'building expanded HIP then SYCL with one compile job\n' > "$trace_root/expanded-build-state.txt"
if bash "$trace_root/build-expanded-snapshot.sh"; then
    sha256sum "$trace_root/build-hip/strata" "$trace_root/build-sycl/strata" > "$trace_root/expanded-binary-sha256.txt"
    printf 'passed: expanded HIP and SYCL compilation; GPU runtime unqualified\n' > "$trace_root/expanded-build-state.txt"
else
    printf 'failed: inspect logs-expanded; no runtime qualification\n' > "$trace_root/expanded-build-state.txt"
    exit 1
fi
