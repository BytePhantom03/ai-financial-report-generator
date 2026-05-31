"""
Smart Financial Data Extractor - Enhanced v2
Extracts structured financial data from documents using domain-aware
regex + NLP patterns. Supports banking, FMCG, tech, retail sectors.
Falls back to LLM if an API key with balance is available.
"""
import os
import re
import json

try:
    from openai import OpenAI
    import openai as _openai_module
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from schema import (
    GeojitReportData, CompanyData, ShareholdingQuarter, PricePerformanceRow,
    ValuationMetric, EstimatesRow, StatementRow, FinancialsBundle
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _num(s: str) -> str:
    """Clean and return a number string, or '-'."""
    if not s:
        return "-"
    s = s.strip().replace(",", "")
    try:
        float(s.replace("%", "").replace("(", "-").replace(")", ""))
        return s
    except ValueError:
        return "-"


def _find(text: str, *patterns) -> str:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return "-"


def _find_row(text: str, label: str, n_cols: int = 5) -> list:
    """
    Find a table row starting with `label` and return up to n_cols values.
    Handles both space and tab delimiters.
    """
    escaped = re.escape(label)
    pat = rf'{escaped}[^\d\n]*([\d,.()\-]+(?:\.\d+)?)\s+([\d,.()\-]+(?:\.\d+)?)\s+([\d,.()\-]+(?:\.\d+)?)\s*([\d,.()\-]+(?:\.\d+)?)?\s*([\d,.()\-]+(?:\.\d+)?)?'
    m = re.search(pat, text, re.IGNORECASE)
    if m:
        return [_num(g) for g in m.groups()[:n_cols]]
    return ["-"] * n_cols


def _detect_sector(text: str) -> str:
    t = text.lower()
    # Check more-specific sectors FIRST before generic finance
    if any(k in t for k in ["quick commerce", "food delivery", "blinkit", "zomato", "hyperpure"]):
        return "Internet & Catalogue Retail"
    if any(k in t for k in ["npa", "nii", "net interest income", "deposits", "advances", "banking", "casa"]):
        return "Banking & Financial Services"
    if any(k in t for k in ["pharma", "drug", "api", "formulation"]):
        return "Pharmaceuticals"
    if any(k in t for k in ["it services", "software", "digital services", "infosys", "wipro", "tcs"]):
        return "Information Technology"
    if any(k in t for k in ["automobile", "car", "vehicle", "ev"]):
        return "Automobiles"
    if any(k in t for k in ["cement", "steel", "metal"]):
        return "Metals & Materials"
    return "Diversified"


def _extract_highlights(text: str) -> list:
    """Extract meaningful bullet-point highlights from text."""
    bullets = []
    for line in text.split("\n"):
        line = line.strip()
        if re.match(r'^[•\-▪*]\s+', line):
            clean = re.sub(r'^[•\-▪*]\s+', '', line).strip()
            if 30 < len(clean) < 400:
                bullets.append(clean)
        if len(bullets) >= 6:
            break

    if len(bullets) < 3:
        # Extract sentences with key financial keywords
        for sent in re.split(r'(?<=[.!?])\s+', text):
            sent = sent.strip()
            if any(kw in sent.lower() for kw in ["grew", "increased", "decreased", "surged",
                                                   "revenue", "profit", "margin", "npa", "deposits"]):
                if 40 < len(sent) < 350:
                    bullets.append(sent)
            if len(bullets) >= 6:
                break
    return bullets[:6] if bullets else ["Key financial highlights extracted from uploaded document."]


def _extract_shareholding(text: str) -> list:
    """Extract shareholding table data."""
    quarters = re.findall(r'Q\d[-\s]?(?:FY)?\d{2,4}', text)
    quarters = list(dict.fromkeys(quarters))[:3]
    if not quarters:
        quarters = ["Q1FY26", "Q4FY25", "Q3FY25"]

    result = []
    for q in quarters:
        # Try to find numbers after the quarter label
        prom = _find(text, rf'Promoters?\s+[\d.]+\s+([\d.]+)\s+[\d.]+', rf'Promoters?\s+([\d.]+)')
        fii  = _find(text, rf"FII'?s?\s+[\d.]+\s+([\d.]+)\s+[\d.]+", rf"FII'?s?\s+([\d.]+)")
        mf   = _find(text, rf'MFs?[/\s]Inst\w*\s+[\d.]+\s+([\d.]+)\s+[\d.]+', rf'MF\w*\s+([\d.]+)')
        pub  = _find(text, rf'Public\s+[\d.]+\s+([\d.]+)\s+[\d.]+', rf'Public\s+([\d.]+)')
        result.append(ShareholdingQuarter(
            quarter=q, promoters=prom, fiis=fii,
            mfs_institutions=mf, public=pub, others="-", promoter_pledge="-"
        ))
    return result


# ─────────────────────────────────────────────
# Domain-Specific Extractors
# ─────────────────────────────────────────────
def _extract_banking(text: str, company_name: str) -> FinancialsBundle:
    """Specialized extractor for banking P&L + balance sheet."""
    income = []
    for label in ["Net interest income", "Non-interest income", "Fee income",
                  "Core operating income", "Operating expenses", "Employee expenses",
                  "Core operating profit", "Provisions", "Profit before tax",
                  "Tax", "Profit after tax"]:
        row = _find_row(text, label)
        income.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                   fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    balance = []
    for label in ["Total assets", "Advances", "Deposits", "Net worth",
                  "Borrowings", "Investments", "Cash & bank balances"]:
        row = _find_row(text, label)
        balance.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                    fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    ratios = []
    for label in ["Net interest margin", "Cost-to-income", "Return on average assets",
                  "Standalone return on equity", "Gross NPA ratio", "Net NPA ratio",
                  "Provision coverage ratio", "Weighted average EPS", "Book value"]:
        row = _find_row(text, label)
        ratios.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                   fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    return FinancialsBundle(income_statement=income, balance_sheet=balance,
                            cash_flow=[], ratios=ratios)


def _extract_generic(text: str, company_name: str) -> FinancialsBundle:
    """Generic P&L extractor for non-banking sectors."""
    income = []
    for label in ["Sales", "Revenue", "EBITDA", "Depreciation", "EBIT",
                  "Interest", "Other Income", "PBT", "Tax", "Reported PAT",
                  "Adj. PAT", "Adj EPS", "No. of shares"]:
        row = _find_row(text, label)
        income.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                   fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    balance = []
    for label in ["Cash", "Accts. Receivable", "Inventories", "Other Cur. Assets",
                  "Investments", "Net Fixed Assets", "Intangible Assets",
                  "Total Assets", "Current Liabilities", "Debt Funds",
                  "Equity Capital", "Shareholder Funds", "Total Liabilities", "BVPS"]:
        row = _find_row(text, label)
        balance.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                    fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    cashflow = []
    for label in ["C.F. Operation", "Capital exp.", "C.F - Investment",
                  "C.F - Finance", "Chg. in cash", "Closing Cash"]:
        row = _find_row(text, label)
        cashflow.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                     fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    ratios = []
    for label in ["EBITDA margin", "EBIT margin", "Net profit mgn.",
                  "ROE", "ROCE", "Receivables", "Inventory", "Payables",
                  "Current ratio", "EV/Sales", "EV/EBITDA", "P/E", "P/BV"]:
        row = _find_row(text, label)
        ratios.append(StatementRow(metric=label, fy23a=row[0], fy24a=row[1],
                                   fy25a=row[2], fy26e=row[3], fy27e=row[4]))

    return FinancialsBundle(income_statement=income, balance_sheet=balance,
                            cash_flow=cashflow, ratios=ratios)


# ─────────────────────────────────────────────
# Main Smart Extractor
# ─────────────────────────────────────────────
def _smart_extract(company_name: str, text: str) -> GeojitReportData:
    sector = _detect_sector(text)
    is_bank = "Banking" in sector or "Financial Services" in sector

    # ── Company description ──
    paras = [p.strip() for p in re.split(r'\n{2,}', text) if len(p.strip()) > 80]
    description = paras[0][:500] if paras else f"{company_name} is a leading company in {sector}."

    # ── Highlights ──
    highlights = _extract_highlights(text)

    # ── Market cap ──
    market_cap = _find(text,
        r'[Mm]arket\s*[Cc]ap\s*[\(Rs\.cr\)]*\s*([\d,]+)',
        r'Market Cap.*?([\d,]+)\s*$')

    # ── EPS, CMP, Target, Rating ──
    cmp   = _find(text, r'CMP\s+Rs\.?\s*([\d.]+)', r'CMP\s+([\d.]+)')
    tgt   = _find(text, r'[Tt]arget\s+Rs\.?\s*([\d.]+)', r'Target\s+([\d.]+)')
    upside= _find(text, r'[Rr]eturn\s+\+?([\d.]+)%', r'\+([\d.]+)%')
    rating= _find(text, r'\b(BUY|HOLD|SELL|ACCUMULATE|REDUCE)\b')
    if rating == "-": rating = "HOLD"

    bloomberg = _find(text, r'Bloomberg\s+Code\s+([A-Z:]+)', r'([A-Z]+:[A-Z]+)')
    nse = _find(text, r'NSE\s+Code\s+([A-Z0-9]+)', r'NSE[:\s]+([A-Z0-9]+)')
    bse = _find(text, r'BSE\s+Code\s+(\d+)', r'BSE[:\s]+(\d+)')
    sensex = _find(text, r'Sensex\s+([\d,]+)', r'(\d{4,6})')

    # ── Date ──
    date = _find(text,
        r'(\d{1,2}(?:st|nd|rd|th)\s+\w+,?\s+\d{4})',
        r'(\w+ \d{1,2},? \d{4})',
        r'(\d{4}-\d{2}-\d{2})')
    if date == "-":
        import datetime; date = datetime.date.today().strftime("%d %B, %Y")

    # ── Outlook paragraph ──
    outlook_match = re.search(r'Outlook\s*&?\s*Valuation\s*\n(.*?)(?:\n\n|\Z)',
                              text, re.IGNORECASE | re.DOTALL)
    if outlook_match:
        outlook = outlook_match.group(1).strip()[:600]
    else:
        tone = "strong growth" if any(w in text.lower() for w in
               ["surged", "grew", "record", "highest"]) else "stable performance"
        outlook = (f"{company_name} continues to demonstrate {tone}. "
                   f"The company operates in the {sector} sector with a diversified "
                   f"revenue mix. Investors should review risk factors carefully before "
                   f"making investment decisions. Rating: {rating}.")

    # ── Financials ──
    if is_bank:
        financials = _extract_banking(text, company_name)
    else:
        financials = _extract_generic(text, company_name)

    # Drop all-dash rows for cleanliness
    def _clean_rows(rows):
        return [r for r in rows if not all(
            v == "-" for v in [r.fy23a, r.fy24a, r.fy25a, r.fy26e, r.fy27e])]

    financials.income_statement = _clean_rows(financials.income_statement)
    financials.balance_sheet    = _clean_rows(financials.balance_sheet)
    financials.cash_flow        = _clean_rows(financials.cash_flow)
    financials.ratios           = _clean_rows(financials.ratios)

    # ── Estimates (check for change table) ──
    estimates = []
    est_block = re.search(
        r'(?:Change in Estimates|Old estimates.*?New estimates)(.*?)(?:Key highlights|\Z)',
        text, re.IGNORECASE | re.DOTALL)
    if est_block:
        block = est_block.group(1)
        for metric in ["Revenue", "EBITDA", "Margins", "Adj. PAT", "EPS"]:
            row = _find_row(block, metric, 4)
            if any(v != "-" for v in row):
                estimates.append(EstimatesRow(
                    metric=metric,
                    old_estimate_fy26=row[0], old_estimate_fy27=row[1],
                    new_estimate_fy26=row[2], new_estimate_fy27=row[3],
                    change_fy26="-", change_fy27="-"
                ))

    if not estimates:
        estimates = [EstimatesRow(metric=m, old_estimate_fy26="-", new_estimate_fy26="-",
                                  old_estimate_fy27="-", new_estimate_fy27="-",
                                  change_fy26="-", change_fy27="-")
                     for m in ["Revenue", "EBITDA", "Adj. PAT", "EPS"]]

    # ── Recommendation history ──
    rec_history = []
    for m in re.finditer(r'(\d{1,2}-\w{3}-\d{2,4})\s+(BUY|HOLD|SELL|ACCUMULATE|REDUCE)\s+([\d.]+)',
                         text, re.IGNORECASE):
        rec_history.append({"Date": m.group(1), "Rating": m.group(2), "Target": m.group(3)})

    # ── Price Performance ──
    pp = []
    for period, key in [("3 Month","3 Month"), ("6 Month","6 Month"), ("1 Year","1 Year")]:
        val = _find(text, rf'{re.escape(period)}\s+([\d.\-]+)%')
        pp.append(PricePerformanceRow(period=period,
                                      absolute_return=f"{val}%" if val != "-" else "-",
                                      absolute_sensex="-", relative_return="-"))

    shareholding = _extract_shareholding(text)

    return GeojitReportData(
        company_name=company_name,
        sector=sector,
        report_date=date,
        company_description=description,
        highlights=highlights,
        outlook_valuation=outlook,
        company_data=CompanyData(
            market_cap=market_cap,
            high_low=_find(text, r'52\s*[Ww]eek\s*High\s*[—\-]\s*Low\s*[\(Rs.\)]*\s*([\d,. \-—]+)'),
            enterprise_value=_find(text, r'Enterprise\s*Value.*?([\d,]+)'),
            outstanding_shares=_find(text, r'Outstanding\s*Shares.*?([\d.]+)'),
            free_float=_find(text, r'Free\s*Float.*?([\d.]+)'),
            dividend_yield=_find(text, r'Dividend\s*Yield.*?([\d.]+)'),
            avg_volume=_find(text, r'6m\s*average\s*volume.*?([\d.]+)'),
            beta=_find(text, r'Beta\s+([\d.]+)'),
            face_value=_find(text, r'[Ff]ace\s*value.*?([\d.]+)')
        ),
        shareholding=shareholding,
        price_performance=pp,
        valuation=ValuationMetric(
            target=tgt, cmp=cmp, upside=f"+{upside}%" if upside != "-" else "-",
            rating=rating, bloomberg=bloomberg, sensex=sensex,
            nse_code=nse, bse_code=bse,
            time_frame="12 Months",
            stock_type=_find(text, r'(Large\s*Cap|Mid\s*Cap|Small\s*Cap)')
        ),
        estimates=estimates,
        financials=financials,
        recommendation_history=rec_history
    )


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def parse_financial_document(company_name: str, document_text: str) -> GeojitReportData:
    """
    Extract structured financial data.
    Tries OpenAI → DeepSeek → Smart Rule-based engine.
    """
    if OPENAI_AVAILABLE:
        for provider, key, base_url, model in [
            ("OpenAI",   os.environ.get("OPENAI_API_KEY",""),   None,                       "gpt-4o-mini"),
            ("DeepSeek", os.environ.get("DEEPSEEK_API_KEY",""), "https://api.deepseek.com/v1", "deepseek-chat"),
        ]:
            if not key:
                continue
            try:
                kwargs = {"api_key": key}
                if base_url:
                    kwargs["base_url"] = base_url
                client = OpenAI(**kwargs)

                if provider == "OpenAI":
                    resp = client.beta.chat.completions.parse(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Expert financial analyst. Extract structured data precisely."},
                            {"role": "user",   "content": _build_prompt(company_name, document_text)},
                        ],
                        response_format=GeojitReportData,
                    )
                    print(f"SUCCESS: Used {provider} for extraction.")
                    return resp.choices[0].message.parsed
                else:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "Expert financial analyst. Output valid JSON only."},
                            {"role": "user",   "content": _build_prompt(company_name, document_text)},
                        ],
                        response_format={"type": "json_object"},
                    )
                    data = json.loads(resp.choices[0].message.content)
                    print(f"SUCCESS: Used {provider} for extraction.")
                    return GeojitReportData(**data)
            except Exception as e:
                print(f"{provider} failed: {e}")

    print("INFO: Using smart rule-based extraction engine.")
    return _smart_extract(company_name, document_text)


def _build_prompt(company_name: str, text: str) -> str:
    return f"""Extract ALL available financial data for {company_name} from this document.
Return a JSON object matching the GeojitReportData schema exactly.
Use "-" for any missing field. Do NOT hallucinate numbers.

Required top-level fields:
company_name, sector, report_date, company_description (2-3 sentences),
highlights (5-6 bullet strings), outlook_valuation (1 paragraph),
company_data, shareholding (list), price_performance (list),
valuation, estimates (list), financials (income_statement, balance_sheet, cash_flow, ratios each
  as list of {{metric, fy23a, fy24a, fy25a, fy26e, fy27e}}),
recommendation_history (list of {{Date, Rating, Target}})

Document (first 12000 chars):
{text[:12000]}"""
