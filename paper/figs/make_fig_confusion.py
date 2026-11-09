#!/usr/bin/env python3
"""Most frequent intent confusions with the full catalog (no retrieval).

Reads the per-sentence routing results of the final-configuration runs and
plots the top-5 wrong-operation pairs per model as mean misroutes per run.
Give-ups (no intent) are excluded from the pairs.
"""
import collections
import glob
import json
import os

import matplotlib as mpl
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, '..', '..', 'paper_exp')
RUNS = [
    ('GPT-4o-mini', 'e4_variance/gpt_catalog_run*.jsonl', '#4C72B0'),
    ('Claude Haiku 4.5', 'e16_routing_supplement/haiku_catalog_run*.jsonl', '#DD8452'),
]
TOP = 5

mpl.rcParams.update({
    'font.family': 'serif', 'font.serif': ['STIXGeneral', 'DejaVu Serif'],
    'mathtext.fontset': 'stix', 'font.size': 7, 'pdf.fonttype': 42,
    'axes.edgecolor': '#999999', 'axes.linewidth': 0.5,
    'xtick.color': '#444444', 'ytick.color': '#222222',
    'xtick.major.width': 0.5, 'ytick.major.width': 0,
})


def confusions(pattern):
    files = sorted(glob.glob(os.path.join(EXP, pattern)))
    pairs = collections.Counter()
    for f in files:
        for line in open(f):
            r = json.loads(line)
            pred = r.get('pred')
            if pred and pred != 'noop' and pred != r['op']:
                pairs[(r['op'], pred)] += 1
    return pairs, len(files)


fig, axes = plt.subplots(2, 1, figsize=(3.45, 2.42), dpi=200)
for ax, (title, pattern, color) in zip(axes, RUNS):
    pairs, n_runs = confusions(pattern)
    top = pairs.most_common(TOP)
    share = 100 * sum(k for _, k in top) / sum(pairs.values())
    print(f'{title}: top-{TOP} share {share:.0f}% of {sum(pairs.values())} misroutes')
    labels = [f'{t} → {p}' for (t, p), _ in top][::-1]
    vals = [k / n_runs for _, k in top][::-1]
    ys = range(len(vals))
    ax.barh(ys, vals, height=0.62, color=color, edgecolor='white', linewidth=0.6, zorder=3)
    for y, v in zip(ys, vals):
        ax.text(v + 0.15, y, f'{v:.1f}', va='center', ha='left', fontsize=6.5, color='#222222')
    ax.set_yticks(list(ys))
    ax.set_yticklabels(labels, fontfamily='DejaVu Sans Mono', fontsize=5.8)
    ax.set_title(f'{title} ({n_runs} runs)', fontsize=7, loc='left', pad=3)
    ax.set_xlim(0, 13)
    ax.xaxis.grid(True, color='#E6E6E6', lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis='x', labelsize=6.5, length=2)
axes[-1].set_xlabel('Misroutes per run', fontsize=6.8)
fig.tight_layout(pad=0.3, h_pad=0.6)
fig.savefig(os.path.join(HERE, 'fig_confusion.pdf'))
fig.savefig(os.path.join(HERE, 'fig_confusion.png'))
print('wrote fig_confusion.pdf / .png')
