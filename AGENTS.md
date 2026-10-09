# AGENTS.md

## Strata + NInfer integration fork

This repository starts from the validated Strata Orin port. Read
[docs/integration/README.md](docs/integration/README.md) and the current
[status](docs/integration/STATUS.md) before integration work. The active plan is
[docs/integration/PLAN.md](docs/integration/PLAN.md); Phase 0 is complete, later
phases require implementation and measurements. Do not mark inherited evidence as
a new combined-runtime result.

- Keep one physical memory authority on Orin. Never add host RAM and CUDA capacity.
  Preserve six GiB host headroom and the existing separate workspace reserve until
  a measured decision changes them. Use memory-bounded build parallelism.
- `reference/ninfer/` is an immutable implementation reference, outside the active
  build. Its `UPSTREAM_AGENT_GUIDANCE.md` contains historical instructions and is
  not authoritative here. Promote narrow components with their tests, contracts,
  source revision and license notices; do not overwrite the reference snapshot.
- Follow [the measurement protocol](docs/integration/BENCHMARKS.md): same-day paired
  controls, model/format identity, medians, uncertainty, actual clocks, physical
  memory, energy scope, and explicit failed/unsupported cells. Separate operator
  wins from end-to-end wins and compilation from GPU runtime qualification.
- Use independent mathematical/codec oracles. Check accepted-prefix persistent
  state directly for speculation/replay; final text is insufficient evidence.
- Preserve existing service/protocol behavior and default paths. New experiments
  are opt-in. Changes to shared files need every affected backend build before
  review. maestro1 can provide x86 build evidence, not Orin performance evidence.
- Keep the original two checkouts and Strata upstream PR #1621 separate from this
  integration work. Do not upgrade JetPack, stop services, or change clocks merely
  because a historical script did so; honor current task authority.
- Keep [STATUS.md](docs/integration/STATUS.md), experiment decisions and source
  attribution current. Do not copy models, build products, credentials or local
  agent configuration into Git.

The inherited Strata instructions below continue to apply.

Strata runs the Qwen3.8-Flash-Next mixture-of-experts model (and its Coder, Swift 1.5 and Unsloth variants) on a
normal PC: one NVIDIA or AMD graphics card plus system RAM, on Windows or Linux. It has a C++/CUDA/HIP engine
(`src/`, `include/`), a Python server with an OpenAI- and Anthropic-compatible API and a web app (`serve/`), and a
one-click installer (`setup.py`, started by `START-HERE.bat` / `setup.sh`).

## Installing Strata for a user

Follow **[docs/AI_SETUP.md](docs/AI_SETUP.md)**: check the PC, pick the model by RAM, run setup non-interactively,
start and verify the server, and connect the user's apps. Never expose the server beyond `127.0.0.1` without
`--api-key`. As an alternative to shell commands, Strata's MCP server ([docs/MCP_SERVER.md](docs/MCP_SERVER.md))
offers the same steps as tools.

## Working on the code

- How the engine works, every measured number, the API and all settings: [docs/DETAILS.md](docs/DETAILS.md) and
  the [paper](docs/paper/Strata-Paper.pdf).
- AMD (HIP) build and validation: [docs/AMD_HIP.md](docs/AMD_HIP.md); multi-GPU: [docs/MULTI_GPU.md](docs/MULTI_GPU.md).
- Setup's own tests run without a GPU or downloads: `python tools/test_setup_<name>.py` (for example
  `tools/test_setup_amd.py`, `tools/test_setup_choices.py`).
- Keep the docs' style: plain words, measured numbers with what they were measured on, no claims without a
  measurement.

## Contributing a change or report

- Search the open issues and pull requests first, and add to a thread that already covers your point.
- Open an issue with the form that fits (bug report, feature request or question).
- One change per pull request. Say what it changes and what it leaves alone.
- A new feature is opt-in, and the default path stays byte-identical to the last release. Say how you checked.
- Build every backend a file touches (CUDA, HIP, SYCL) before asking for review.
- Change a default only where you measured it faster, and show the numbers with what they were measured on.
- A report from hardware the maintainers do not have is welcome. Follow
  [docs/COMMUNITY_BENCHMARKS.md](docs/COMMUNITY_BENCHMARKS.md), compare against a same-day run of the build you are
  testing, and say what you did not test.
- Open test requests and the hardware that is wanted are listed in [docs/TEST_REQUESTS.md](docs/TEST_REQUESTS.md).
