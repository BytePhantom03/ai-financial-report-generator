"""
charts.py — Geojit-style financial charts matching the sample PDF exactly.
Produces bar+line combo charts for Revenue, EBITDA, PAT.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from schema import GeojitReportData

# ── Geojit brand palette ────────────────────────────────────────────────
TEAL   = "#00A1C6"
ORANGE = "#F26522"
BLUE   = "#004B87"
GREY   = "#888888"

def _v(s):
    """Safe string→float. Returns 0.0 if missing/dash."""
    try:
        return float(str(s).replace(",","").replace("%","").replace("(","").replace(")","").strip())
    except:
        return 0.0

def _bar_line_chart(labels, bar_vals, line_vals, bar_label, line_label,
                    title, path, bar_color=TEAL, line_color=ORANGE):
    """Bar + line combo chart matching Geojit style."""
    fig, ax1 = plt.subplots(figsize=(4.2, 2.6))
    fig.patch.set_facecolor("white")
    ax1.set_facecolor("white")

    x = np.arange(len(labels))
    w = 0.55
    bars = ax1.bar(x, bar_vals, width=w, color=bar_color, zorder=3, alpha=0.85)

    # Value labels on bars
    for bar in bars:
        h = bar.get_height()
        if h != 0:
            ax1.text(bar.get_x() + bar.get_width()/2, h + max(bar_vals)*0.01,
                     f"{h:,.0f}" if abs(h) >= 10 else f"{h:.1f}",
                     ha="center", va="bottom", fontsize=5, color=GREY)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=6, rotation=0)
    ax1.tick_params(axis="y", labelsize=6, colors=TEAL)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.spines["left"].set_color(TEAL)
    ax1.yaxis.label.set_color(TEAL)
    ax1.set_ylabel(bar_label, fontsize=6, color=TEAL)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f}"))
    ax1.axhline(0, color=GREY, linewidth=0.5)

    # Line on twin axis
    ax2 = ax1.twinx()
    ax2.plot(x, line_vals, color=line_color, linewidth=1.5,
             marker="o", markersize=3, zorder=4)
    for i, (xi, yi) in enumerate(zip(x, line_vals)):
        ax2.text(xi, yi + max(abs(v) for v in line_vals)*0.05 if yi >= 0 else yi - max(abs(v) for v in line_vals)*0.08,
                 f"{yi:.1f}%", ha="center", va="bottom", fontsize=5, color=line_color)
    ax2.tick_params(axis="y", labelsize=6, colors=line_color)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.spines["right"].set_color(line_color)
    ax2.yaxis.label.set_color(line_color)
    ax2.set_ylabel(line_label, fontsize=6, color=line_color)

    # Legend
    from matplotlib.lines import Line2D
    legend_elems = [
        matplotlib.patches.Patch(facecolor=bar_color, label=bar_label),
        Line2D([0],[0], color=line_color, linewidth=1.5, label=line_label)
    ]
    ax1.legend(handles=legend_elems, fontsize=5, loc="upper left",
               frameon=False, ncol=2)

    plt.title(title, fontsize=7, fontweight="bold", color="#333333", pad=4)
    plt.tight_layout(pad=0.5)
    plt.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()


def generate_charts(data: GeojitReportData, output_dir: str = "temp_charts") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    YEARS = ["FY23A","FY24A","FY25A","FY26E","FY27E"]
    IS = data.financials.income_statement
    RT = data.financials.ratios

    def _row(rows, *keys):
        for key in keys:
            for r in rows:
                if key.lower() in r.metric.lower():
                    return r
        return None

    # ── Chart 1: Revenue (bar) + Growth% (line) ─────────────────────────
    rev = _row(IS, "Sales", "Revenue", "Net interest income")
    if rev:
        vals  = [_v(rev.fy23a), _v(rev.fy24a), _v(rev.fy25a), _v(rev.fy26e), _v(rev.fy27e)]
        # compute YoY growth
        growths = [0]
        for i in range(1, len(vals)):
            g = ((vals[i]-vals[i-1])/abs(vals[i-1])*100) if vals[i-1] != 0 else 0
            growths.append(round(g, 1))
        try:
            p = os.path.join(output_dir, "revenue.png")
            _bar_line_chart(YEARS, vals, growths, "Revenue (Rs.cr)", "Growth (%)",
                            "Revenue", p, TEAL, ORANGE)
            paths["revenue"] = p
        except Exception as e:
            print("Revenue chart error:", e)

    # ── Chart 2: EBITDA (bar) + Margin% (line) ──────────────────────────
    ebitda = _row(IS, "EBITDA")
    margin = _row(RT, "EBITDA margin") or _row(IS, "EBITDA Margin")
    if ebitda:
        ev = [_v(ebitda.fy23a), _v(ebitda.fy24a), _v(ebitda.fy25a), _v(ebitda.fy26e), _v(ebitda.fy27e)]
        mv = ([_v(margin.fy23a), _v(margin.fy24a), _v(margin.fy25a), _v(margin.fy26e), _v(margin.fy27e)]
              if margin else [0]*5)
        try:
            p = os.path.join(output_dir, "ebitda.png")
            _bar_line_chart(YEARS, ev, mv, "EBITDA (Rs.cr)", "Margin (%)",
                            "EBITDA", p, TEAL, ORANGE)
            paths["ebitda"] = p
        except Exception as e:
            print("EBITDA chart error:", e)

    # ── Chart 3: PAT (bar) + Margin% (line) ─────────────────────────────
    pat = _row(IS, "Reported PAT", "Adj. PAT", "Profit after tax")
    npm = _row(RT, "Net profit mgn", "Net profit margin")
    if pat:
        pv = [_v(pat.fy23a), _v(pat.fy24a), _v(pat.fy25a), _v(pat.fy26e), _v(pat.fy27e)]
        nv = ([_v(npm.fy23a), _v(npm.fy24a), _v(npm.fy25a), _v(npm.fy26e), _v(npm.fy27e)]
              if npm else [0]*5)
        try:
            p = os.path.join(output_dir, "pat.png")
            _bar_line_chart(YEARS, pv, nv, "PAT (Rs.cr)", "Margin (%)",
                            "PAT", p, TEAL, ORANGE)
            paths["pat"] = p
        except Exception as e:
            print("PAT chart error:", e)

    # ── Chart 4: Gross Order Value or NII ───────────────────────────────
    gov = _row(IS, "Gross Order", "Core operating profit", "Non-interest income")
    if gov:
        gv = [_v(gov.fy23a), _v(gov.fy24a), _v(gov.fy25a), _v(gov.fy26e), _v(gov.fy27e)]
        growths4 = [0]
        for i in range(1, len(gv)):
            g = ((gv[i]-gv[i-1])/abs(gv[i-1])*100) if gv[i-1] != 0 else 0
            growths4.append(round(g, 1))
        try:
            p = os.path.join(output_dir, "gov.png")
            _bar_line_chart(YEARS, gv, growths4, gov.metric[:20], "Growth (%)",
                            gov.metric[:25], p, "#5BA3C9", ORANGE)
            paths["gov"] = p
        except Exception as e:
            print("GOV chart error:", e)

    return paths
