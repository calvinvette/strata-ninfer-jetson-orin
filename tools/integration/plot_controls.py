"""Export the exact paired control summaries as PNG/SVG, without filling gaps."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    result = json.loads(args.summary.read_text())
    cells = result['cells']
    args.output.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 4, figsize=(17, 5), constrained_layout=True)
    keys = [('prompt_tps', 'Prompt tokens/s'), ('decode_tps', 'Decode tokens/s'),
            ('client_ttft_s', 'Client TTFT (s)'), ('client_total_s', 'Client total (s)')]
    for axis, (key, title) in zip(axes, keys):
        for offset, variant, color in [(-0.18, 'baseline', '#345995'), (0.18, 'candidate', '#d96c06')]:
            values = [cell[key][variant + '_median'] for cell in cells]
            axis.barh([i + offset for i in range(len(cells))], values, height=0.34,
                      label='Pinned control' if variant == 'baseline' else 'Branch control', color=color)
        axis.set_yticks(range(len(cells)), [f"{cell['cell']} (n={cell['paired_blocks']})" for cell in cells])
        axis.set_title(title)
        axis.grid(axis='x', alpha=0.2)
    axes[0].legend(loc='lower right')
    fig.suptitle('Same-source Orin controls: medians of per-request metrics; dynamic clocks')
    for suffix in ('png', 'svg'):
        fig.savefig(args.output / f'control-medians.{suffix}', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 4, figsize=(17, 5), constrained_layout=True)
    for axis, (key, title) in zip(axes, keys):
        medians = [cell[key]['median_within_block_candidate_over_baseline'] for cell in cells]
        intervals = [cell[key]['paired_bootstrap_95_interval'] for cell in cells]
        axis.errorbar(medians, range(len(cells)),
                      xerr=[[max(0, median - bounds[0]) for median, bounds in zip(medians, intervals)],
                            [max(0, bounds[1] - median) for median, bounds in zip(medians, intervals)]],
                      fmt='o', color='#345995', capsize=4)
        axis.axvline(1, color='gray', linestyle='--')
        axis.set_yticks(range(len(cells)), [f"{cell['cell']} (n={cell['paired_blocks']})" for cell in cells])
        axis.set_title(title)
        axis.set_xlabel('Within-block branch / pinned ratio')
        axis.grid(axis='x', alpha=0.2)
    fig.suptitle('Control stability: paired median ratios and bootstrap intervals; screening only')
    for suffix in ('png', 'svg'):
        fig.savefig(args.output / f'control-paired-ratios.{suffix}', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
