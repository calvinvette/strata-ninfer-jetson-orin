# Source attribution for this integration fork

The active starting engine and its inherited files are Strata by Niko1221 and
the Strata contributors, under the root [MIT license](LICENSE). The Orin port is
preserved from [calvinvette/strata-inference-orin](https://github.com/calvinvette/strata-inference-orin)
at `0be090c8997b24cf5d21557ced40a1b7e93e87d3`.

`reference/ninfer/` contains NInfer source and documentation from
[calvinvette/ninfer-jetson-orin](https://github.com/calvinvette/ninfer-jetson-orin),
revision `b07248f2528125aeda7550055580204541f1714c`, including work from its upstream
contributors and the Orin port. Its [LICENSE](reference/ninfer/LICENSE) is
Apache License 2.0. Existing copyright and dependency notices are retained.
NInfer's original `AGENTS.md` was renamed `UPSTREAM_AGENT_GUIDANCE.md`; file bytes
otherwise match the pinned source for all committed imports. The added reference
`AGENTS.md` and this integration documentation belong to this bootstrap.

`evidence/ninfer-orin/` contains separately labeled local reports and the modified
working-tree plan from that port. The import manifest lists each origin and hash.
These copied materials retain their source attribution; they are not new results.

NInfer's bundled third-party files, evaluation corpora and model cards retain
their own license/notice files, including
[corpus notices](reference/ninfer/eval/corpora/perplexity-1m/THIRD_PARTY_NOTICES.md).
Model weights are not included. The root MIT license does not relicense the
imported NInfer or its dependencies. Future adapted files must identify their
source path/revision, retain notices and record material changes.
