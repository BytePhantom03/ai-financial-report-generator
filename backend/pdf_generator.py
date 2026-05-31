import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, HRFlowable, NextPageTemplate, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from schema import GeojitReportData
from charts import generate_charts

# ── Page geometry
W, H = A4           # 595.3 × 841.9 pt
LM   = 18           # left margin
RM   = 18           # right margin
TM   = 34           # top margin  (clears green header bar)
BM   = 24           # bottom margin (clears footer bar)
BW   = W - LM - RM  # usable body width ≈ 559 pt

# ── Brand palette
C_BLUE   = colors.HexColor("#004B87")
C_GREEN  = colors.HexColor("#7DBA00")
C_ORANGE = colors.HexColor("#F26522")
C_RED    = colors.HexColor("#CC2200")
C_TEAL   = colors.HexColor("#00A1C6")
C_LGREY  = colors.HexColor("#E8E8E8")
C_XLGREY = colors.HexColor("#F5F5F5")
C_DGREY  = colors.HexColor("#3D3D3D")
C_MGREY  = colors.HexColor("#888888")
C_WHITE  = colors.white
C_BLACK  = colors.black

RATING_COLOR = {
    "BUY":        "#007700",
    "ACCUMULATE": "#007700",
    "HOLD":       "#F26522",
    "REDUCE":     "#CC2200",
    "SELL":       "#CC2200",
}


# ─────────────────────────────────────────────────────────────────────────────
# Style factory
# ─────────────────────────────────────────────────────────────────────────────
def _make_styles():
    S = getSampleStyleSheet()
    defs = {
        "t5":    dict(fontSize=5,    leading=6.5,  textColor=C_DGREY),
        "t6":    dict(fontSize=6,    leading=7.5,  textColor=C_DGREY),
        "t6b":   dict(fontSize=6,    leading=7.5,  textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "t7":    dict(fontSize=7,    leading=9.5,  textColor=C_DGREY),
        "t7b":   dict(fontSize=7,    leading=9.5,  textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "t8":    dict(fontSize=8,    leading=10.5, textColor=C_DGREY),
        "t8b":   dict(fontSize=8,    leading=10.5, textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "t9b":   dict(fontSize=9,    leading=12,   textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "ctr6":  dict(fontSize=6,    leading=7.5,  textColor=C_DGREY,  alignment=TA_CENTER),
        "ctr7":  dict(fontSize=7,    leading=9,    textColor=C_DGREY,  alignment=TA_CENTER),
        "wh6b":  dict(fontSize=6,    leading=7.5,  textColor=C_WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER),
        "wh7b":  dict(fontSize=7,    leading=9,    textColor=C_WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER),
        "bl7b":  dict(fontSize=7,    leading=9,    textColor=C_BLUE,   fontName="Helvetica-Bold"),
        "bl9b":  dict(fontSize=9,    leading=12,   textColor=C_BLUE,   fontName="Helvetica-Bold"),
        "co":    dict(fontSize=20,   leading=24,   textColor=C_BLUE,   fontName="Helvetica-Bold"),
        "sec":   dict(fontSize=9,    leading=12,   textColor=C_BLUE,   fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=3),
        "hdl":   dict(fontSize=10,   leading=13,   textColor=C_BLUE,   fontName="Helvetica-Bold", spaceAfter=3),
        "org9b": dict(fontSize=9,    leading=11,   textColor=C_ORANGE, fontName="Helvetica-Bold"),
        "disc":  dict(fontSize=5.5,  leading=7.2,  textColor=C_MGREY,  alignment=TA_JUSTIFY),
        "bullet":dict(fontSize=7,    leading=10,   textColor=C_DGREY,  leftIndent=10, firstLineIndent=-10, spaceAfter=2),
    }
    for name, kw in defs.items():
        kw["parent"] = S["Normal"]
        S.add(ParagraphStyle(name, **kw))
    return S


# ─────────────────────────────────────────────────────────────────────────────
# Table helpers
# ─────────────────────────────────────────────────────────────────────────────
def _tbl(data, cw, hbg=None, hfg=C_BLACK, fs=6.5, zebra=True, repeat=1):
    if hbg is None:
        hbg = C_LGREY
    t = Table(data, colWidths=cw, repeatRows=repeat)
    cmds = [
        ("BACKGROUND",    (0,0), (-1,0),  hbg),
        ("TEXTCOLOR",     (0,0), (-1,0),  hfg),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), fs),
        ("LEADING",       (0,0), (-1,-1), fs + 1.8),
        ("TOPPADDING",    (0,0), (-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
        ("ALIGN",         (0,0), (0,-1),  "LEFT"),
        ("ALIGN",         (1,0), (-1,-1), "RIGHT"),
        ("LINEBELOW",     (0,0), (-1,0),  0.7, C_BLUE),
        ("LINEABOVE",     (0,0), (-1,0),  0.7, C_BLUE),
        ("BOX",           (0,0), (-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0), (-1,-1), 0.2, C_LGREY),
    ]
    if zebra:
        cmds.append(("ROWBACKGROUNDS", (0,1), (-1,-1), [C_WHITE, C_XLGREY]))
    t.setStyle(TableStyle(cmds))
    return t


def _kv_tbl(rows, cw, fs=6.5):
    t = Table(rows, colWidths=cw)
    t.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (0,-1),  "Helvetica-Bold"),
        ("FONTNAME",      (1,0), (1,-1),  "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), fs),
        ("LEADING",       (0,0), (-1,-1), fs + 2),
        ("TOPPADDING",    (0,0), (-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
        ("ALIGN",         (1,0), (1,-1),  "RIGHT"),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0), (-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0), (-1,-1), 0.2, C_LGREY),
    ]))
    return t


def _fs_tbl(title, rows, lbl_w=88, yr_w=38, fs=6):
    """Financial statement table: blue header row, zebra body, 5-year columns."""
    if not rows:
        return None
    YRS = ["FY23A", "FY24A", "FY25A", "FY26E", "FY27E"]
    cw  = [lbl_w] + [yr_w] * 5
    hdr = [Paragraph(f"<b>{title}</b>",
                     ParagraphStyle("_fsh", parent=ParagraphStyle("_b"),
                                    fontSize=fs, leading=fs+2,
                                    textColor=C_WHITE, fontName="Helvetica-Bold"))] + YRS
    td  = [hdr] + [[r.metric, r.fy23a, r.fy24a, r.fy25a, r.fy26e, r.fy27e]
                   for r in rows]
    t = Table(td, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0),  C_WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), fs),
        ("LEADING",       (0,0), (-1,-1), fs + 1.8),
        ("TOPPADDING",    (0,0), (-1,-1), 1.2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.2),
        ("LEFTPADDING",   (0,0), (-1,-1), 2.5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 2.5),
        ("ALIGN",         (0,0), (0,-1),  "LEFT"),
        ("ALIGN",         (1,0), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0), (-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0), (-1,-1), 0.2, C_LGREY),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Canvas decorations  (header, footer, sidebar)
# ─────────────────────────────────────────────────────────────────────────────
def _draw_header(c):
    c.setFillColor(C_GREEN)
    c.rect(0, H - 26, W, 26, fill=1, stroke=0)

    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(LM, H - 17, "Retail Equity Research")

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(W - LM, H - 15, "GEOJIT")
    c.setFont("Helvetica", 5.5)
    c.drawRightString(W - LM, H - 23, "PEOPLE YOU PROSPER WITH")

    c.setStrokeColor(C_LGREY)
    c.setLineWidth(0.4)
    c.line(LM, H - 28, W - RM, H - 28)


def _draw_footer(c):
    c.setFillColor(C_GREEN)
    c.rect(0, 0, W, 18, fill=1, stroke=0)

    c.setFillColor(C_WHITE)
    c.circle(14, 9, 7, fill=1, stroke=0)
    c.setFillColor(C_GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(14, 6, "G")

    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(W / 2, 6, "www.geojit.com")


def _draw_sidebar(c, text):
    """Orange vertical tab on right edge (page 1 only)."""
    tw, th = 17, 115
    x = W - tw
    y = H - 26 - th - 18
    c.setFillColor(C_ORANGE)
    c.rect(x, y, tw, th, fill=1, stroke=0)
    c.saveState()
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 6.5)
    c.translate(x + tw / 2, y + th / 2)
    c.rotate(90)
    c.drawCentredString(0, -2.5, text)
    c.restoreState()


def _on_page1(c, doc):
    c.saveState()
    _draw_header(c)
    _draw_footer(c)
    _draw_sidebar(c, getattr(doc, "_sidebar_tag", "Q1FY26") + "  Result Update")
    c.restoreState()


def _on_page_n(c, doc):
    c.saveState()
    _draw_header(c)
    _draw_footer(c)
    c.setFillColor(C_MGREY)
    c.setFont("Helvetica", 7)
    c.drawRightString(W - RM, 19, str(doc.page))
    c.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Small flowable helpers
# ─────────────────────────────────────────────────────────────────────────────
def _rating_badge(rating, S):
    clr = colors.HexColor(RATING_COLOR.get(rating.upper(), "#F26522"))
    p = Paragraph(f'<font color="white" size="11"><b>{rating}</b></font>', S["ctr7"])
    t = Table([[p]], colWidths=[52], rowHeights=[24])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,0), clr),
        ("ALIGN",         (0,0), (0,0), "CENTER"),
        ("VALIGN",        (0,0), (0,0), "MIDDLE"),
        ("TOPPADDING",    (0,0), (0,0), 4),
        ("BOTTOMPADDING", (0,0), (0,0), 4),
    ]))
    return t


def _chg_cell(val, S):
    try:
        v = float(str(val).replace(",", "").replace("%", "").strip())
        if v > 0:
            return Paragraph(f'<font color="#007700">▲ {val}</font>', S["ctr6"])
        if v < 0:
            return Paragraph(f'<font color="#CC2200">▼ {val}</font>', S["ctr6"])
    except Exception:
        pass
    return Paragraph(str(val) if val else "—", S["ctr6"])


def _sec(title, S):
    return Paragraph(title, S["sec"])


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf(data: GeojitReportData, output_filename: str) -> str:
    out_dir = os.path.dirname(os.path.abspath(output_filename)) or "."
    os.makedirs(out_dir, exist_ok=True)

    S   = _make_styles()
    v   = data.valuation
    cd  = data.company_data
    rating = (v.rating or "HOLD").upper()

    qm = re.search(r"Q\d+?FY\d+", data.report_date or "")
    sidebar_tag = qm.group(0) if qm else "Q1FY26"

    chart_dir   = os.path.join(out_dir,
                  "charts_" + os.path.splitext(os.path.basename(output_filename))[0])
    chart_paths = generate_charts(data, chart_dir)

    IS = data.financials.income_statement
    BS = data.financials.balance_sheet
    CF = data.financials.cash_flow
    RT = data.financials.ratios

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — Executive Summary  (two-column layout)
    # ══════════════════════════════════════════════════════════════════════════
    # Column widths: left ≈ 170 pt, right = rest (minus 8 pt gutter)
    LC = 172
    RC = BW - LC - 8

    # ── LEFT COLUMN ──────────────────────────────────────────────────────────
    left = []

    # Company Data table
    cd_rows = [
        [Paragraph("<b>Company Data</b>", S["bl7b"]), ""],
        ["Market Cap (Rs.cr)",      cd.market_cap],
        ["52 Week High – Low (Rs.)", cd.high_low],
        ["Enterprise Value (Rs.cr)", cd.enterprise_value],
        ["Outstanding Shares (cr)", cd.outstanding_shares],
        ["Free Float (%)",           cd.free_float],
        ["Dividend Yield (%)",       cd.dividend_yield],
        ["6m average volume (cr)",   cd.avg_volume],
        ["Beta",                     cd.beta],
        ["Face value (Rs.)",         cd.face_value],
    ]
    cd_t = Table(cd_rows, colWidths=[106, 62])
    cd_t.setStyle(TableStyle([
        ("SPAN",          (0,0), (1,0)),
        ("BACKGROUND",    (0,0), (1,0),  C_LGREY),
        ("LINEBELOW",     (0,0), (1,0),  0.7, C_BLUE),
        ("FONTNAME",      (0,1), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,1), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 6.5),
        ("LEADING",       (0,0), (-1,-1), 8.5),
        ("TOPPADDING",    (0,0), (-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
        ("ALIGN",         (1,1), (1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0), (-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0), (-1,-1), 0.2, C_LGREY),
    ]))
    left.append(cd_t)
    left.append(Spacer(1, 5))

    # Shareholding table
    sh = data.shareholding[:3]
    if sh:
        sh_rows = [["Shareholding (%)"] + [s.quarter for s in sh]]
        for lbl, attr in [
            ("Promoters",    "promoters"),
            ("FII's",        "fiis"),
            ("MFs/Inst.",    "mfs_institutions"),
            ("Public",       "public"),
            ("Others",       "others"),
            ("Total",        "__tot__"),
            ("Promoter Pledge", "promoter_pledge"),
        ]:
            row = [lbl]
            for s in sh:
                row.append("100.0" if attr == "__tot__" else str(getattr(s, attr, "—")))
            sh_rows.append(row)
        ncols = len(sh)
        left.append(_tbl(sh_rows, [72] + [32] * ncols, fs=6))
        left.append(Spacer(1, 5))

    # Price Performance table
    pp = data.price_performance[:3]
    if pp:
        pp_rows = [
            ["Price Performance"] + [p.period for p in pp],
            ["Absolute Return"]   + [p.absolute_return for p in pp],
            ["Absolute Sensex"]   + [p.absolute_sensex for p in pp],
            ["Relative Return*"]  + [p.relative_return for p in pp],
        ]
        left.append(_tbl(pp_rows, [74] + [32] * len(pp), fs=6))
        left.append(Spacer(1, 2))
        left.append(Paragraph("*over/under performance to benchmark index", S["t5"]))
        left.append(Spacer(1, 5))

    # Mini price chart: use revenue chart in left column as trend indicator
    rev_chart = chart_paths.get("revenue")
    if rev_chart and os.path.exists(rev_chart):
        left.append(Image(rev_chart, width=LC - 4, height=100))

    # ── RIGHT COLUMN ─────────────────────────────────────────────────────────
    right = []

    # "Retail Equity Research" sub-label
    right.append(Paragraph("Retail Equity Research", S["t7b"]))
    right.append(Spacer(1, 2))

    # Large company name
    right.append(Paragraph(data.company_name, S["co"]))
    right.append(Spacer(1, 3))

    # Sector + date line
    right.append(Paragraph(
        f'Sector:  <b>{data.sector}</b>'
        f'<font color="#888888" size="7">          {data.report_date}</font>',
        S["t7"]))
    right.append(Spacer(1, 4))

    # Key Changes row: [badge | Target ▲ | Rating ▼ | Earnings ▼]
    arr_up = Paragraph('<font color="#007700" size="10">▲</font>', S["ctr7"])
    arr_dn = Paragraph('<font color="#CC2200" size="10">▼</font>', S["ctr7"])
    kc_t = Table(
        [["Key Changes", "Target",  "Rating",  "Earnings"],
         [_rating_badge(rating, S), arr_up, arr_dn, arr_dn]],
        colWidths=[90, 68, 68, 68])
    kc_t.setStyle(TableStyle([
        ("FONTSIZE",      (0,0), (-1,-1), 7),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND",    (0,0), (-1,0),  C_LGREY),
        ("LINEBELOW",     (0,0), (-1,0),  0.5, C_LGREY),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("BOX",           (0,0), (-1,-1), 0.3, C_LGREY),
    ]))
    right.append(kc_t)
    right.append(Spacer(1, 3))

    # Stock ID strip: Stock Type | Bloomberg | Sensex | NSE | BSE | Time Frame
    id_rows = [
        ["Stock Type", "Bloomberg Code", "Sensex", "NSE Code", "BSE Code", "Time Frame"],
        [v.stock_type or "Large Cap", v.bloomberg or "—", v.sensex or "—",
         v.nse_code or "—", v.bse_code or "—", v.time_frame or "12 Months"],
    ]
    right.append(_tbl(id_rows, [58, 78, 48, 50, 50, 52], fs=6))
    right.append(Spacer(1, 2))
    right.append(Paragraph(f"Data as of {data.report_date}, 16:23hrs", S["t5"]))
    right.append(Spacer(1, 4))

    # Target / CMP / Return block (top-right of right column)
    tcr = Table(
        [[Paragraph("Target", S["t6b"]),
          Paragraph(f"Rs. {v.target}", S["t8b"])],
         [Paragraph("CMP",    S["t6b"]),
          Paragraph(f"Rs. {v.cmp}",    S["t8b"])],
         [Paragraph("Return", S["t6b"]),
          Paragraph(v.upside or "—",   S["org9b"])]],
        colWidths=[54, RC - 58])
    tcr.setStyle(TableStyle([
        ("ALIGN",         (1,0), (1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
        ("LINEBELOW",     (0,-1), (-1,-1), 0.4, C_LGREY),
    ]))
    right.append(tcr)
    right.append(Spacer(1, 5))
    right.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    right.append(Spacer(1, 4))

    # Bold headline (first highlight acts as headline)
    headline = (data.highlights[0]
                if data.highlights
                else f"{data.company_name}: Financial Update")
    right.append(Paragraph(headline, S["hdl"]))
    right.append(Spacer(1, 2))

    # Company description paragraph
    right.append(Paragraph(data.company_description, S["t7"]))
    right.append(Spacer(1, 4))

    # Bullet highlights (skip item 0 already used as headline)
    for hl in (data.highlights[1:] if len(data.highlights) > 1 else data.highlights):
        right.append(Paragraph(f"\u2022\u2002{hl}", S["bullet"]))
    right.append(Spacer(1, 5))

    right.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    right.append(Spacer(1, 3))

    # Outlook & Valuation
    right.append(_sec("Outlook & Valuation", S))
    right.append(Paragraph(data.outlook_valuation, S["t7"]))
    right.append(Spacer(1, 5))

    right.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    right.append(Spacer(1, 3))

    # Quarterly Financials Consolidated table
    right.append(_sec("Quarterly Financials Consolidated", S))
    right.append(Spacer(1, 2))

    q_cw  = [58, 40, 40, 56, 40, 56]
    q_hdr = ["Rs.cr", "Q1FY26", "Q1FY25", "YoY Growth (%)", "Q4FY25", "QoQ Growth (%)"]
    q_rows = [q_hdr]

    def _find_row(pool, *keys):
        for key in keys:
            for r in pool:
                if key.lower() in r.metric.lower():
                    return r
        return None

    def _yoy(a, b):
        try:
            fa, fb = float(str(a).replace(",","")), float(str(b).replace(",",""))
            if fa:
                return f"{(fb - fa)/abs(fa)*100:.1f}"
        except Exception:
            pass
        return "—"

    q_metrics = [
        ("Sales",       ["Sales", "Revenue", "Net interest income"]),
        ("EBITDA",      ["EBITDA"]),
        ("EBIT",        ["EBIT"]),
        ("Margin (%)",  ["EBITDA Margin", "EBIT margin"]),
        ("PBT",         ["PBT", "Profit before tax"]),
        ("Rep. PAT",    ["Reported PAT", "Profit after tax"]),
        ("Adj. PAT",    ["Adj. PAT", "Adjusted PAT"]),
        ("Adj. EPS (Rs)", ["Adj EPS", "Adj. EPS", "Adjusted EPS"]),
    ]
    for label, keys in q_metrics:
        row = _find_row(IS, *keys) or _find_row(RT, *keys)
        if row:
            yoy = _yoy(row.fy24a, row.fy25a)
            qoq = _yoy(row.fy24a, row.fy25a)
            q_rows.append([row.metric, row.fy25a, row.fy24a,
                           yoy, row.fy24a, qoq])
    if len(q_rows) == 1:
        for m in ["Sales", "EBITDA", "PAT"]:
            q_rows.append([m, "—", "—", "—", "—", "—"])

    right.append(_tbl(q_rows, q_cw, hbg=C_BLUE, hfg=C_WHITE, fs=6))
    right.append(Spacer(1, 4))

    # Annual Key Estimates table (Y.E March: FY25A FY26E FY27E Growth%)
    right.append(Spacer(1, 2))
    ann_hdr = ["Y.E March (Rs. cr)", "FY25A", "FY26E", "FY27E", "Growth (%)", "Growth (%)"]
    ann_rows = [["Y.E March (Rs. cr)", "FY25A", "FY26E", "FY27E", "FY26E Chg", "FY27E Chg"]]
    added = 0
    ann_metrics = [
        ["Sales", "Revenue", "Net interest income"],
        ["Growth (%)", "Sales growth"],
        ["EBITDA"],
        ["EBITDA Margin"],
        ["PAT Adjusted", "Adj. PAT", "Reported PAT"],
        ["Growth (%)"],
        ["Adjusted EPS", "Adj EPS", "Adj. EPS"],
        ["Growth (%)"],
        ["P/E"],
        ["P/B", "P/BV"],
        ["EV/EBITDA"],
        ["ROE"],
        ["D/E"],
    ]
    for keys in ann_metrics:
        row = _find_row(IS, *keys) or _find_row(RT, *keys)
        if row and added < 12:
            c26 = _yoy(row.fy25a, row.fy26e)
            c27 = _yoy(row.fy25a, row.fy27e)
            ann_rows.append([row.metric, row.fy25a, row.fy26e, row.fy27e, c26, c27])
            added += 1
    if added == 0:
        for m in ["Sales", "EBITDA", "PAT"]:
            ann_rows.append([m, "—", "—", "—", "—", "—"])

    right.append(_tbl(ann_rows, [104, 42, 42, 42, 44, 44],
                      hbg=C_BLUE, hfg=C_WHITE, fs=6.5))

    # Assemble two-column page 1
    pg1 = Table(
        [[left, right]],
        colWidths=[LC, RC],
        style=TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
    story.append(pg1)
    story.append(NextPageTemplate("pN"))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — Key Highlights + 4-chart grid + Change in Estimates
    # ══════════════════════════════════════════════════════════════════════════
    story.append(_sec("Key highlights", S))
    story.append(Spacer(1, 3))
    for hl in data.highlights:
        story.append(Paragraph(f"\u2022\u2002{hl}", S["bullet"]))
    story.append(Spacer(1, 8))

    # 2×2 chart grid — use charts that were generated; fall back to blank spacer
    C_W  = (BW - 12) / 2        # ~273 pt wide
    C_H  = C_W * 0.72           # aspect ~4:2.9

    def _chart_cell(key, title):
        """Return an Image or a titled placeholder."""
        p = chart_paths.get(key)
        if p and os.path.exists(p):
            return Image(p, width=C_W, height=C_H)
        return Paragraph(f"<b>{title}</b>", S["t6b"])

    chart_grid = Table(
        [[_chart_cell("revenue", "Revenue"),
          _chart_cell("gov",     "Gross Order Value")],
         [_chart_cell("ebitda",  "EBITDA"),
          _chart_cell("pat",     "PAT")]],
        colWidths=[C_W + 6, C_W + 6],
        style=TableStyle([
            ("ALIGN",         (0,0), (-1,-1), "CENTER"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ]))
    story.append(chart_grid)
    story.append(Spacer(1, 8))

    # Change in Estimates table
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    story.append(Spacer(1, 4))
    story.append(_sec("Change in Estimates", S))
    story.append(Spacer(1, 3))

    E_CW  = [72, 52, 52, 52, 52, 50, 50]
    e_r0  = [
        Paragraph("Year / Rs cr", S["t6b"]),
        Paragraph("Old estimates", S["wh6b"]), "",
        Paragraph("New estimates", S["wh6b"]), "",
        Paragraph("Change (%)",    S["wh6b"]), "",
    ]
    e_r1  = ["", "FY26E", "FY27E", "FY26E", "FY27E", "FY26E", "FY27E"]
    est_rows = [e_r0, e_r1]
    for e in data.estimates:
        est_rows.append([
            e.metric,
            e.old_estimate_fy26, e.old_estimate_fy27,
            e.new_estimate_fy26, e.new_estimate_fy27,
            _chg_cell(e.change_fy26, S),
            _chg_cell(e.change_fy27, S),
        ])

    t_est = Table(est_rows, colWidths=E_CW, repeatRows=2)
    t_est.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0),  C_LGREY),
        ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
        ("BACKGROUND",    (1,0),  (2,0),   C_BLUE),
        ("BACKGROUND",    (3,0),  (4,0),   C_BLUE),
        ("BACKGROUND",    (5,0),  (6,0),   C_BLUE),
        ("SPAN",          (1,0),  (2,0)),
        ("SPAN",          (3,0),  (4,0)),
        ("SPAN",          (5,0),  (6,0)),
        ("ALIGN",         (0,0),  (-1,-1), "CENTER"),
        ("ALIGN",         (0,0),  (0,-1),  "LEFT"),
        ("BACKGROUND",    (0,1),  (-1,1),  C_XLGREY),
        ("FONTNAME",      (0,1),  (-1,1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),  (-1,-1), 6.5),
        ("LEADING",       (0,0),  (-1,-1), 8.5),
        ("TOPPADDING",    (0,0),  (-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 1.5),
        ("LEFTPADDING",   (0,0),  (-1,-1), 3),
        ("RIGHTPADDING",  (0,0),  (-1,-1), 3),
        ("ROWBACKGROUNDS",(0,2),  (-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0),  (-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0),  (-1,-1), 0.2, C_LGREY),
        ("LINEBELOW",     (0,0),  (-1,0),  0.5, C_LGREY),
        ("LINEBELOW",     (0,1),  (-1,1),  0.7, C_BLUE),
    ]))
    story.append(t_est)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — Consolidated Financials (4-quadrant)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(_sec("Consolidated Financials", S))
    story.append(Spacer(1, 4))

    HALF  = (BW - 10) / 2
    LBL   = 86
    YW    = int((HALF - LBL) / 5)

    def _quad_col(label, rows, lbl_w=LBL, yr_w=YW):
        tbl = _fs_tbl(label, rows, lbl_w=lbl_w, yr_w=yr_w, fs=6)
        if tbl is None:
            return [Paragraph(f"<b>{label}</b>", S["bl7b"]),
                    Spacer(1, 2),
                    Paragraph("No data extracted.", S["t6"])]
        return [Paragraph(f"<b>{label}</b>", S["bl7b"]), Spacer(1, 2), tbl]

    row1 = Table(
        [[_quad_col("Profit & Loss", IS),
          _quad_col("Balance Sheet", BS)]],
        colWidths=[HALF, HALF],
        style=TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (0,-1),  6),
            ("RIGHTPADDING",  (1,0), (1,-1),  0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
    story.append(row1)
    story.append(Spacer(1, 8))

    row2 = Table(
        [[_quad_col("Cashflow", CF),
          _quad_col("Ratio", RT)]],
        colWidths=[HALF, HALF],
        style=TableStyle([
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0), (-1,-1), 0),
            ("RIGHTPADDING",  (0,0), (0,-1),  6),
            ("RIGHTPADDING",  (1,0), (1,-1),  0),
            ("TOPPADDING",    (0,0), (-1,-1), 0),
            ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ]))
    story.append(row2)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — Recommendation Summary + Rating Criteria + Disclosures
    # ══════════════════════════════════════════════════════════════════════════
    story.append(_sec("Recommendation Summary  —  (last 3 years)", S))
    story.append(Spacer(1, 4))

    if data.recommendation_history:
        rc_rows = [["Dates", "Rating", "Target"]]
        for r in data.recommendation_history:
            rc_rows.append([r.get("Date","—"), r.get("Rating","—"), r.get("Target","—")])
        story.append(_tbl(rc_rows, [130, 90, 90], fs=7))
    else:
        story.append(Paragraph("No prior recommendation history available.", S["t7"]))

    story.append(Spacer(1, 10))
    story.append(_sec("Investment Rating Criteria", S))
    story.append(Spacer(1, 3))

    irc = [
        ["Ratings",           "Large caps",                   "Midcaps",                        "Small Caps"],
        ["Buy",               "Upside is above 10%",          "Upside is above 15%",            "Upside is above 20%"],
        ["Accumulate",        "—",                            "Upside between 10%-15%",         "Upside between 10%-20%"],
        ["Hold",              "Upside between 0%-10%",        "Upside between 0%-10%",          "Upside between 0%-10%"],
        ["Reduce/sell",       "Downside is more than 0%",     "Downside is more than 0%",       "Downside is more than 0%"],
        ["Not rated/Neutral", "—",                            "—",                              "—"],
    ]
    story.append(_tbl(irc, [72, 148, 148, 148], fs=7))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Buy:</b> Acquire at Current Market Price (CMP), with the target mentioned in the research note.  "
        "<b>Accumulate:</b> Partial buying or to accumulate as CMP dips in the future.  "
        "<b>Hold:</b> Hold the stock with the expected target mentioned in the note.  "
        "<b>Reduce:</b> Reduce your exposure to the stock due to limited upside.  "
        "<b>Sell:</b> Exit from the stock.  "
        "<b>Not rated/Neutral:</b> The analyst has no investment opinion on the stock under review.",
        S["disc"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Symbols definition:</b>  "
        '<font color="#007700">▲ Upgrade</font>   '
        '◆ No Change   '
        '<font color="#CC2200">▼ Downgrade</font>', S["disc"]))
    story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=0.6, color=C_LGREY))
    story.append(Spacer(1, 4))
    story.append(Paragraph("DISCLAIMER & DISCLOSURES", S["t7b"]))
    story.append(Spacer(1, 3))

    disc_txt = (
        "<b>Certification:</b> The analyst(s) of this Report hereby certify that all the views expressed in this "
        "research report reflect personal views about any or all of the subject issuer or securities. This report has "
        "been prepared by the Research Team of Geojit Investments Limited, hereinafter referred to as GIL. "
        "CRISIL has provided research support in preparation of this research report. The target price and "
        "recommendation provided in this report are strictly GIL's views and are NOT PROVIDED by CRISIL. "
        "CRISIL expresses no opinion on valuation and has no financial liability whatsoever to the subscribers "
        "or users of this report.<br/><br/>"
        "<b>Standard Warning:</b> Investment in securities market are subject to market risks. Read all related "
        "documents carefully before investing.<br/><br/>"
        "The recommendations are based on a 12 month horizon, unless otherwise specified. The investment ratings "
        "are on absolute positive/negative return basis. It is possible that due to volatile price fluctuation "
        "in the near to medium term, there could be a temporary mismatch to rating.<br/><br/>"
        "<b>Regulatory Disclosures:</b> Geojit Investments Limited (GIL) and its subsidiaries are registered with "
        "SEBI as a Research Analyst (SEBI Reg. No. INH200000345). GIL confirms that (i) it has no financial "
        "interest or any other material conflict in relation to the subject company(ies) covered herein; (ii) "
        "GIL's associates have no actual/beneficial ownership of 1% or more in the subject company at the end "
        "of the month immediately preceding the date of publication of the research report.<br/><br/>"
        "<b>11. Standard Warning:</b> \"In securities market are subject to market risks. Read all the related "
        "documents carefully before investing.\"<br/><br/>"
        "<b>Geojit Financial Services Ltd.</b>  Registered Office: 7th Floor 34/659-P, Civil Line Road, "
        "Padivattom, Kochi-682024, Kerala, India.  Phone: +91 484-2901000  Website: www.geojit.com  "
        "SEBI Reg. No.: INH200000345  Corporate Identity Number: U67120KL2023PLC086700  "
        "Depository Participant : IN-DP-761-2024"
    )
    story.append(Paragraph(disc_txt, S["disc"]))

    # ── Document build ────────────────────────────────────────────────────────
    class _GDoc(BaseDocTemplate):
        def __init__(self, *a, **kw):
            self._sidebar_tag = kw.pop("sidebar_tag", "Q1FY26")
            super().__init__(*a, **kw)

        def handle_pageBegin(self):
            self._handle_pageBegin()

    doc = _GDoc(
        output_filename,
        pagesize=A4,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM, bottomMargin=BM,
        sidebar_tag=sidebar_tag,
    )

    body_frame = Frame(LM, BM, BW, H - TM - BM, id="body")
    doc.addPageTemplates([
        PageTemplate(id="p1", frames=[body_frame], onPage=_on_page1),
        PageTemplate(id="pN", frames=[body_frame], onPage=_on_page_n),
    ])

    doc.build(story)
    print(f"PDF generated: {output_filename}")
    return output_filename
