"""Figures 1-7 of the CASCADE paper.

Figures 1, 2, 6, and 7 are conceptual. Figures 3-5 are drawn from the outputs of
scripts/statistics.py (results/statistics.json) and scripts/agreement.py (results/agreement.json),
so run those first. Requires matplotlib and numpy.

Usage:  python3 scripts/figure_generation.py      (writes PNG files to results/figures/)
"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
OUT = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 8.5, "axes.edgecolor": "#9aa3ad",
                     "axes.labelcolor": "#1d2733", "xtick.color": "#1d2733", "ytick.color": "#1d2733"})
INK, MUTED, GRID = "#1d2733", "#5b6672", "#e3e7ec"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"      # validated categorical slots 1-3
NEUTRAL = "#b8c0c8"
_stats = json.load(open(os.path.join(ROOT, "results", "statistics.json")))
_agree = json.load(open(os.path.join(ROOT, "results", "agreement.json")))
# adapt the script outputs to the structures used below
res = {"systems": {k: dict(v, error=v["errors"], mech=v["mechanisms"]) for k, v in _stats["systems"].items()}}
ci = {s: {f: {"k": round(v.get("fleiss_kappa", v.get("kripp_alpha_interval")), 2), "ci": v["ci95"]}
          for f, v in _agree[s]["fields"].items() if "ci95" in v} for s in ("main", "heldout")}
ORDER = [("AG2 MathChat", "AG2 MathChat\n(two-agent loop)"), ("MetaGPT", "MetaGPT\n(sequential pipeline)"),
         ("ChatDev", "ChatDev\n(chain with review)"), ("AG2 GroupChat + verifier", "AG2 GroupChat\n(group + verifier)"),
         ("AppWorld multi-agent", "AppWorld\n(supervisor star)"), ("Magentic-One", "Magentic-One\n(orchestrator star)"),
         ("HyperAgent", "HyperAgent\n(hierarchy)")]

def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=300, facecolor="white", bbox_inches="tight")
    plt.close(fig)

def box(ax, x, y, w, h, fc="white", ec=INK, lw=1.0, r=1.2, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, zorder=z))

def arrow(ax, x1, y1, x2, y2, color=INK, lw=1.0, ms=8, z=3, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw,
                                 zorder=z, linestyle=ls, connectionstyle=f"arc3,rad={rad}"))

# ---------- Fig. 1: two-axis taxonomy ----------
def fig_taxonomy():
    fig = plt.figure(figsize=(7.0, 4.4)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 63); ax.axis("off")
    ax.text(14, 60.5, "Origin layer\n(where the fault arises)", ha="center", va="center", fontsize=8.8, fontweight="bold", color=INK)
    ax.text(50, 60.5, "Propagation mechanism\n(how the error travels)", ha="center", va="center", fontsize=8.8, fontweight="bold", color=INK)
    ax.text(86, 60.5, "Propagation regime\n(how far it gets)", ha="center", va="center", fontsize=8.8, fontweight="bold", color=INK)
    layers = ["Model (reasoning, knowledge)", "Planning (goals, decomposition)", "Memory and context", "Tool and environment",
              "Communication (hand-off)", "Orchestration (design, control)", "Adversarial input"]
    for i, t in enumerate(layers):
        y = 51 - i * 7.2
        box(ax, 1, y, 26, 5.6, fc="#eef3fa" if i < 6 else "#fdecec", ec=S1 if i < 6 else "#b42318")
        ax.text(14, y + 2.8, t, ha="center", va="center", fontsize=7.6, color=INK)
    mech = [("Relay", "passed on unchanged"), ("Snowball", "later steps build on it"), ("Endorsement", "approved or agreed with"),
            ("Artifact", "via code, files, shared memory"), ("Loop", "re-issued in a cycle"), ("Delegation", "instruction turned into action")]
    for i, (t, d) in enumerate(mech):
        y = 49.5 - i * 8.2
        box(ax, 37, y, 26, 6.6, fc="#fdf0e8", ec=S2)
        ax.text(50, y + 4.3, t, ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
        ax.text(50, y + 1.9, d, ha="center", va="center", fontsize=6.9, color=MUTED)
    reg = [("P0 Contained", "stays with the origin agent"), ("P1 Propagated", "consumed by other agents"),
           ("P2 Amplified", "gains confidence, size, or reach"), ("P3 Emergent", "no single root error")]
    for i, (t, d) in enumerate(reg):
        y = 46 - i * 11
        box(ax, 73, y, 26, 8, fc="#e8f6f0", ec=S3)
        ax.text(86, y + 5.2, t, ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
        ax.text(86, y + 2.4, d, ha="center", va="center", fontsize=6.9, color=MUTED)
    arrow(ax, 27.5, 30, 36.5, 30, lw=1.6, ms=12); arrow(ax, 63.5, 30, 72.5, 30, lw=1.6, ms=12)
    ax.text(50, 0.8, "Every observed error is coded once on each axis; the mechanisms are not exclusive (several may act on one error).",
            ha="center", fontsize=6.9, color=MUTED, style="italic")
    save(fig, "fig1_taxonomy.png")

# ---------- Fig. 2: metrics on a trace graph ----------
def fig_metrics():
    fig = plt.figure(figsize=(7.0, 3.1)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off")
    lanes = ["Planner", "Navigator", "Editor", "Executor"]
    ys = [36, 27, 18, 9]
    for n, y in zip(lanes, ys):
        ax.plot([12, 97], [y, y], color=GRID, lw=1.2, zorder=0)
        ax.text(10.5, y, n, ha="right", va="center", fontsize=8, color=INK)
    ax.text(54, 42.5, "turn  →", ha="center", fontsize=7.5, color=MUTED)
    nodes = [(18, 0, "ok"), (26, 1, "ok"), (33, 0, "root"), (42, 1, "c"), (50, 0, "c"), (58, 2, "c"), (66, 3, "c"), (74, 0, "det"), (82, 2, "c"), (90, 0, "out")]
    pts = []
    for x, li, kind in nodes:
        y = ys[li]; pts.append((x, y))
        if kind == "ok": ax.add_patch(Circle((x, y), 1.6, fc="white", ec=MUTED, lw=1, zorder=3))
        elif kind == "root": ax.add_patch(Circle((x, y), 2.1, fc="#b42318", ec="#b42318", lw=1, zorder=3)); ax.text(x, y + 3.6, "root error\n(origin turn)", ha="center", fontsize=6.8, color="#b42318")
        elif kind == "c": ax.add_patch(Circle((x, y), 1.8, fc=S2, ec="white", lw=1.5, zorder=3))
        elif kind == "det": ax.add_patch(Circle((x, y), 2.0, fc="white", ec=S1, lw=2, zorder=3)); ax.text(x, y + 3.6, "detection", ha="center", fontsize=6.8, color=S1)
        elif kind == "out": ax.add_patch(Circle((x, y), 2.0, fc=S2, ec=INK, lw=1.5, zorder=3)); ax.text(x, y + 3.6, "final output\n(reached)", ha="center", fontsize=6.8, color=INK)
    for a, b in [(2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)]:
        arrow(ax, pts[a][0] + 1.8, pts[a][1], pts[b][0] - 1.8, pts[b][1], color=MUTED, lw=0.9, ms=7, z=2)
    ax.annotate("", xy=(74, 2.5), xytext=(33, 2.5), arrowprops=dict(arrowstyle="<->", color=S1, lw=1))
    ax.text(53.5, 0.6, "detection latency: turns from the root error to the first detection", ha="center", fontsize=6.8, color=S1)
    ax.text(98, 30, "blast radius = 3\n(Navigator, Editor,\nExecutor)\n\nhop depth = 3\n\ncontained: no", ha="left", va="center", fontsize=7, color=INK)
    fig.subplots_adjust(right=0.8)
    save(fig, "fig2_metrics.png")

# ---------- Fig. 3: results by system (regime stack + rates) ----------
def fig_results():
    S = res["systems"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), gridspec_kw=dict(width_ratios=[1.35, 1]))
    ax = axes[0]
    labels = [l for _, l in ORDER]
    for i, (k, _) in enumerate(ORDER):
        r = S[k]["regimes"]; n = sum(v for kk, v in r.items() if kk != "None" and kk is not None)
        p0, p1, p2 = r.get("P0_CONTAINED", 0), r.get("P1_PROPAGATED", 0), r.get("P2_AMPLIFIED", 0)
        y = len(ORDER) - 1 - i; left = 0
        for v, col, nm in [(p0, NEUTRAL, "P0"), (p1, S1, "P1"), (p2, S2, "P2")]:
            if v:
                w = v / n * 100
                ax.barh(y, w - 0.6, left=left + 0.3, color=col, height=0.62, edgecolor="white", linewidth=0)
                if w >= 9: ax.text(left + w / 2, y, str(v), ha="center", va="center", fontsize=7, color="white" if col != NEUTRAL else INK)
                left += w
        ax.text(101.5, y, f"n = {n}", va="center", fontsize=7, color=MUTED)
    ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(labels[::-1], fontsize=7)
    ax.set_xlim(0, 100); ax.set_xlabel("Share of coded errors (%)", fontsize=7.5)
    ax.spines[["top", "right"]].set_visible(False); ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=NEUTRAL, label="P0 contained"), Patch(color=S1, label="P1 propagated"), Patch(color=S2, label="P2 amplified")],
              ncol=3, fontsize=6.8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    ax.set_title("(a) Propagation regime of the root error", fontsize=8.2, loc="left", pad=22)
    ax = axes[1]
    for i, (k, _) in enumerate(ORDER):
        d = S[k]; y = len(ORDER) - 1 - i
        det = d["detected"][0] / d["detected"][1] * 100 if d["detected"][1] else 0
        cor = d["corrected"][0] / d["corrected"][1] * 100 if d["corrected"][1] else 0
        ax.plot([0, 100], [y, y], color=GRID, lw=0.8, zorder=0)
        ax.plot([cor, det], [y, y], color=MUTED, lw=1.2, zorder=1)
        ax.scatter(det, y, s=34, color=S1, zorder=3, edgecolor="white", linewidth=1)
        ax.scatter(cor, y, s=34, color=S2, marker="D", zorder=3, edgecolor="white", linewidth=1)
    ax.set_yticks(range(len(ORDER))); ax.set_yticklabels([])
    ax.set_xlim(-4, 104); ax.set_xlabel("Share of coded errors (%)", fontsize=7.5)
    ax.spines[["top", "right", "left"]].set_visible(False); ax.tick_params(axis="y", length=0)
    ax.scatter([], [], s=34, color=S1, label="detected by an agent"); ax.scatter([], [], s=34, color=S2, marker="D", label="corrected before output")
    ax.legend(fontsize=6.8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=2)
    ax.set_title("(b) Detection and correction", fontsize=8.2, loc="left", pad=22)
    fig.tight_layout()
    save(fig, "fig3_results.png")

# ---------- Fig. 4: mechanism heatmap ----------
def fig_mech():
    S = res["systems"]; M = ["SNOWBALL", "RELAY", "DELEGATION", "ARTIFACT", "LOOP", "ENDORSEMENT"]
    rows = [(l.replace("\n", " "), [S[k]["mech"][m] / S[k]["error"] * 100 if S[k]["error"] else 0 for m in M], S[k]["error"]) for k, l in ORDER]
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", ["#f4f8fd", "#9ec5ef", "#2a78d6", "#123f78"])
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    A = np.array([r[1] for r in rows])
    ax.imshow(A, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(A.shape[0]):
        for j in range(A.shape[1]):
            v = A[i, j]; ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if v > 55 else INK)
    ax.set_xticks(range(len(M))); ax.set_xticklabels([m.capitalize() for m in M], fontsize=7.5)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([f"{r[0]}  (n={r[2]})" for r in rows], fontsize=7)
    ax.set_xticks([x - 0.5 for x in range(1, len(M))], minor=True); ax.set_yticks([y - 0.5 for y in range(1, len(rows))], minor=True)
    ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="both", length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("Share of coded errors (%) in which each mechanism acted (majority of three coders)", fontsize=8, loc="left")
    fig.tight_layout(); save(fig, "fig4_mechanisms.png")

# ---------- Fig. 5: agreement main vs held-out ----------
def fig_agree():
    F = [("error_present", "Error present"), ("outcome", "Task outcome"), ("hop_depth", "Hop depth (α)"), ("blast_radius", "Blast radius (α)"),
         ("detected", "Detected"), ("propagated", "Propagated"), ("regime", "Regime (P0–P2)"), ("corrected", "Corrected"),
         ("reached_output", "Reached output"), ("target", "Conflict target"), ("origin_layer", "Origin layer")]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for i, (f, lab) in enumerate(F):
        y = len(F) - 1 - i
        for nm, col, dy, mk in [("main", S1, 0.16, "o"), ("heldout", S2, -0.16, "D")]:
            k = ci[nm][f]["k"]; lo, hi = ci[nm][f]["ci"]
            ax.plot([lo, hi], [y + dy, y + dy], color=col, lw=1.4, alpha=0.8)
            ax.scatter(k, y + dy, color=col, marker=mk, s=26, zorder=3, edgecolor="white", linewidth=0.8)
    ax.axvline(0.7, color=MUTED, ls=(0, (3, 2)), lw=0.9); ax.text(0.705, len(F) - 0.45, "0.70 target", fontsize=6.8, color=MUTED)
    ax.set_yticks(range(len(F))); ax.set_yticklabels([l for _, l in F][::-1], fontsize=7.4)
    ax.set_xlim(-0.1, 1.02); ax.set_xlabel("Fleiss κ (Krippendorff α for counts) with 95% bootstrap interval", fontsize=7.4)
    ax.spines[["top", "right"]].set_visible(False); ax.xaxis.grid(True, color=GRID); ax.set_axisbelow(True)
    ax.scatter([], [], color=S1, marker="o", label="Main sample, codebook v1.1 (136 traces)")
    ax.scatter([], [], color=S2, marker="D", label="Held-out sample, codebook v1.2 (35 traces)")
    ax.legend(fontsize=6.8, frameon=False, loc="lower left")
    fig.tight_layout(); save(fig, "fig5_agreement.png")

# ---------- Fig. 6: mitigation gap matrix ----------
def fig_gaps():
    M = ["Relay", "Snowball", "Endorsement", "Artifact", "Loop", "Delegation", "Adversarial\nspread"]
    stages = ["Prevent", "Detect", "Contain", "Attribute"]
    # 2 = several evaluated techniques; 1 = one or few, or only proposed; 0 = gap (none found)
    G = [[1, 1, 1, 2], [1, 2, 0, 2], [2, 1, 0, 1], [1, 1, 0, 1], [1, 1, 1, 1], [2, 1, 1, 1], [2, 2, 2, 1]]
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    cols = {2: "#2a78d6", 1: "#9ec5ef", 0: "#ffffff"}
    for i, row in enumerate(G):
        for j, v in enumerate(row):
            y = len(G) - 1 - i
            ax.add_patch(FancyBboxPatch((j + 0.06, y + 0.08), 0.88, 0.84, boxstyle="round,pad=0,rounding_size=0.08",
                                        fc=cols[v], ec="#9aa3ad" if v == 0 else "white", lw=1, ls=(0, (2, 2)) if v == 0 else "-"))
            ax.text(j + 0.5, y + 0.5, {2: "●", 1: "◐", 0: "gap"}[v], ha="center", va="center", fontsize=8 if v else 7,
                    color="white" if v == 2 else (INK if v == 1 else "#b42318"))
    ax.set_xlim(0, len(stages)); ax.set_ylim(0, len(G))
    ax.set_xticks([j + 0.5 for j in range(len(stages))]); ax.set_xticklabels(stages, fontsize=7.8); ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(G))]); ax.set_yticklabels(M[::-1], fontsize=7.6)
    ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.text(0, -0.55, "●  several evaluated techniques    ◐  one or few, or proposed only    gap  none found in the reviewed literature",
            fontsize=6.6, color=MUTED, transform=ax.transData)
    fig.tight_layout(); save(fig, "fig6_gaps.png")

# ---------- Fig. 7: topology archetypes ----------
def fig_topology():
    fig = plt.figure(figsize=(7.0, 2.5)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 36); ax.axis("off")
    def node(x, y, c=S1, r=1.9): ax.add_patch(Circle((x, y), r, fc=c, ec="white", lw=1.5, zorder=3))
    def e(a, b, both=False):
        arrow(ax, a[0], a[1], b[0], b[1], color=MUTED, lw=0.9, ms=6, z=2)
    titles = [(10, "Chain / pipeline"), (30, "Chain with review"), (50, "Star (supervisor)"), (70, "Hierarchy"), (90, "Group / debate")]
    for x, t in titles: ax.text(x, 33, t, ha="center", fontsize=8, fontweight="bold", color=INK)
    # chain
    p = [(10, 26), (10, 19), (10, 12)]; [node(*q) for q in p]; e((10, 24), (10, 21)); e((10, 17), (10, 14))
    # chain with review
    p = [(27, 26), (27, 19), (27, 12)]; [node(*q) for q in p]; e((27, 24), (27, 21)); e((27, 17), (27, 14))
    node(34, 19, c=S3); arrow(ax, 29, 19.6, 32, 19.6, color=MUTED, lw=0.9, ms=6); arrow(ax, 32, 18.4, 29, 18.4, color=S3, lw=0.9, ms=6)
    # star
    c = (50, 19); node(*c, c=S2, r=2.3)
    for q in [(43, 26), (57, 26), (43, 12), (57, 12)]: node(*q); e(c, q)
    # hierarchy
    top = (70, 26); node(*top, c=S2, r=2.3)
    for q in [(64, 18), (70, 18), (76, 18)]: node(*q); e(top, q)
    node(64, 11); e((64, 16), (64, 13))
    # group
    pts = [(85, 24), (95, 24), (85, 13), (95, 13)]
    [node(*q) for q in pts]
    for i in range(4):
        for j in range(i + 1, 4):
            ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]], color=MUTED, lw=0.8, zorder=1)
    notes = [(10, "errors relayed forward;\nno one looks back"), (30, "reviewer can catch,\nor endorse, the error"),
             (50, "hub relays and\ndelegates errors"), (70, "planner errors are\ndelegated downward"), (90, "agreement can amplify\nshared errors")]
    for x, t in notes: ax.text(x, 4.5, t, ha="center", va="center", fontsize=6.8, color=MUTED)
    save(fig, "fig7_topologies.png")

if __name__ == "__main__":
    fig_taxonomy(); fig_metrics(); fig_results(); fig_mech(); fig_agree(); fig_gaps(); fig_topology()
