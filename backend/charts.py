import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import numpy as np
from schema import GeojitReportData

TEAL   = "#00A1C6"
ORANGE = "#F26522"
BLUE   = "#004B87"
GREY   = "#888888"
YEARS  = ["FY23A", "FY24A", "FY25A", "FY26E", "FY27E"]


def _v(s):
    try:
        return float(str(s).replace(",", "").replace("%", "")
                     .replace("(", "-").replace(")", "").strip())
    except Exception:
        return 0.0


def _find(rows, *keys):
    for key in keys:
        for r in rows:
            if key.lower() in r.metric.lower():
                return r
    return None


def _bar_line(labels, bar_vals, line_vals, bar_label, line_label,
              title, path, bar_color=TEAL, line_color=ORANGE):
    """Bar + line combo chart styled to match Geojit sample."""
    fig, ax1 = plt.subplots(figsize=(4.0, 2.55))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("white")

    x = np.arange(len(labels))
    w = 0.52
    bars = ax1.bar(x, bar_vals, width=w, color=bar_color, zorder=3, alpha=0.88)

    max_bar = max(abs(v) for v in bar_vals) if bar_vals else 1
    for bar in bars:
        h = bar.get_height()
        if h != 0:
            label_txt = f"{h:,.0f}" if abs(h) >= 10 else f"{h:.1f}"
            y_pos = h + max_bar * 0.015 if h >= 0 else h - max_bar * 0.05
            ax1.text(bar.get_x() + bar.get_width() / 2, y_pos,
                     label_txt, ha="center", va="bottom", fontsize=4.5, color=GREY)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=5.5, rotation=0)
    ax1.tick_params(axis="y", labelsize=5.5, colors=TEAL)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_color(TEAL)
    ax1.yaxis.label.set_color(TEAL)
    ax1.set_ylabel(bar_label, fontsize=5.5, color=TEAL)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax1.axhline(0, color=GREY, linewidth=0.5)

    ax2 = ax1.twinx()
    ax2.plot(x, line_vals, color=line_color, linewidth=1.4,
             marker="o", markersize=2.5, zorder=4)
    max_line = max(abs(v) for v in line_vals) if line_vals else 1
    for xi, yi in zip(x, line_vals):
        offset = max_line * 0.07 if yi >= 0 else -max_line * 0.09
        ax2.text(xi, yi + offset, f"{yi:.1f}%",
                 ha="center", va="bottom", fontsize=4.5, color=line_color)
    ax2.tick_params(axis="y", labelsize=5.5, colors=line_color)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color(line_color)
    ax2.set_ylabel(line_label, fontsize=5.5, color=line_color)

    legend_elems = [
        mpatches.Patch(facecolor=bar_color, label=bar_label),
        Line2D([0], [0], color=line_color, linewidth=1.4, label=line_label),
    ]
    ax1.legend(handles=legend_elems, fontsize=4.5, loc="upper left",
               frameon=False, ncol=2)

    plt.title(title, fontsize=6.5, fontweight="bold", color="#333333", pad=3)
    plt.tight_layout(pad=0.4)
    plt.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()


def generate_charts(data: GeojitReportData, output_dir: str = "temp_charts") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    IS = data.financials.income_statement
    RT = data.financials.ratios

    # ── Chart 1: Revenue (bar) + YoY Growth% (line) ──────────────────────────
    rev = _find(IS, "Sales", "Revenue", "Net interest income")
    if rev:
        vals = [_v(rev.fy23a), _v(rev.fy24a), _v(rev.fy25a), _v(rev.fy26e), _v(rev.fy27e)]
        growths = [0.0]
        for i in range(1, len(vals)):
            g = ((vals[i] - vals[i-1]) / abs(vals[i-1]) * 100) if vals[i-1] else 0.0
            growths.append(round(g, 1))
        p = os.path.join(output_dir, "revenue.png")
        try:
            _bar_line(YEARS, vals, growths,
                      "Revenue (Rs.cr)", "Growth (YoY%)", "Revenue", p)
            paths["revenue"] = p
        except Exception as e:
            print(f"Revenue chart error: {e}")

    # ── Chart 2: Gross Order Value / NII / similar (bar) + Growth% (line) ────
    gov = _find(IS, "Gross Order", "Core operating profit", "Non-interest income", "Fee income")
    if gov:
        gv = [_v(gov.fy23a), _v(gov.fy24a), _v(gov.fy25a), _v(gov.fy26e), _v(gov.fy27e)]
        grw = [0.0]
        for i in range(1, len(gv)):
            g = ((gv[i] - gv[i-1]) / abs(gv[i-1]) * 100) if gv[i-1] else 0.0
            grw.append(round(g, 1))
        p = os.path.join(output_dir, "gov.png")
        try:
            _bar_line(YEARS, gv, grw,
                      f"{gov.metric[:18]} (Rs.cr)", "Growth (%)",
                      gov.metric[:22], p, "#5BA3C9", ORANGE)
            paths["gov"] = p
        except Exception as e:
            print(f"GOV chart error: {e}")

    # ── Chart 3: EBITDA (bar) + EBITDA Margin% (line) ────────────────────────
    ebitda  = _find(IS, "EBITDA")
    e_margin = _find(RT, "EBITDA margin") or _find(IS, "EBITDA Margin")
    if ebitda:
        ev = [_v(ebitda.fy23a), _v(ebitda.fy24a), _v(ebitda.fy25a),
              _v(ebitda.fy26e), _v(ebitda.fy27e)]
        mv = ([_v(e_margin.fy23a), _v(e_margin.fy24a), _v(e_margin.fy25a),
               _v(e_margin.fy26e), _v(e_margin.fy27e)]
              if e_margin else [0.0] * 5)
        p = os.path.join(output_dir, "ebitda.png")
        try:
            _bar_line(YEARS, ev, mv, "EBITDA (Rs.cr)", "Margin (%)", "EBITDA", p)
            paths["ebitda"] = p
        except Exception as e:
            print(f"EBITDA chart error: {e}")

    # ── Chart 4: PAT (bar) + Net Profit Margin% (line) ───────────────────────
    pat = _find(IS, "Reported PAT", "Adj. PAT", "Profit after tax")
    npm = _find(RT, "Net profit mgn", "Net profit margin", "NPM")
    if pat:
        pv = [_v(pat.fy23a), _v(pat.fy24a), _v(pat.fy25a),
              _v(pat.fy26e), _v(pat.fy27e)]
        nv = ([_v(npm.fy23a), _v(npm.fy24a), _v(npm.fy25a),
               _v(npm.fy26e), _v(npm.fy27e)]
              if npm else [0.0] * 5)
        p = os.path.join(output_dir, "pat.png")
        try:
            _bar_line(YEARS, pv, nv, "PAT (Rs.cr)", "Margin (%)", "PAT", p)
            paths["pat"] = p
        except Exception as e:
            print(f"PAT chart error: {e}")

    return paths
