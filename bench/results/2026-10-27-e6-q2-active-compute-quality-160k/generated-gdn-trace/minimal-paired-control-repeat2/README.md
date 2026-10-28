# E6 160K minimal paired control, repeat 2

## Outcome

The second no-capture staged Strata/NInfer pair again generated the same exact
47-token answer with identical token IDs and residency. The within-pair final
state differs in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`; `L`, `ple`,
`dead`, and `ple_prev` match. As with the first pair, the harness exits as a
correctness failure. Equal text does not establish persistent-state parity.

Across the two no-capture pairs, each backend's final fingerprints for those
five fields also differ between runs, despite identical token IDs and residency
hashes. These are hashes of raw active state bytes: the implementation streams
the owned GDN buffer, QSA tail/dead/pooled arrays, and KV cells through `L` into
FNV-1a fingerprints (`src/program/generate.cpp`, `hash_session_state`). They do
not include pointers or allocation addresses. The observation therefore shows
run-to-run variation in the hashed state bytes, but hashes do not quantify the
size or location of the numerical differences. `ple`, `dead`, and `ple_prev`
remain identical across both backends and both runs.

| Arm | Pair 1 GDN | Pair 2 GDN | Pair 1 tail | Pair 2 tail | Pair 1 pooled | Pair 2 pooled | Pair 1 KV | Pair 2 KV |
|---|---|---|---|---|---|---|---|---|
| Strata | `2a90fc4a12c0c0ad` | `fe8b2b44ca2ee539` | `659dac83cfe3e9f3` | `d64719a1c2a0d0d1` | `cdae5f0fa91fbf29` | `bb62045bdc0f1e06` | `d09a76643288496a` | `c73b08c17fdad83d` |
| NInfer | `9a500914230499a4` | `10cdca1453c99143` | `2a057cb7040b261f` | `d29bc49bf6ea10ba` | `75334cd467b38850` | `629b3a89c242bd6d` | `7a6f07bd7218d191` | `84492cede33af65d` |

## Run conditions

The workload was `heldout-retrieval-arithmetic-163840`, with 163,840 prompt
tokens and the same prompt content/token-ID SHA256 values as pair 1. There were
no optional capture sidecars. Pair 2 took 54.52 minutes; minimum available
memory was 6.59 GiB, peak swap was 1.30 GiB, and sampled OOM kills were zero.
Clocks were observed only; energy was not measured. The supervisor returned
failure because the final state comparison failed. This is a correctness
diagnostic, not a performance result.

Raw logs and telemetry remain local-only. The JSON result is retained with the
local run output and is not committed.
