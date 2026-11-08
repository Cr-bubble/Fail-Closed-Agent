#!/usr/bin/env python3
"""Fig. 1 — fail-closed architecture + routing pipeline (double-column width)."""
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

mpl.rcParams.update({'font.size': 6.8, 'font.family': 'sans-serif', 'pdf.fonttype': 42})
ORANGE, BLUE, DBLUE, GRAY, RED = '#F3D9C4', '#D6E4F0', '#B8CFE8', '#EEEEEE', '#C0392B'
EDGE = '#666666'

fig, ax = plt.subplots(figsize=(7.1, 2.55), dpi=200)
ax.set_xlim(0, 10); ax.set_ylim(0, 3.4); ax.axis('off')

def box(x, y, w, h, text, fc, fs=6.6, lw=0.8, ec=EDGE, style='round,pad=0.03'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=fs, zorder=3, linespacing=1.25)

def arrow(p, q, color='#333333', ls='-', lw=1.0, rad=0.0, z=4):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=7,
                 color=color, ls=ls, lw=lw, connectionstyle=f'arc3,rad={rad}', zorder=z))

# ---- top row: routing pipeline
box(0.05, 2.05, 0.95, 0.70, 'NL request\n(lock-step)', 'white')
box(1.45, 2.80, 2.05, 0.52, 'Intent catalog (~80 ops)\nalways complete · cached', GRAY, 6.2)
box(1.45, 1.20, 2.05, 0.52, 'BM25 top-k examples\nadditive only', GRAY, 6.2)
box(1.35, 2.00, 2.25, 0.72, 'LLM (frozen mini)\n1 sentence → 1 intent JSON', ORANGE)
box(3.95, 2.05, 1.30, 0.62, 'Schema\nvalidation', BLUE)
box(5.55, 2.05, 1.45, 0.62, 'Name grounding\n(live netlist)', BLUE)
box(7.30, 2.05, 0.95, 0.62, 'Dispatch', BLUE)
box(8.55, 2.42, 1.40, 0.62, 'Analysis handlers\n(read-only)', BLUE, 6.2)
box(8.55, 0.42, 1.40, 0.62, 'Response\n#RESPONSE/#END', 'white', 6.2)

arrow((1.00, 2.40), (1.35, 2.38))
arrow((2.47, 2.80), (2.47, 2.73))
arrow((2.47, 1.72), (2.47, 1.99))
arrow((3.60, 2.36), (3.95, 2.36))
arrow((5.25, 2.36), (5.55, 2.36))
arrow((7.00, 2.36), (7.30, 2.36))
arrow((8.25, 2.45), (8.55, 2.62))
arrow((9.25, 2.42), (9.25, 1.05))
# corrective feedback (dashed red, curved over the top)
arrow((4.60, 2.67), (2.75, 2.74), color=RED, ls=(0,(3,2)), lw=0.9, rad=0.30)
arrow((6.27, 2.67), (2.95, 2.78), color=RED, ls=(0,(3,2)), lw=0.9, rad=0.36)
ax.text(4.45, 3.22, 'reject reason → one retry / retranslate', fontsize=5.8, color=RED, ha='center')

# ---- bottom row: mutation path with guards
box(5.40, 0.95, 1.60, 0.62, 'Mutation handler\nsnapshot → transform', BLUE, 6.2)
box(3.00, 0.18, 3.10, 0.62, 'Guards: ① register-cut CEC  ② bounds  ③ basis', DBLUE, 6.4)
box(1.30, 0.18, 1.30, 0.62, 'Commit\n(delta ledger)', BLUE, 6.2)
box(0.05, 0.18, 0.95, 0.62, 'Netlist\nstate', 'white')
arrow((7.60, 2.05), (6.95, 1.57), rad=0.2)
arrow((6.20, 0.95), (5.50, 0.80), rad=0.15)
arrow((3.00, 0.49), (2.60, 0.49))
arrow((1.30, 0.49), (1.00, 0.49))
# rollback (dashed red)
arrow((5.20, 0.80), (5.95, 0.93), color=RED, ls=(0,(3,2)), lw=0.9, rad=-0.3)
ax.text(4.55, 0.02, 'any gate fails → rollback to snapshot', fontsize=5.8, color=RED, ha='center')
# live netlist feeds grounding (thin gray up-arrow)
arrow((0.52, 0.80), (6.10, 2.05), color='#AAAAAA', lw=0.7, rad=-0.32, z=1)
ax.text(1.05, 1.02, 'live state', fontsize=5.6, color='#888888', rotation=28)
# fail-closed default
box(7.30, 0.95, 1.05, 0.52, 'safe no-op\n(unchanged)', GRAY, 6.0)
arrow((7.80, 2.05), (7.80, 1.47), color='#888888', ls=(0,(2,2)), lw=0.8)
arrow((8.35, 1.10), (8.55, 0.85), color='#888888', lw=0.8, rad=0.1)
arrow((2.60, 0.80), (8.55, 0.60), color='#333333', lw=0.9, rad=-0.18)

fig.tight_layout(pad=0.2)
fig.savefig('fig_arch.pdf'); fig.savefig('fig_arch.png')
print('ok')
