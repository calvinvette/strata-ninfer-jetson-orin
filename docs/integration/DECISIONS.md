# Initial decisions

| ID | Decision | Reason / revisiting condition |
| --- | --- | --- |
| D001 | Start with Strata's Flash-Next runtime and verified Coder IQ1_M pack | Retains the working out-of-core expert path; revisiting requires a new exact-target/format proposal |
| D002 | Import NInfer as a pinned reference, then promote qualified components | Whole runtimes and packed formats are not interchangeable; build/link integration occurs per contract |
| D003 | One physical LPDDR authority, with typed allocation/reservation constraints | Host/device duplication and workspace/transition peaks matter on Orin |
| D004 | Explicit allocations and six GiB headroom remain controls | Managed/mapped/async paths require buffer-specific ownership and measured benefit |
| D005 | Numerical oracles precede performance; state checks precede speculative publication | Text plausibility cannot establish operator or accepted-prefix state correctness |
| D006 | Kernel wins require request-level confirmation | Historical 37.3% operator gain did not imply a comparable full-engine gain |
| D007 | Different models/formats remain separate benchmark cohorts | Prevents attributing a model, quantization or clock change to integration work |
| D008 | Keep CUDA 12.6/SM87 for the first campaign | Toolchain/clock upgrades are independent experiments, contingent on verified board support |
| D009 | Single active request first; concurrency is conditional later work | Admission/state ownership and physical capacity must be proven before compact decode batching |
| D010 | Independent GitHub repository with preserved Strata ancestry | Account already owns the Strata network fork; this keeps PR #1621 separate from integration research |

For a change to these decisions, use the [decision template](templates/decision.md)
and link its evidence from this table. No measured defaults change in the bootstrap.
