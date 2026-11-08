#!/usr/bin/env python3
"""Fig. 1 — two panels: (a) routing pipeline, (b) execution & commit discipline.
Grid-aligned boxes; horizontal/vertical arrows only; one dashed style per meaning."""
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

mpl.rcParams.update({'font.size': 6.8, 'font.family': 'sans-serif', 'pdf.fonttype': 42})
ORANGE, BLUE, DBLUE, GRAY = '#F5DCC8', '#DCE8F4', '#C3D6EC', '#F0F0F0'
EDGE, RED, GY = '#777777', '#C0392B', '#999999'

fig, ax = plt.subplots(figsize=(7.1, 2.5), dpi=200)
ax.set_xlim(0, 10); ax.set_ylim(0, 3.55); ax.axis('off')

def box(x, y, w, h, text, fc, fs=6.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.03',
                                fc=fc, ec=EDGE, lw=0.8, zorder=2))
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=fs,
            zorder=3, linespacing=1.3)

def arr(p, q, color='#333333', ls='-', lw=1.0, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=7,
                 color=color, ls=ls, lw=lw, connectionstyle=f'arc3,rad={rad}', zorder=4))

def elbow(p, mid, q, color='#333333', lw=1.0):
    ax.plot([p[0], mid[0]], [p[1], mid[1]], color=color, lw=lw, zorder=4,
            solid_capstyle='round')
    arr(mid, q, color=color, lw=lw)

# ---------- panel titles & divider ----------
ax.text(0.25, 3.32, '(a) Routing pipeline', fontsize=7.2, fontweight='bold')
ax.text(5.55, 3.32, '(b) Execution and commit discipline', fontsize=7.2, fontweight='bold')
ax.plot([5.33, 5.33], [0.2, 3.25], color='#DDDDDD', lw=0.8)

# ---------- panel (a) ----------
box(0.45, 2.50, 1.40, 0.70, 'Intent catalog\n(~80 ops, complete,\ncached)', GRAY, 5.9)
box(2.00, 2.50, 1.40, 0.70, 'BM25 top-k\nexamples\n(additive only)', GRAY, 5.9)
box(0.70, 1.40, 1.60, 0.65, '① Translate\nLLM (frozen mini)', ORANGE)
box(2.65, 1.40, 1.15, 0.65, '② Schema\nvalidation', BLUE)
box(4.05, 1.40, 1.15, 0.65, '③ Ground names\n(live netlist)', BLUE, 6.1)
box(2.05, 0.40, 2.55, 0.55, 'fail-closed default: safe no-op (design unchanged)', GRAY, 6.0)

ax.text(0.08, 1.93, 'NL request', fontsize=5.9, color='#444444')
arr((0.10, 1.72), (0.70, 1.72))
arr((1.15, 2.50), (1.30, 2.06))                      # catalog -> translate
arr((2.70, 2.50), (2.15, 2.06))                      # examples -> translate
arr((2.30, 1.72), (2.65, 1.72))
arr((3.80, 1.72), (4.05, 1.72))
arr((5.20, 1.72), (5.63, 1.72))                      # -> dispatch (panel b)
arr((3.22, 2.05), (2.15, 2.12), color=RED, ls=(0, (3, 2)), lw=0.9, rad=0.32)
arr((4.62, 2.05), (2.30, 2.16), color=RED, ls=(0, (3, 2)), lw=0.9, rad=0.30)
ax.text(4.42, 2.56, 'reject reason → one retry', fontsize=5.7, color=RED, ha='center')
arr((3.22, 1.40), (3.22, 0.95), color=GY, ls=(0, (2, 2)), lw=0.8)
arr((4.62, 1.40), (4.40, 0.95), color=GY, ls=(0, (2, 2)), lw=0.8)

# ---------- panel (b) ----------
box(5.63, 1.40, 0.95, 0.65, '④ Dispatch', BLUE)
box(6.95, 2.45, 1.60, 0.60, 'Analysis handlers\n(read-only)', BLUE, 6.1)
box(6.95, 1.40, 1.60, 0.65, 'Snapshot →\ntransform', BLUE, 6.1)
box(8.78, 1.40, 1.12, 0.65, 'Guards: CEC ·\nbounds · basis', DBLUE, 5.9)
box(8.78, 0.40, 1.12, 0.60, 'Commit\n(delta ledger)', BLUE, 6.0)
box(6.95, 0.40, 1.60, 0.60, 'Persistent\nnetlist state', 'white', 6.1)

elbow((6.10, 2.05), (6.10, 2.75), (6.95, 2.75))      # dispatch -> analysis
arr((6.58, 1.72), (6.95, 1.72))                      # dispatch -> mutation
arr((8.55, 1.72), (8.78, 1.72))                      # transform -> guards
arr((9.34, 1.40), (9.34, 1.00))                      # guards -pass-> commit
ax.text(9.42, 1.18, 'pass', fontsize=5.7, color='#444444')
arr((8.78, 0.70), (8.55, 0.70))                      # commit -> state
arr((8.90, 2.05), (7.90, 2.12), color=RED, ls=(0, (3, 2)), lw=0.9, rad=0.30)
ax.text(8.45, 2.26, 'fail → rollback', fontsize=5.7, color=RED, ha='center')
arr((8.55, 2.75), (9.90, 2.75))                      # analysis reply
ax.text(9.55, 2.84, 'reply', fontsize=5.7, color='#444444')

fig.tight_layout(pad=0.2)
fig.savefig('fig_arch.pdf'); fig.savefig('fig_arch.png')
print('ok')
