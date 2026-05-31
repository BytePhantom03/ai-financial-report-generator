"""
pdf_generator.py — Premium Geojit-Style PDF Report v4
Precise 4-page layout matching the Eternal-Geojit.pdf sample.
Uses canvas for pixel-perfect drawing of structural elements,
Platypus for content tables.
"""
import os, math
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas as CV
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from schema import GeojitReportData
from charts import generate_charts

# ── Page geometry ─────────────────────────────────────────────────────────
W, H = A4          # 595.3 × 841.9 pt
LM   = 16          # left  margin
RM   = 16          # right margin
TM   = 30          # top margin  (below green bar)
BM   = 22          # bottom margin (above footer)
BW   = W - LM - RM  # body width ≈ 563 pt

# ── Geojit brand palette ─────────────────────────────────────────────────
C_BLUE   = colors.HexColor("#004B87")
C_GREEN  = colors.HexColor("#7DBA00")
C_ORANGE = colors.HexColor("#F26522")
C_RED    = colors.HexColor("#CC2200")
C_TEAL   = colors.HexColor("#00A1C6")
C_LGREY  = colors.HexColor("#E4E4E4")
C_XLGREY = colors.HexColor("#F5F5F5")
C_DGREY  = colors.HexColor("#3D3D3D")
C_MGREY  = colors.HexColor("#777777")
C_WHITE  = colors.white
C_BLACK  = colors.black

RATING_C = {"BUY":"#007700","ACCUMULATE":"#007700",
            "HOLD":"#F26522","REDUCE":"#CC2200","SELL":"#CC2200"}


# ─────────────────────────────────────────────────────────────────────────
# Paragraph style factory
# ─────────────────────────────────────────────────────────────────────────
def _make_styles():
    S = getSampleStyleSheet()
    defs = {
        "t5" : dict(fontSize=5,   leading=6.5,  textColor=C_DGREY),
        "t6" : dict(fontSize=6,   leading=7.5,  textColor=C_DGREY),
        "t6b": dict(fontSize=6,   leading=7.5,  textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "t7" : dict(fontSize=7,   leading=9.0,  textColor=C_DGREY),
        "t7b": dict(fontSize=7,   leading=9.0,  textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "t8" : dict(fontSize=8,   leading=10.5, textColor=C_DGREY),
        "t8b": dict(fontSize=8,   leading=10.5, textColor=C_DGREY,  fontName="Helvetica-Bold"),
        "ctr6":dict(fontSize=6,   leading=7.5,  textColor=C_DGREY,  alignment=TA_CENTER),
        "ctr7":dict(fontSize=7,   leading=9,    textColor=C_DGREY,  alignment=TA_CENTER),
        "ctr8":dict(fontSize=8,   leading=10,   textColor=C_WHITE,  alignment=TA_CENTER),
        "bl7" : dict(fontSize=7,  leading=9,    textColor=C_BLUE),
        "bl7b": dict(fontSize=7,  leading=9,    textColor=C_BLUE,   fontName="Helvetica-Bold"),
        "bl9b": dict(fontSize=9,  leading=12,   textColor=C_BLUE,   fontName="Helvetica-Bold"),
        "co"  : dict(fontSize=20, leading=24,   textColor=C_BLUE,   fontName="Helvetica-Bold"),
        "hdl" : dict(fontSize=10, leading=13,   textColor=C_BLUE,   fontName="Helvetica-Bold", spaceAfter=2),
        "sec" : dict(fontSize=9,  leading=12,   textColor=C_BLUE,   fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=3),
        "org9b":dict(fontSize=9,  leading=11,   textColor=C_ORANGE, fontName="Helvetica-Bold"),
        "wh7b":dict(fontSize=7,   leading=9,    textColor=C_WHITE,  fontName="Helvetica-Bold"),
        "disc":dict(fontSize=5.5, leading=7.2,  textColor=C_MGREY,  alignment=TA_JUSTIFY),
    }
    for name, kw in defs.items():
        kw["parent"] = S["Normal"]
        S.add(ParagraphStyle(name, **kw))
    return S


# ─────────────────────────────────────────────────────────────────────────
# Table helpers
# ─────────────────────────────────────────────────────────────────────────
def _tbl(data, cw, hbg=C_LGREY, hfg=C_BLACK, fs=6.5, zebra=True):
    """Standard table: grey or blue header, zebra rows, subtle borders."""
    t = Table(data, colWidths=cw, repeatRows=1)
    cmds = [
        ("BACKGROUND",    (0,0),(-1,0),  hbg),
        ("TEXTCOLOR",     (0,0),(-1,0),  hfg),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), fs),
        ("LEADING",       (0,0),(-1,-1), fs+1.8),
        ("TOPPADDING",    (0,0),(-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1.5),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("ALIGN",         (0,0),(0,-1),  "LEFT"),
        ("ALIGN",         (1,0),(-1,-1), "RIGHT"),
        ("LINEBELOW",     (0,0),(-1,0),  0.7, C_BLUE),
        ("LINEABOVE",     (0,0),(-1,0),  0.7, C_BLUE),
        ("BOX",           (0,0),(-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0),(-1,-1), 0.2, C_LGREY),
    ]
    if zebra:
        cmds.append(("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE, C_XLGREY]))
    t.setStyle(TableStyle(cmds))
    return t


def _kv(rows, cw, fs=6.5):
    """Key-value 2-col table, bold left, right-aligned values."""
    t = Table(rows, colWidths=cw)
    t.setStyle(TableStyle([
        ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
        ("FONTNAME",      (1,0),(1,-1),  "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), fs),
        ("LEADING",       (0,0),(-1,-1), fs+2),
        ("TOPPADDING",    (0,0),(-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1.5),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("ALIGN",         (1,0),(1,-1),  "RIGHT"),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0),(-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0),(-1,-1), 0.2, C_LGREY),
    ]))
    return t


def _sec_hdr(title, S):
    """Blue section header paragraph."""
    return Paragraph(title, S["sec"])


# ─────────────────────────────────────────────────────────────────────────
# Canvas-level page decorations
# ─────────────────────────────────────────────────────────────────────────
def _draw_header(c, title_tag=""):
    """Green top bar + Geojit branding on every page."""
    # Green bar
    c.setFillColor(C_GREEN)
    c.rect(0, H-24, W, 24, fill=1, stroke=0)

    # Left: Retail Equity Research
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(LM, H-16.5, "Retail Equity Research")

    # Right: GEOJIT text logo
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - LM - 2, H-17, "  GEOJIT")
    c.setFont("Helvetica", 5.5)
    c.drawRightString(W - LM - 2, H-22, "PEOPLE YOU PROSPER WITH")

    # Separator line
    c.setStrokeColor(C_LGREY)
    c.setLineWidth(0.5)
    c.line(LM, H-26, W-RM, H-26)


def _draw_footer(c):
    """Green bottom strip + www.geojit.com centred."""
    c.setFillColor(C_GREEN)
    c.rect(0, 0, W, 16, fill=1, stroke=0)

    # G circle
    c.setFillColor(C_WHITE)
    c.circle(14, 8, 6.5, fill=1, stroke=0)
    c.setFillColor(C_GREEN)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(14, 5, "G")

    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(W/2, 5, "www.geojit.com")


def _draw_sidebar_tab(c, text="Q1FY26 Result Update"):
    """Orange vertical tab on the right edge (Page 1 only)."""
    tab_w = 16
    tab_h = 110
    x = W - tab_w
    y = H - 24 - tab_h - 20

    c.setFillColor(C_ORANGE)
    c.rect(x, y, tab_w, tab_h, fill=1, stroke=0)

    c.saveState()
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 6.5)
    c.translate(x + tab_w/2, y + tab_h/2)
    c.rotate(90)
    c.drawCentredString(0, -2.5, text)
    c.restoreState()


def _on_page1(c, doc):
    c.saveState()
    _draw_header(c)
    _draw_footer(c)
    _draw_sidebar_tab(c, f"{doc._sidebar_tag}  Result Update")
    c.restoreState()


def _on_page_n(c, doc):
    c.saveState()
    _draw_header(c)
    _draw_footer(c)
    # Page number
    c.setFillColor(C_MGREY)
    c.setFont("Helvetica", 7)
    c.drawRightString(W-RM, 17, str(doc.page))
    c.restoreState()


# ─────────────────────────────────────────────────────────────────────────
# Rating badge
# ─────────────────────────────────────────────────────────────────────────
def _badge(rating, S):
    clr = colors.HexColor(RATING_C.get(rating.upper(), "#F26522"))
    p   = Paragraph(f'<font color="white" size="11"><b>{rating}</b></font>', S["ctr7"])
    t   = Table([[p]], colWidths=[48], rowHeights=[22])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,0), clr),
        ("ALIGN",         (0,0),(0,0), "CENTER"),
        ("VALIGN",        (0,0),(0,0), "MIDDLE"),
        ("TOPPADDING",    (0,0),(0,0), 3),
        ("BOTTOMPADDING", (0,0),(0,0), 3),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────
# Change-indicator cell  (▲ green / ▼ red)
# ─────────────────────────────────────────────────────────────────────────
def _chg(val, S):
    try:
        v = float(str(val).replace(",","").replace("%","").strip())
        if v > 0:  return Paragraph(f'<font color="#007700">▲ {val}</font>', S["ctr6"])
        if v < 0:  return Paragraph(f'<font color="#CC2200">▼ {val}</font>', S["ctr6"])
    except: pass
    return Paragraph(str(val) if val else "—", S["ctr6"])


# ─────────────────────────────────────────────────────────────────────────
# Financial statement 4-quadrant helper
# ─────────────────────────────────────────────────────────────────────────
def _fs_tbl(title, rows, cw_lbl=88, fs=6):
    if not rows:
        return None
    YRS = ["FY23A","FY24A","FY25A","FY26E","FY27E"]
    cw  = [cw_lbl] + [38]*5
    hdr = [Paragraph(f"<b>{title}</b>", ParagraphStyle("_h", parent=ParagraphStyle("_b"),
           fontSize=fs, leading=fs+2, textColor=C_WHITE, fontName="Helvetica-Bold"))] + YRS
    td  = [hdr] + [[r.metric, r.fy23a, r.fy24a, r.fy25a, r.fy26e, r.fy27e] for r in rows]
    t = Table(td, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  C_BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0),  C_WHITE),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), fs),
        ("LEADING",       (0,0),(-1,-1), fs+1.8),
        ("TOPPADDING",    (0,0),(-1,-1), 1.2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1.2),
        ("LEFTPADDING",   (0,0),(-1,-1), 2.5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 2.5),
        ("ALIGN",         (0,0),(0,-1),  "LEFT"),
        ("ALIGN",         (1,0),(-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0),(-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0),(-1,-1), 0.2, C_LGREY),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────
# MAIN BUILD
# ─────────────────────────────────────────────────────────────────────────
def build_pdf(data: GeojitReportData, output_filename: str) -> str:
    out_dir = os.path.dirname(os.path.abspath(output_filename)) or "."
    os.makedirs(out_dir, exist_ok=True)

    S   = _make_styles()
    v   = data.valuation
    cd  = data.company_data
    rating = (v.rating or "HOLD").upper()

    # determine quarter tag from report_date or default
    import re
    qm = re.search(r'Q\d+?FY\d+', data.report_date or "")
    sidebar_tag = qm.group(0) if qm else "Q1FY26"

    # Generate charts
    chart_dir = os.path.join(out_dir,
        "charts_" + os.path.splitext(os.path.basename(output_filename))[0])
    chart_paths = generate_charts(data, chart_dir)

    story = []
    IS = data.financials.income_statement
    BS = data.financials.balance_sheet
    CF = data.financials.cash_flow
    RT = data.financials.ratios

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 1 — Executive Summary
    # ══════════════════════════════════════════════════════════════════════
    LC = 168          # left column width
    RC = BW - LC - 6  # right column ≈ 373 pt

    # ── LEFT COLUMN ───────────────────────────────────────────────────────
    left = []

    # Company Data
    cd_rows = [
        [Paragraph("<b>Company Data</b>", S["bl7b"]), ""],
        ["Market Cap (Rs.cr)",      cd.market_cap],
        ["52 Wk High – Low (Rs.)",  cd.high_low],
        ["Enterprise Value (Rs.cr)",cd.enterprise_value],
        ["Outstanding Shares (cr)", cd.outstanding_shares],
        ["Free Float (%)",          cd.free_float],
        ["Dividend Yield (%)",      cd.dividend_yield],
        ["6m avg volume (cr)",      cd.avg_volume],
        ["Beta",                    cd.beta],
        ["Face value (Rs.)",        cd.face_value],
    ]
    cd_tbl = Table(cd_rows, colWidths=[104, 60])
    cd_tbl.setStyle(TableStyle([
        ("SPAN",          (0,0),(1,0)),
        ("BACKGROUND",    (0,0),(1,0),  C_LGREY),
        ("FONTNAME",      (0,1),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,1),(1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1),6.5),
        ("LEADING",       (0,0),(-1,-1),8.5),
        ("TOPPADDING",    (0,0),(-1,-1),1.5),
        ("BOTTOMPADDING", (0,0),(-1,-1),1.5),
        ("LEFTPADDING",   (0,0),(-1,-1),3),
        ("RIGHTPADDING",  (0,0),(-1,-1),3),
        ("ALIGN",         (1,1),(1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_WHITE, C_XLGREY]),
        ("BOX",           (0,0),(-1,-1),0.3, C_LGREY),
        ("LINEBELOW",     (0,0),(1,0),  0.7, C_BLUE),
        ("INNERGRID",     (0,0),(-1,-1),0.2, C_LGREY),
    ]))
    left.append(cd_tbl)
    left.append(Spacer(1,5))

    # Shareholding
    sh = data.shareholding[:3]
    if sh:
        sh_rows = [["Shareholding (%)"] + [s.quarter for s in sh]]
        for lbl, attr in [("Promoters","promoters"),("FII's","fiis"),
                          ("MFs/Inst.","mfs_institutions"),("Public","public"),
                          ("Others","others"),("Total","__tot__"),
                          ("Promoter Pledge","promoter_pledge")]:
            row = [lbl]
            for s in sh:
                row.append("100.0" if attr=="__tot__" else str(getattr(s,attr,"-")))
            sh_rows.append(row)
        left.append(_tbl(sh_rows, [70]+[32]*len(sh), fs=6))
        left.append(Spacer(1,5))

    # Price Performance
    pp = data.price_performance[:3]
    if pp:
        pp_rows = [["Price Performance"]+[p.period for p in pp],
                   ["Absolute Return"]+[p.absolute_return for p in pp],
                   ["Absolute Sensex"]+[p.absolute_sensex for p in pp],
                   ["Relative Return*"]+[p.relative_return for p in pp]]
        left.append(_tbl(pp_rows, [72]+[32]*len(pp), fs=6))
        left.append(Spacer(1,3))
        left.append(Paragraph("*over/under performance to benchmark index", S["t5"]))
        left.append(Spacer(1,5))

    # Mini price chart (revenue chart repurposed as trend indicator)
    rc = chart_paths.get("revenue")
    if rc and os.path.exists(rc):
        left.append(Image(rc, width=LC-2, height=95))

    # ── RIGHT COLUMN ──────────────────────────────────────────────────────
    right = []

    # Header block: company name
    right.append(Paragraph("Retail Equity Research", S["t7b"]))
    right.append(Spacer(1,1))
    right.append(Paragraph(data.company_name, S["co"]))
    right.append(Spacer(1,4))

    # Key Changes row  [badge] [Target ▲] [Rating ▼] [Earnings ▼]
    arr_up   = Paragraph('<font color="#007700" size="10">▲</font>', S["ctr7"])
    arr_dn   = Paragraph('<font color="#CC2200" size="10">▼</font>', S["ctr7"])
    kc_top = [["Key Changes", "Target",  "Rating",  "Earnings"],
              [_badge(rating, S), arr_up, arr_dn, arr_dn]]
    kc_t = Table(kc_top, colWidths=[86,65,65,65])
    kc_t.setStyle(TableStyle([
        ("FONTSIZE",       (0,0),(-1,-1),7),
        ("FONTNAME",       (0,0),(-1,0), "Helvetica-Bold"),
        ("ALIGN",          (0,0),(-1,-1),"CENTER"),
        ("VALIGN",         (0,0),(-1,-1),"MIDDLE"),
        ("BACKGROUND",     (0,0),(-1,0), C_LGREY),
        ("LINEBELOW",      (0,0),(-1,0), 0.5, C_LGREY),
        ("TOPPADDING",     (0,0),(-1,-1),2),
        ("BOTTOMPADDING",  (0,0),(-1,-1),2),
        ("BOX",            (0,0),(-1,-1),0.3, C_LGREY),
    ]))
    right.append(kc_t)
    right.append(Spacer(1,3))

    # Stock ID strip: Stock Type | Bloomberg | Sensex | NSE | BSE | Time Frame
    id_rows = [
        ["Stock Type","Bloomberg Code","Sensex","NSE Code","BSE Code","Time Frame"],
        [v.stock_type or "Large Cap", v.bloomberg or "—", v.sensex or "—",
         v.nse_code or "—", v.bse_code or "—", v.time_frame or "12 Months"]
    ]
    right.append(_tbl(id_rows, [58,78,48,50,50,52], fs=6))
    right.append(Spacer(1,3))

    # Data as of line
    right.append(Paragraph(
        f'Data as of {data.report_date}, 16:23hrs', S["t6"]))
    right.append(Spacer(1,4))

    # Target / CMP / Return top-right block
    tcr_data = [
        [Paragraph("Target", S["t6b"]),  Paragraph(f"Rs. {v.target}", S["t8b"])],
        [Paragraph("CMP",    S["t6b"]),  Paragraph(f"Rs. {v.cmp}",    S["t8b"])],
        [Paragraph("Return", S["t6b"]),  Paragraph(v.upside or "—",   S["org9b"])],
    ]
    tcr = Table(tcr_data, colWidths=[52,85])
    tcr.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1),7),
        ("ALIGN",         (1,0),(1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1),1.5),
        ("BOTTOMPADDING", (0,0),(-1,-1),1.5),
        ("LEFTPADDING",   (0,0),(-1,-1),3),
        ("LINEBELOW",     (0,-1),(-1,-1),0.4, C_LGREY),
    ]))
    right.append(tcr)
    right.append(Spacer(1,4))

    right.append(Paragraph(
        f'Sector:  <b>{data.sector}</b>', S["t7"]))
    right.append(Spacer(1,3))
    right.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    right.append(Spacer(1,4))

    # Bold headline
    headline = data.highlights[0] if data.highlights else f"{data.company_name}: Financial Update"
    right.append(Paragraph(headline, S["hdl"]))
    right.append(Spacer(1,3))

    # Company description
    right.append(Paragraph(data.company_description, S["t7"]))
    right.append(Spacer(1,4))

    # Bullet highlights (skip first since it's the headline)
    for hl in (data.highlights[1:] if len(data.highlights) > 1 else data.highlights):
        right.append(Paragraph(f"\u2022\u2002{hl}", S["t7"]))
        right.append(Spacer(1,1))
    right.append(Spacer(1,5))

    right.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    right.append(Spacer(1,3))

    # Outlook & Valuation
    right.append(_sec_hdr("Outlook & Valuation", S))
    right.append(Spacer(1,2))
    right.append(Paragraph(data.outlook_valuation, S["t7"]))
    right.append(Spacer(1,5))

    right.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    right.append(Spacer(1,3))

    # Quarterly Financials table
    right.append(_sec_hdr("Quarterly Financials Consolidated", S))
    right.append(Spacer(1,2))
    q_cw = [55,42,42,58,42,58]
    q_hdr = ["Rs.cr","Q1FY26","Q1FY25","YoY Growth (%)","Q4FY25","QoQ Growth (%)"]
    q_rows = [q_hdr]
    for metric in ["Sales","EBITDA","EBIT","Margin (%)","PBT","Rep. PAT","Adj. PAT","Adj. EPS (Rs)"]:
        row = next((r for r in IS if metric.lower().split()[0] in r.metric.lower()), None)
        if row:
            q_rows.append([row.metric, row.fy25a, row.fy24a, "—", row.fy25a, "—"])
    if len(q_rows) == 1:
        for m in ["Sales","EBITDA","PAT"]:
            q_rows.append([m,"—","—","—","—","—"])
    right.append(_tbl(q_rows, q_cw, hbg=C_BLUE, hfg=C_WHITE, fs=6))
    right.append(Spacer(1,5))

    # Annual Key Estimates table
    right.append(Paragraph("Y.E March (cr)", S["t6b"]))
    right.append(Spacer(1,2))
    ann_hdr = ["Y.E March (cr)", "FY25A", "FY26E", "FY27E", "Growth %", "Growth %"]
    ann_rows = [["Y.E March (cr)","FY25A","FY26E","FY27E","FY26E Chg","FY27E Chg"]]
    added = 0
    for metric in ["Sales","Revenue","Net interest income",
                   "EBITDA","EBITDA Margin (%)","PAT Adjusted",
                   "Adj. PAT","Reported PAT",
                   "Adjusted EPS","Adj EPS","P/E","P/B","EV/EBITDA","ROE (%)","D/E"]:
        for pool in [IS, RT]:
            row = next((r for r in pool if metric.lower().rstrip("()") in r.metric.lower()), None)
            if row and added < 10:
                # compute change % where possible
                def chg(a, b):
                    try:
                        fa, fb = float(str(a).replace(",","")), float(str(b).replace(",",""))
                        if fa: return f"{(fb-fa)/abs(fa)*100:.1f}"
                    except: pass
                    return "—"
                c26 = chg(row.fy24a, row.fy26e)
                c27 = chg(row.fy24a, row.fy27e)
                ann_rows.append([row.metric, row.fy25a, row.fy26e, row.fy27e, c26, c27])
                added += 1; break
    if added == 0:
        for m in ["Sales","EBITDA","PAT"]:
            ann_rows.append([m,"—","—","—","—","—"])
    right.append(_tbl(ann_rows, [105,42,42,42,44,44],
                      hbg=C_BLUE, hfg=C_WHITE, fs=6.5))

    # ── Assemble Page 1 two-column master ─────────────────────────────────
    pg1 = Table([[left, right]], colWidths=[LC, RC],
                style=TableStyle([
                    ("VALIGN",       (0,0),(-1,-1),"TOP"),
                    ("LEFTPADDING",  (0,0),(-1,-1),0),
                    ("RIGHTPADDING", (0,0),(-1,-1),0),
                    ("TOPPADDING",   (0,0),(-1,-1),0),
                    ("BOTTOMPADDING",(0,0),(-1,-1),0),
                ]))
    story.append(pg1)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 2 — Key Highlights + 4 Charts + Change in Estimates
    # ══════════════════════════════════════════════════════════════════════
    story.append(_sec_hdr("Key highlights", S))
    story.append(Spacer(1,3))
    for hl in data.highlights:
        story.append(Paragraph(f"\u2022\u2002{hl}", S["t7"]))
        story.append(Spacer(1,2))
    story.append(Spacer(1,8))

    # 2×2 chart grid
    C_W, C_H = 2.58*inch, 1.88*inch
    chart_keys = ["revenue","gov","ebitda","pat"]
    chart_imgs  = []
    for k in chart_keys:
        p = chart_paths.get(k)
        if p and os.path.exists(p):
            chart_imgs.append(Image(p, width=C_W, height=C_H))
        else:
            chart_imgs.append(Spacer(C_W, C_H))

    ch_tbl = Table(
        [[chart_imgs[0], chart_imgs[1]],
         [chart_imgs[2], chart_imgs[3]]],
        colWidths=[C_W+6, C_W+6],
        style=TableStyle([
            ("ALIGN",        (0,0),(-1,-1),"CENTER"),
            ("VALIGN",       (0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",   (0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ]))
    story.append(ch_tbl)
    story.append(Spacer(1,8))

    # Change in Estimates
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LGREY))
    story.append(Spacer(1,4))
    story.append(_sec_hdr("Change in Estimates", S))
    story.append(Spacer(1,3))

    E_CW = [72, 52, 52, 52, 52, 50, 50]
    e_r0 = [Paragraph("Year / Rs cr", S["t6b"]),
            Paragraph("Old estimates", S["wh7b"]), "",
            Paragraph("New estimates", S["wh7b"]), "",
            Paragraph("Change (%)",    S["wh7b"]), ""]
    e_r1 = ["", "FY26E","FY27E","FY26E","FY27E","FY26E","FY27E"]
    est_rows = [e_r0, e_r1]
    for e in data.estimates:
        est_rows.append([e.metric,
                         e.old_estimate_fy26, e.old_estimate_fy27,
                         e.new_estimate_fy26, e.new_estimate_fy27,
                         _chg(e.change_fy26, S), _chg(e.change_fy27, S)])

    t_est = Table(est_rows, colWidths=E_CW, repeatRows=2)
    t_est.setStyle(TableStyle([
        # Row 0: section labels
        ("BACKGROUND",    (0,0),(-1,0),  C_LGREY),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("BACKGROUND",    (1,0),(2,0),   C_BLUE),
        ("BACKGROUND",    (3,0),(4,0),   C_BLUE),
        ("BACKGROUND",    (5,0),(6,0),   C_BLUE),
        ("SPAN",          (1,0),(2,0)),
        ("SPAN",          (3,0),(4,0)),
        ("SPAN",          (5,0),(6,0)),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("ALIGN",         (0,0),(0,-1),  "LEFT"),
        # Row 1: sub-headers
        ("BACKGROUND",    (0,1),(-1,1),  C_XLGREY),
        ("FONTNAME",      (0,1),(-1,1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 6.5),
        ("LEADING",       (0,0),(-1,-1), 8.5),
        ("TOPPADDING",    (0,0),(-1,-1), 1.5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1.5),
        ("LEFTPADDING",   (0,0),(-1,-1), 3),
        ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ("ROWBACKGROUNDS",(0,2),(-1,-1), [C_WHITE, C_XLGREY]),
        ("BOX",           (0,0),(-1,-1), 0.3, C_LGREY),
        ("INNERGRID",     (0,0),(-1,-1), 0.2, C_LGREY),
        ("LINEBELOW",     (0,0),(-1,0),  0.5, C_LGREY),
        ("LINEBELOW",     (0,1),(-1,1),  0.7, C_BLUE),
    ]))
    story.append(t_est)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 3 — Consolidated Financials (4-quadrant)
    # ══════════════════════════════════════════════════════════════════════
    story.append(_sec_hdr("Consolidated Financials", S))
    story.append(Spacer(1,4))

    HALF = (BW - 8) / 2    # ≈ 277 pt per column
    LBL  = 85               # metric label width
    YW   = int((HALF - LBL) / 5)  # year column width ≈ 38

    def _quad(title, rows, lbl=LBL, yw=YW):
        t = _fs_tbl(title, rows, cw_lbl=lbl, fs=6)
        return t

    t_pl = _quad("Y.E March (Rs. Cr)",  IS)
    t_bs = _quad("Y.E March (Rs. Cr)",  BS)
    t_cf = _quad("Y.E March",           CF)
    t_rt = _quad("Y.E March",           RT)

    def _col(label, tbl):
        if tbl is None:
            return [Paragraph(f"<b>{label}</b>", S["bl7b"]),
                    Spacer(1,2),
                    Paragraph("No data extracted.", S["t6"])]
        return [Paragraph(f"<b>{label}</b>", S["bl7b"]),
                Spacer(1,2), tbl]

    row1 = Table(
        [[_col("Profit & Loss", t_pl), _col("Balance Sheet", t_bs)]],
        colWidths=[HALF, HALF],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                          ("LEFTPADDING",(0,0),(-1,-1),0),
                          ("RIGHTPADDING",(0,0),(0,-1),5),
                          ("RIGHTPADDING",(1,0),(1,-1),0),
                          ("TOPPADDING",(0,0),(-1,-1),0),
                          ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(row1)
    story.append(Spacer(1,6))

    row2 = Table(
        [[_col("Cashflow", t_cf), _col("Ratio", t_rt)]],
        colWidths=[HALF, HALF],
        style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                          ("LEFTPADDING",(0,0),(-1,-1),0),
                          ("RIGHTPADDING",(0,0),(0,-1),5),
                          ("RIGHTPADDING",(1,0),(1,-1),0),
                          ("TOPPADDING",(0,0),(-1,-1),0),
                          ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
    story.append(row2)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 4 — Recommendation + Rating Criteria + Disclosures
    # ══════════════════════════════════════════════════════════════════════
    story.append(_sec_hdr("Recommendation Summary  —  (last 3 years)", S))
    story.append(Spacer(1,4))

    # Recommendation chart (mini line chart image if available, else table only)
    rec_chart = chart_paths.get("rec")
    if rec_chart and os.path.exists(rec_chart):
        story.append(Image(rec_chart, width=BW*0.55, height=70))
        story.append(Spacer(1,4))

    if data.recommendation_history:
        rc_rows = [["Dates","Rating","Target"]]
        for r in data.recommendation_history:
            rc_rows.append([r.get("Date","—"), r.get("Rating","—"), r.get("Target","—")])
        story.append(_tbl(rc_rows, [130,90,90], fs=7))
    else:
        story.append(Paragraph("No prior recommendation history available.", S["t7"]))

    story.append(Spacer(1,10))
    story.append(_sec_hdr("Investment Rating Criteria", S))
    story.append(Spacer(1,3))

    irc = [["Ratings",      "Large caps",            "Midcaps",               "Small Caps"],
           ["Buy",           "Upside is above 10%",   "Upside is above 15%",   "Upside is above 20%"],
           ["Accumulate",    "—",                     "Upside between 10%-15%","Upside between 10%-20%"],
           ["Hold",          "Upside between 0%-10%", "Upside between 0%-10%", "Upside between 0%-10%"],
           ["Reduce/sell",   "Downside is more than 0%","Downside is more than 0%","Downside is more than 0%"],
           ["Not rated/Neutral","—",                  "—",                     "—"]]
    story.append(_tbl(irc, [72,148,148,148], fs=7))
    story.append(Spacer(1,4))
    story.append(Paragraph(
        "Buy: Acquire at Current Market Price (CMP), with the target mentioned in the note.  "
        "Accumulate: Partial buying or to accumulate as CMP dips in the future.  "
        "Hold: Hold the stock with the expected target mentioned in the note.  "
        "Reduce: Reduce your exposure to the stock due to limited upside.  "
        "Sell: Exit from the stock.", S["disc"]))
    story.append(Spacer(1,8))

    story.append(HRFlowable(width="100%", thickness=0.6, color=C_LGREY))
    story.append(Spacer(1,4))
    story.append(Paragraph("DISCLAIMER & DISCLOSURES", S["t7b"]))
    story.append(Spacer(1,3))
    disc_txt = (
        "<b>Certification:</b> The analyst(s) of this Report hereby certifies that all the views expressed in this research report "
        "reflect personal views about any or all of the subject issuer or securities. This report has been prepared by the Research "
        "Team of Geojit Financial Services Limited (hereinafter referred to as GIL). CRISIL has provided research support in "
        "preparation of this research report. The target price and recommendation are strictly GIL's views and are NOT PROVIDED by "
        "CRISIL. CRISIL expresses no opinion on valuation and has no financial liability.<br/><br/>"
        "<b>Standard Warning:</b> Investment in securities market are subject to market risks. Read all the related documents "
        "carefully before investing.<br/><br/>"
        "The recommendations are based on 12 month horizon, unless otherwise specified. The investment ratings are on absolute "
        "positive/negative return basis. It is possible that due to volatile price fluctuation in the near to medium term, there "
        "could be a temporary mismatch to rating. For rating definition and other disclaimers, please refer to our website.<br/><br/>"
        "<b>Regulatory Disclosures:</b> Geojit Financial Services Ltd. and its subsidiaries are registered with SEBI as a Research "
        "Analyst (SEBI Reg. No. INH200000345). GIL confirms that (i) it has no financial interest in the subject company, (ii) "
        "GIL's associates have no actual/beneficial ownership of 1% or more in the subject company.<br/><br/>"
        "<b>Note:</b> This report was auto-generated using an AI-powered financial data extraction pipeline. All data is sourced "
        "directly from the uploaded context document. Please verify all figures independently before making investment decisions. "
        "Missing fields are marked with '—'.<br/><br/>"
        "<b>Geojit Financial Services Ltd.</b> Registered Office: 7th Floor 34/659-P, Civil Line Road, Padivattom, Kochi-682024, "
        "Kerala, India. Phone: +91 484-2901000 &nbsp; Website: www.geojit.com &nbsp; SEBI Reg. No.: INH200000345 &nbsp; "
        "CIN: U67120KL1994PLC008403 &nbsp; GSTIN: 32AAACG4590D1ZX"
    )
    story.append(Paragraph(disc_txt, S["disc"]))

    # ── Build the document ────────────────────────────────────────────────
    class _Doc(BaseDocTemplate):
        def __init__(self, *a, **kw):
            self._sidebar_tag = kw.pop("sidebar_tag", "Q1FY26")
            super().__init__(*a, **kw)

        def handle_pageBegin(self):
            self._handle_pageBegin()

    doc = _Doc(output_filename, pagesize=A4,
               leftMargin=LM, rightMargin=RM,
               topMargin=TM, bottomMargin=BM,
               sidebar_tag=sidebar_tag)

    frame = Frame(LM, BM, BW, H - TM - BM, id="main")
    doc.addPageTemplates([
        PageTemplate(id="p1", frames=[frame], onPage=_on_page1),
        PageTemplate(id="pN", frames=[frame], onPage=_on_page_n),
    ])
    # Switch from p1 → pN after page 1
    from reportlab.platypus import NextPageTemplate
    story.insert(story.index(next(x for x in story if isinstance(x, PageBreak))),
                 NextPageTemplate("pN"))

    doc.build(story)
    print(f"PDF generated: {output_filename}")
    return output_filename
