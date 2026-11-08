#!/usr/bin/env python3
"""Fig. 3 — ablation ladder as a dot plot (honest non-zero baseline).
Blue = gpt-4o-mini, orange = claude-haiku-4.5; whiskers = min-max over N runs."""
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.lines import Line2D

mpl.rcParams.update({
    'font.size': 7.5, 'font.family': 'sans-serif',
    'axes.edgecolor': '#999999', 'axes.linewidth': 0.6,
    'xtick.color': '#555555', 'ytick.color': '#333333',
    'pdf.fonttype': 42,
})
BLUE, ORANGE, GRAY = '#4C72B0', '#DD8452', '#AAAAAA'

rows = [
    ('Bare LLM (intent-name list only)', 61.4, None, None, BLUE,   1, 'gpt'),
    ('Bare LLM (intent-name list only)', 78.7, None, None, ORANGE, 1, 'haiku'),
    ('Full catalog, no retrieval',       88.4, 88.3, 88.7, BLUE,   5, 'gpt'),
    ('+ BM25 k=50, production bank',     88.9, 88.6, 89.2, BLUE,   5, 'gpt'),
    ('+ BM25 k=50, legacy bank (LOCO)',  95.35, 95.1, 95.6, BLUE,  2, 'gpt'),
    ('+ BM25 k=50, production bank',     97.4, None, None, ORANGE, 1, 'haiku'),
]
fig, ax = plt.subplots(figsize=(3.45, 2.35), dpi=200)
ys = list(range(len(rows)))[::-1]
for y, (label, v, lo, hi, c, n, m) in zip(ys, rows):
    ax.plot([55.5, v], [y, y], color='#DDDDDD', lw=0.8, zorder=1)
    if lo is not None:
        ax.plot([lo, hi], [y, y], color=c, lw=2.6, alpha=0.45, zorder=2,
                solid_capstyle='butt')
    ax.plot(v, y, 'o', ms=5.5, color=c, mec='white', mew=0.8, zorder=3)
    ntxt = f'{v:.1f}'.rstrip('0').rstrip('.') if v != 95.35 else '95.1–95.6'
    ntxt += f' (N={n})' if n > 1 and v != 95.35 else ''
    ax.text(v + 0.9, y, ntxt, va='center', ha='left', fontsize=6.8,
            color='#222222', zorder=5)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=6.8)
ax.set_xlim(55.5, 111); ax.set_ylim(-0.8, len(rows)-0.25)
ax.set_xticks([60, 70, 80, 90, 100])
ax.set_xlabel('Intent accuracy (%)', fontsize=7.5)
ax.xaxis.grid(True, color='#EDEDED', lw=0.5); ax.set_axisbelow(True)
for s in ('top', 'right', 'left'):
    ax.spines[s].set_visible(False)
ax.tick_params(left=False)
for xv in (86.9, 94.3, 95.3):
    ax.axvline(xv, color=GRAY, lw=0.6, ls=(0, (2, 2)), zorder=0)
ax.text(86.6, -0.68, 'legacy-era ladder (hist.)', fontsize=5.6, color='#999999', ha='right')
leg = ax.legend(handles=[
    Line2D([], [], marker='o', ls='', ms=5, color=BLUE, mec='white', label='gpt-4o-mini'),
    Line2D([], [], marker='o', ls='', ms=5, color=ORANGE, mec='white', label='claude-haiku-4.5')],
    loc='upper right', fontsize=6.4, frameon=True, handletextpad=0.2,
    borderaxespad=0.2)
leg.get_frame().set_facecolor('white'); leg.get_frame().set_edgecolor('none')
leg.get_frame().set_alpha(0.95)
fig.tight_layout(pad=0.3)
fig.savefig('fig_ladder.pdf'); fig.savefig('fig_ladder.png')
print('ok')
