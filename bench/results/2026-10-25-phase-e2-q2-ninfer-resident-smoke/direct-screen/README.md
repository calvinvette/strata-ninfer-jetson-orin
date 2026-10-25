# Direct-mapped NInfer Q2_0 service screen

Three fresh Orin services used the same Q2_0 model and PLE, 3,000-slot profile,
1-GiB page-locked resident complement, six-GiB physical headroom plus separate
three-GiB workspace reserve, prompt, generation settings and GPU resident-map
hash (`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Each
used strict NInfer and `--pcie-frac 0.55 --pcie-mode direct`. Each measured
request generated 29 tokens with the same output hash
`18e649c52e8a6a942bfb6c486a4da267fc7ca05faaf55c831ea4b35372df848e`.

| Run | Prompt latency | Decode latency | Client total | First-text TTFT | GPU offloads |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.877 s | 3.289 s | 9.169 s | 5.970 s | 106 (0.8%) |
| 2 | 5.873 s | 3.303 s | 9.179 s | 5.967 s | 106 (0.8%) |
| 3 | 5.885 s | 3.296 s | 9.184 s | 5.979 s | 106 (0.8%) |

Direct-mapped access completed without error and processed the same number of
`pcie_frac`-selected miss experts as the copied staging mode. Orin shares
physical memory, so these counts do not represent traffic over a discrete PCIe
link. Its median client time (9.179 s) was
close to, and slightly slower than, the copied mode's 9.148 s median. This is a
descriptive comparison: direct-only runs followed the earlier randomized
CPU-versus-copy screen, so the difference is not a paired effect estimate. The
run shows the existing Orin mapped alias is usable for this bounded case; it
does not show a speedup. See the [CPU versus copied staging report](../staged-screen/README.md)
for the matched resident-map controls and full methodology. Raw logs, configs,
results and resident maps are retained here.
