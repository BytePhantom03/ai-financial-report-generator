"""
Gemini 2.0 Flash extractor.
Sends the raw PDF file to Gemini Files API (multimodal) — no text preprocessing.
Extracts all financial data including tables embedded in chart images.
"""
import json
import os
import time

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from schema import (
    GeojitReportData, CompanyData, ShareholdingQuarter,
    PricePerformanceRow, ValuationMetric, EstimatesRow,
    StatementRow, FinancialsBundle
)

EXTRACTION_PROMPT = """
You are a senior equity research analyst at Geojit Financial Services.
Extract ALL financial data from this document for {company_name}.

Return ONLY a valid JSON object. No markdown, no backticks, no explanation.
Use "-" (dash string) for any field you cannot find. Never use null or None.

Required JSON structure:
{{
  "company_name": "{company_name}",
  "sector": "string e.g. Banking & Financial Services",
  "report_date": "string e.g. 29th July, 2025",
  "company_description": "2-3 sentence description of what the company does",
  "highlights": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "outlook_valuation": "full paragraph from Outlook & Valuation section",

  "company_data": {{
    "market_cap": "number string in Rs. cr e.g. 295735",
    "high_low": "e.g. 314 - 190",
    "enterprise_value": "number string",
    "outstanding_shares": "number string in cr",
    "free_float": "number string in %",
    "dividend_yield": "number string",
    "avg_volume": "number string",
    "beta": "number string",
    "face_value": "number string"
  }},

  "valuation": {{
    "rating": "BUY or HOLD or SELL or ACCUMULATE or REDUCE",
    "target": "number string",
    "cmp": "number string",
    "upside": "e.g. +10%",
    "bloomberg": "ticker code",
    "sensex": "index value",
    "nse_code": "e.g. ETERNAL",
    "bse_code": "e.g. 543320",
    "time_frame": "12 Months",
    "stock_type": "Large Cap or Mid Cap or Small Cap"
  }},

  "shareholding": [
    {{
      "quarter": "Q1FY26",
      "promoters": "% value",
      "fiis": "% value",
      "mfs_institutions": "% value",
      "public": "% value",
      "others": "% value",
      "promoter_pledge": "Nil or % value"
    }}
  ],

  "price_performance": [
    {{"period": "3 Month", "absolute_return": "% e.g. 32.1%", "absolute_sensex": "% e.g. 3.0%", "relative_return": "% e.g. 36.9%"}},
    {{"period": "6 Month", "absolute_return": "44.8%", "absolute_sensex": "7.9%", "relative_return": "39.7%"}},
    {{"period": "1 Year",  "absolute_return": "39.7%", "absolute_sensex": "2.5%", "relative_return": "37.1%"}}
  ],

  "estimates": [
    {{"metric": "Revenue", "old_estimate_fy26": "-", "old_estimate_fy27": "-", "new_estimate_fy26": "-", "new_estimate_fy27": "-", "change_fy26": "-", "change_fy27": "-"}},
    {{"metric": "EBITDA",  "old_estimate_fy26": "-", "old_estimate_fy27": "-", "new_estimate_fy26": "-", "new_estimate_fy27": "-", "change_fy26": "-", "change_fy27": "-"}},
    {{"metric": "Margins (%)", "old_estimate_fy26": "-", "old_estimate_fy27": "-", "new_estimate_fy26": "-", "new_estimate_fy27": "-", "change_fy26": "-", "change_fy27": "-"}},
    {{"metric": "Adj. PAT", "old_estimate_fy26": "-", "old_estimate_fy27": "-", "new_estimate_fy26": "-", "new_estimate_fy27": "-", "change_fy26": "-", "change_fy27": "-"}},
    {{"metric": "EPS",      "old_estimate_fy26": "-", "old_estimate_fy27": "-", "new_estimate_fy26": "-", "new_estimate_fy27": "-", "change_fy26": "-", "change_fy27": "-"}}
  ],

  "financials": {{
    "income_statement": [
      {{"metric": "Sales",       "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "% change",    "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "EBITDA",      "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Depreciation","fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "EBIT",        "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Interest",    "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Other Income","fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "PBT",         "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Tax",         "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Reported PAT","fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Adj. PAT",    "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Adj EPS",     "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}}
    ],
    "balance_sheet": [
      {{"metric": "Cash",                "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Accts. Receivable",   "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Inventories",         "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Net Fixed Assets",    "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Total Assets",        "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Current Liabilities", "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Debt Funds",          "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Shareholder Funds",   "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "BVPS",                "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}}
    ],
    "cash_flow": [
      {{"metric": "C.F. Operation",  "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Capital exp.",    "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "C.F - Investment","fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "C.F - Finance",   "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Closing Cash",    "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}}
    ],
    "ratios": [
      {{"metric": "EBITDA margin (%)",   "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "Net profit mgn. (%)", "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "ROE (%)",             "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "ROCE (%)",            "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "EV/Sales (x)",        "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "EV/EBITDA (x)",       "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "P/E (x)",             "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "P/BV (x)",            "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}},
      {{"metric": "D/E",                 "fy23a": "-", "fy24a": "-", "fy25a": "-", "fy26e": "-", "fy27e": "-"}}
    ]
  }},

  "recommendation_history": [
    {{"Date": "11-Aug-22", "Rating": "BUY",  "Target": "69"}},
    {{"Date": "29-Jul-25", "Rating": "HOLD", "Target": "337"}}
  ]
}}

Fill in every field with real values from the document.
For fields not found in the document, use "-" not null.
Extract data as numbers only — no units like "cr" or "Rs." inside the value.
"""


def extract_with_gemini(company_name: str, filename: str, file_bytes: bytes) -> GeojitReportData:
    """
    Upload file to Gemini Files API and extract structured financial data.
    Works with PDF (including image-heavy slides), TXT, and CSV.
    """
    if not GEMINI_AVAILABLE:
        raise ImportError("google-generativeai not installed")

    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    genai.configure(api_key=GEMINI_API_KEY)

    ext = filename.rsplit(".", 1)[-1].lower()
    mime_map = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "csv": "text/csv",
    }
    mime_type = mime_map.get(ext, "application/octet-stream")

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        print(f"Uploading {filename} ({len(file_bytes)//1024} KB) to Gemini Files API...")
        uploaded = genai.upload_file(path=tmp_path, mime_type=mime_type)

        # Wait for processing
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = genai.get_file(uploaded.name)

        if uploaded.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini file processing failed: {uploaded.state.name}")

        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        prompt = EXTRACTION_PROMPT.format(company_name=company_name)

        print(f"Extracting financial data with Gemini 2.0 Flash...")
        response = model.generate_content(
            [uploaded, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        print(f"SUCCESS: Gemini extracted data for {company_name}")
        return _build_report_data(data, company_name)

    finally:
        os.unlink(tmp_path)
        try:
            genai.delete_file(uploaded.name)
        except Exception:
            pass


def _build_report_data(data: dict, company_name: str) -> GeojitReportData:
    """Convert raw Gemini JSON dict into typed GeojitReportData."""
    import datetime

    def safe(d, key, default="-"):
        v = d.get(key, default)
        return str(v) if v is not None and v != "" else default

    cd_raw = data.get("company_data", {})
    cd = CompanyData(
        market_cap=safe(cd_raw, "market_cap"),
        high_low=safe(cd_raw, "high_low"),
        enterprise_value=safe(cd_raw, "enterprise_value"),
        outstanding_shares=safe(cd_raw, "outstanding_shares"),
        free_float=safe(cd_raw, "free_float"),
        dividend_yield=safe(cd_raw, "dividend_yield"),
        avg_volume=safe(cd_raw, "avg_volume"),
        beta=safe(cd_raw, "beta"),
        face_value=safe(cd_raw, "face_value"),
    )

    val_raw = data.get("valuation", {})
    valuation = ValuationMetric(
        rating=safe(val_raw, "rating", "HOLD"),
        target=safe(val_raw, "target"),
        cmp=safe(val_raw, "cmp"),
        upside=safe(val_raw, "upside"),
        bloomberg=safe(val_raw, "bloomberg"),
        sensex=safe(val_raw, "sensex"),
        nse_code=safe(val_raw, "nse_code"),
        bse_code=safe(val_raw, "bse_code"),
        time_frame=safe(val_raw, "time_frame", "12 Months"),
        stock_type=safe(val_raw, "stock_type", "Large Cap"),
    )

    shareholding = []
    for sh in data.get("shareholding", []):
        shareholding.append(ShareholdingQuarter(
            quarter=safe(sh, "quarter", "Q1FY26"),
            promoters=safe(sh, "promoters"),
            fiis=safe(sh, "fiis"),
            mfs_institutions=safe(sh, "mfs_institutions"),
            public=safe(sh, "public"),
            others=safe(sh, "others"),
            promoter_pledge=safe(sh, "promoter_pledge"),
        ))
    if not shareholding:
        shareholding = [ShareholdingQuarter(quarter="Q1FY26")]

    price_performance = []
    for pp in data.get("price_performance", []):
        price_performance.append(PricePerformanceRow(
            period=safe(pp, "period"),
            absolute_return=safe(pp, "absolute_return"),
            absolute_sensex=safe(pp, "absolute_sensex"),
            relative_return=safe(pp, "relative_return"),
        ))
    if not price_performance:
        price_performance = [
            PricePerformanceRow(period="3 Month"),
            PricePerformanceRow(period="6 Month"),
            PricePerformanceRow(period="1 Year"),
        ]

    estimates = []
    for e in data.get("estimates", []):
        estimates.append(EstimatesRow(
            metric=safe(e, "metric"),
            old_estimate_fy26=safe(e, "old_estimate_fy26"),
            old_estimate_fy27=safe(e, "old_estimate_fy27"),
            new_estimate_fy26=safe(e, "new_estimate_fy26"),
            new_estimate_fy27=safe(e, "new_estimate_fy27"),
            change_fy26=safe(e, "change_fy26"),
            change_fy27=safe(e, "change_fy27"),
        ))

    def _rows(lst):
        out = []
        for r in lst:
            if isinstance(r, dict):
                out.append(StatementRow(
                    metric=safe(r, "metric"),
                    fy23a=safe(r, "fy23a"),
                    fy24a=safe(r, "fy24a"),
                    fy25a=safe(r, "fy25a"),
                    fy26e=safe(r, "fy26e"),
                    fy27e=safe(r, "fy27e"),
                ))
        return [r for r in out if not all(
            v == "-" for v in [r.fy23a, r.fy24a, r.fy25a, r.fy26e, r.fy27e]
        )]

    fin_raw = data.get("financials", {})
    financials = FinancialsBundle(
        income_statement=_rows(fin_raw.get("income_statement", [])),
        balance_sheet=_rows(fin_raw.get("balance_sheet", [])),
        cash_flow=_rows(fin_raw.get("cash_flow", [])),
        ratios=_rows(fin_raw.get("ratios", [])),
    )

    report_date = data.get("report_date") or datetime.date.today().strftime("%d %B, %Y")
    highlights = data.get("highlights", [])
    if not highlights:
        highlights = ["Key financial highlights extracted from uploaded document."]

    return GeojitReportData(
        company_name=data.get("company_name", company_name),
        sector=data.get("sector", "Diversified"),
        report_date=str(report_date),
        company_description=data.get("company_description", f"{company_name} operates across diversified business segments."),
        highlights=highlights,
        outlook_valuation=data.get("outlook_valuation", f"{company_name} maintains a stable outlook."),
        company_data=cd,
        shareholding=shareholding,
        price_performance=price_performance,
        valuation=valuation,
        estimates=estimates,
        financials=financials,
        recommendation_history=data.get("recommendation_history", []),
    )
