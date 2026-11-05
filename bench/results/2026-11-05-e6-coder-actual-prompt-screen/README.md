# Coder IQ1_M actual-prompt backend screens

These screens compare the same Strata build with its default expert backend
and strict NInfer on Jetson Orin AGX (SM87, CUDA 12.6). Both used Qwen3.8-
Flash-Next-GSQ-RCO Coder IQ1_M, the same 256-slot profile, 6 GiB static PCIe
complement, `--adapt-every 0`, CPU prefill sharing off, and a six-GiB memory
floor. Each arm warmed up on its exact measured prompt. Prompts use
length-controlled unrelated filler followed by a held-out `is_prime(n)` task;
they are synthetic inputs, not natural documents or codebases.

## Summary

| Actual prompt / context | Pairs | Prompt TPS change | Decode TPS change | TTFT reduction | Client-time reduction | Quality / minimum RAM |
|---|---:|---:|---:|---:|---:|---|
| 8,192 / 16,384 tokens | 4 | +0.06% (−0.03%, +0.12%) | −0.39% (−0.61%, −0.08%) | +0.06% (−0.03%, +0.12%) | +0.03% (−0.05%, +0.08%) | All outputs matched, 11-case oracle passed; 14.46 GiB |
| 16,384 / 32,768 tokens | 4 | −0.14% (−0.47%, +0.04%) | −1.19% (−2.88%, −0.56%) | −0.15% (−0.47%, +0.04%) | −0.18% (−0.48%, −0.07%) | All outputs matched, 11-case oracle passed; 14.02 GiB |
| 32,768 / 65,536 tokens | 4 | +0.02% (−0.16%, +0.34%) | −2.92% (−71.69%, +4.82%) | +0.01% (−0.16%, +0.33%) | −0.16% (−4.40%, +0.16%) | All outputs matched, 11-case oracle passed; 13.09 GiB |

Parentheses show the four-pair screening interval from the saved paired
bootstrap summary; they describe only each tested task/profile. At both lengths,
the backends recorded identical resident hits and lookups within every pair:
1,470/33,213 at 8K and 1,468/33,213 at 16K. The 8K decode interval is entirely
negative but its effect is under 1%; at 16K the measured decode regression is
larger but remains below the pre-registered 5% useful-effect threshold.
Neither screen demonstrates a useful NInfer speedup.

At 32K, three paired decode effects were between −5.37% and +4.82%; the
fourth was −71.69% and is retained in the result. That NInfer arm had 1,505
resident hits / 34,037 lookups versus 1,470 / 33,219 for its paired Strata
arm, while outputs still matched and passed the oracle. The reason for this
route-count difference and decode outlier is unknown. The four-pair median is
therefore not evidence of a stable decode effect. Prompt TPS, TTFT and
client-time medians stayed close to zero. This screen shows no useful
end-to-end gain.

The 32K supervisor passed its six-GiB available-memory floor with 13.09 GiB
minimum available RAM. CPU/GPU clocks were observed but uncontrolled; EMC
readback was denied and energy was not measured. No state capture was used.
These results do not qualify general long-context quality or other prompt
families. E6/E7 remain open and no profile is promoted.

## Evidence

- [8K measurements](input-8192-retry2/results.json)
- [8K supervisor result](supervisor-8192-retry2/result.json)
- [16K measurements](input-16384/results.json)
- [16K supervisor result](supervisor-16384/result.json)
- [32K measurements](input-32768/results.json)
- [32K supervisor result](supervisor-32768-fastprep/result.json)

Raw arm logs and telemetry remain local and are not included in Git. Each JSON
records model-shard hashes, prompt hash, binary/profile hashes and exact runtime
options. The 8K, 16K and 32K screens ran on the same date but are separate
prompt length points, not a combined randomized context-by-backend experiment.
The 32K prompt was constructed with a binary search over filler length (15
tokenizer/template passes); this changes only prompt preparation, not the
measured request.
