#!/usr/bin/env python3
"""Fig. 1 — two panels, TikZ-style auto-fitted nodes (box drawn around measured
text, so text can never overflow). Arrows anchor to measured box edges."""
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

mpl.rcParams.update({'font.size': 6.8, 'font.family': 'sans-serif', 'pdf.fonttype': 42})
ORANGE, BLUE, DBLUE, GRAY = '#F5DCC8', '#DCE8F4', '#C3D6EC', '#F0F0F0'
EDGE, RED, GY = '#777777', '#C0392B', '#999999'

fig, ax = plt.subplots(figsize=(7.1, 2.5), dpi=200)
ax.set_xlim(0, 10); ax.set_ylim(0, 3.55); ax.axis('off')
fig.canvas.draw()
REN = fig.canvas.get_renderer()

class Node:
    def __init__(self, cx, cy, text, fc, fs=6.4, padx=0.10, pady=0.07):
        t = ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
                    zorder=3, linespacing=1.3)
        bb = t.get_window_extent(renderer=REN).transformed(ax.transData.inverted())
        self.x0, self.x1 = bb.x0 - padx, bb.x1 + padx
        self.y0, self.y1 = bb.y0 - pady, bb.y1 + pady
        ax.add_patch(FancyBboxPatch((self.x0, self.y0), self.x1-self.x0,
                     self.y1-self.y0, boxstyle='round,pad=0.03',
                     fc=fc, ec=EDGE, lw=0.8, zorder=2))
    @property
    def cx(self): return (self.x0+self.x1)/2
    @property
    def cy(self): return (self.y0+self.y1)/2
    def L(self, dy=0): return (self.x0-0.03, self.cy+dy)
    def R(self, dy=0): return (self.x1+0.03, self.cy+dy)
    def T(self, dx=0): return (self.cx+dx, self.y1+0.03)
    def B(self, dx=0): return (self.cx+dx, self.y0-0.03)

def arr(p, q, color='#333333', ls='-', lw=1.0, rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=7,
                 color=color, ls=ls, lw=lw, connectionstyle=f'arc3,rad={rad}', zorder=4))

def elbow(p, mid, q, color='#333333', lw=1.0):
    ax.plot([p[0], mid[0]], [p[1], mid[1]], color=color, lw=lw, zorder=4)
    arr(mid, q, color=color, lw=lw)

ax.text(0.25, 3.32, '(a) Routing pipeline', fontsize=7.2, fontweight='bold')
ax.text(5.65, 3.32, '(b) Execution and commit discipline', fontsize=7.2, fontweight='bold')
ax.plot([5.45, 5.45], [0.2, 3.25], color='#DDDDDD', lw=0.8)

# ---- panel (a)
cat = Node(1.15, 2.80, 'Intent catalog\n~80 ops · complete · cached', GRAY, 5.9)
ex  = Node(3.30, 2.80, 'BM25 top-k examples\n(additive only)', GRAY, 5.9)
tr  = Node(1.45, 1.72, '① Translate\nLLM (frozen mini)', ORANGE)
sc  = Node(3.25, 1.72, '② Schema\nvalidation', BLUE)
gr  = Node(4.70, 1.72, '③ Ground names\n(live netlist)', BLUE, 6.1)
no  = Node(3.10, 0.55, 'fail-closed default:\nsafe no-op (design unchanged)', GRAY, 5.9)

ax.text(0.06, 1.95, 'NL request', fontsize=5.9, color='#444444')
arr((0.08, 1.72), tr.L())
arr(cat.B(), tr.T(-0.45))
arr(ex.B(-0.6), tr.T(0.0))
arr(tr.R(), sc.L()); arr(sc.R(), gr.L())
arr(gr.R(), (5.72, 1.72))
arr(sc.T(), tr.T(0.45), color=RED, ls=(0, (3, 2)), lw=0.9, rad=0.35)
arr(gr.T(), tr.T(0.58), color=RED, ls=(0, (3, 2)), lw=0.9, rad=0.30)
ax.text(4.95, 2.47, 'reject reason → one retry', fontsize=5.7, color=RED, ha='center')
arr(sc.B(), no.T(-0.4), color=GY, ls=(0, (2, 2)), lw=0.8)
arr(gr.B(), no.T(0.9), color=GY, ls=(0, (2, 2)), lw=0.8)

# ---- panel (b)
dp = Node(6.15, 1.72, '④ Dispatch', BLUE)
an = Node(7.90, 2.78, 'Analysis handlers\n(read-only)', BLUE, 6.1)
mu = Node(7.72, 1.72, 'Snapshot →\ntransform', BLUE, 6.1)
gd = Node(9.20, 1.72, 'Guards: CEC ·\nbounds · basis', DBLUE, 5.9)
cm = Node(9.22, 0.62, 'Commit\n(delta ledger)', BLUE, 6.0)
st = Node(7.90, 0.62, 'Persistent\nnetlist state', 'white', 6.1)

elbow(dp.T(), (dp.cx, an.cy), an.L())
arr(dp.R(), mu.L())
arr(mu.R(), gd.L())
arr(gd.B(), cm.T())
ax.text(gd.cx+0.12, (gd.y0+cm.y1)/2, 'pass', fontsize=5.7, color='#444444')
arr(cm.L(), st.R())
arr(gd.T(), mu.T(0.3), color=RED, ls=(0, (3, 2)), lw=0.9, rad=0.30)
ax.text(8.62, 2.33, 'fail → rollback', fontsize=5.7, color=RED, ha='center')
arr(an.R(), (9.95, an.cy))
ax.text(9.58, an.cy+0.10, 'reply', fontsize=5.7, color='#444444')

fig.tight_layout(pad=0.2)
fig.savefig('fig_arch.pdf'); fig.savefig('fig_arch.png')
print('ok')
