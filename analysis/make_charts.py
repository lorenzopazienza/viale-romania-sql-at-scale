"""Draws the charts in docs/img/ from the JSON files in results/."""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
IMG = os.path.join(ROOT, "docs", "img")

INK, BODY, MUTED, GRID = "#15181D", "#4A5059", "#6A7079", "#E3E5E8"
SLOW, FAST, NEUTRAL = "#D93D42", "#008C7A", "#5A606A"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": BODY, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 14,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})


def load(name):
    with open(os.path.join(RES, name)) as f:
        return json.load(f)


def fmt_ms(v, _=None):
    """Axis ticks: 10 ms, 1 s, ..."""
    if v >= 1000:
        return f"{v / 1000:g} s"
    return f"{v:g} ms"


def label_ms(v):
    """Value labels: 3 significant figures."""
    if v >= 1000:
        return f"{v / 1000:.1f} s"
    if v >= 100:
        return f"{v:.0f} ms"
    return f"{v:.1f} ms"


def fmt_rows(v, _=None):
    return {1e4: "10k", 1e5: "100k", 1e6: "1M", 1e7: "10M"}.get(v, f"{v:,.0f}")


def save(fig, name):
    os.makedirs(IMG, exist_ok=True)
    fig.savefig(os.path.join(IMG, name))
    plt.close(fig)
    print("saved docs/img/" + name)


def scaling():
    data = load("exp4_scaling.json")
    x = [r["rows"] for r in data]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for key, color, label in (("ghost_noidx_ms", SLOW, "no index (full table scan)"),
                              ("ghost_idx_ms", FAST, "index on (location, access_date, entry_time)")):
        y = [r[key] for r in data]
        ax.plot(x, y, color=color, lw=2, marker="o", ms=7, mec="white", mew=2, label=label)
        ax.annotate(label_ms(y[-1]), (x[-1], y[-1]), xytext=(10, 0), textcoords="offset points",
                    va="center", color=INK, fontsize=11)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_rows))
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_ms))
    ax.set_xticks([1e4, 1e5, 1e6, 1e7])
    ax.set_xlim(7e3, 2.2e7)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_xlabel("rows in access_log")
    ax.set_title("Step 3 (ghost badge): query time vs table size")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "scaling_ghost.png")


def case_query():
    big = [r for r in load("exp4_scaling.json") if r["db"] == "big_10m"][0]
    bars = [("Course version: EXCEPT (step 10)", big["except_idx_ms"], FAST),
            ("Whole case in one CTE query", big["case_idx_ms"], SLOW),
            ("Same query, LIMIT 1 in crime_window", big["case_fixed_idx_ms"], FAST)]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    labels = [b[0] for b in bars][::-1]
    vals = [b[1] for b in bars][::-1]
    cols = [b[2] for b in bars][::-1]
    ax.barh(labels, vals, color=cols, height=0.55)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_ms))
    for i, v in enumerate(vals):
        ax.text(v * 1.15, i, label_ms(v), va="center", color=INK)
    ax.set_xlim(right=max(vals) * 8)
    ax.grid(axis="x", color=GRID, lw=1)
    ax.set_title("10M rows, index in place: the elegant query is the slow one")
    ax.tick_params(axis="y", colors=INK, length=0)
    save(fig, "case_query.png")


def correlated():
    data = load("exp5_correlated_vs_window.json")
    x = [r["grades"] for r in data]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    series = (("correlated_ms", SLOW, "correlated subquery"),
              ("correlated_idx_ms", NEUTRAL, "correlated subquery + index (course_id, grade)"),
              ("window_ms", FAST, "RANK() OVER (PARTITION BY course_id)"))
    for key, color, label in series:
        pts = [(xi, r[key]) for xi, r in zip(x, data) if r[key] is not None]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=2, marker="o", ms=7,
                mec="white", mew=2, label=label)
        stopped = [xi for xi, r in zip(x, data) if r[key] is None]
        if stopped:
            ax.plot(stopped, [60000] * len(stopped), ls="none", marker="x", ms=9, mew=2, color=color)
    ax.axhline(60000, color=MUTED, lw=1, ls="--")
    ax.text(x[0], 60000 * 1.3, "stopped at 60 s", color=MUTED, fontsize=10)
    ax.text(x[2], 60000 * 1.3, "both correlated versions stopped", color=MUTED, fontsize=10, ha="center")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_ms))
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_xlabel("rows in grades")
    ax.set_title("Step 8: lowest grade per course")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=10)
    save(fig, "correlated_vs_window.png")


def index_design():
    data = load("exp6_index_design.json")
    base = data[0]["ghost_ms"]
    labels = [r["index"] for r in data][::-1]
    vals = [r["ghost_ms"] for r in data][::-1]
    cols = [FAST if v < base / 10 else SLOW for v in vals]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.barh(labels, vals, color=cols, height=0.55)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_ms))
    for i, r in enumerate(data[::-1]):
        ax.text(r["ghost_ms"] * 1.15, i, f"{label_ms(r['ghost_ms'])} · reads {r['ghost_rows_read']:,} rows",
                va="center", color=INK, fontsize=10)
    ax.set_xlim(right=max(vals) * 60)
    ax.grid(axis="x", color=GRID, lw=1)
    ax.tick_params(axis="y", colors=INK, length=0, labelsize=10)
    ax.set_title("Step 3 at 10M rows, one index at a time (red: no better than a scan)")
    save(fig, "index_design.png")


def anti_joins():
    data = load("exp7_anti_joins.json")["variants"]
    labels = [r["variant"] for r in data][::-1]
    vals = [r["ms"] for r in data][::-1]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.barh(labels, vals, color=[NEUTRAL] * len(vals), height=0.55)
    for i, r in enumerate(data[::-1]):
        ax.text(r["ms"] * 1.02, i, f"{r['ms'] / 1000:.1f} s · {r['rows']:,} rows", va="center",
                color=INK, fontsize=10)
    ax.set_xlim(right=max(vals) * 1.45)
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_ms))
    ax.grid(axis="x", color=GRID, lw=1)
    ax.tick_params(axis="y", colors=INK, length=0)
    ax.set_title("All unregistered swipes in 10M rows, four ways")
    save(fig, "anti_joins.png")


def trigger_cost():
    data = load("exp8_trigger_cost.json")
    labels = {"plain": "no check", "fk": "FOREIGN KEY", "trigger": "trigger + alert table"}
    rows = data["variants"]
    fig, ax = plt.subplots(figsize=(8, 2.8))
    names = [labels[r["variant"]] for r in rows][::-1]
    vals = [r["rows_per_s"] for r in rows][::-1]
    ax.barh(names, vals, color=NEUTRAL, height=0.55)
    for i, v in enumerate(vals):
        ax.text(v * 1.01, i, f"{v:,.0f} rows/s", va="center", color=INK, fontsize=10)
    ax.set_xlim(right=max(vals) * 1.3)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:g}k"))
    ax.grid(axis="x", color=GRID, lw=1)
    ax.tick_params(axis="y", colors=INK, length=0)
    ax.set_title(f"Insert throughput, {data['rows_inserted']:,} swipes")
    save(fig, "trigger_cost.png")


if __name__ == "__main__":
    scaling()
    case_query()
    correlated()
    index_design()
    anti_joins()
    trigger_cost()
