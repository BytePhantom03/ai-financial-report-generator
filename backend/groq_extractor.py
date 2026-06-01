"""
Groq Llama 3.1 70B extractor — fast text-only fallback.
Used for TXT/CSV inputs or when Gemini is unavailable.
"""
import json

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

from gemini_extractor import _build_report_data
from schema import GeojitReportData

_PROMPT_TEMPLATE = """You are a senior equity research analyst.
Extract ALL financial data for {company_name} from the document text below.

Return ONLY valid JSON matching this exact schema (use "-" for missing values, never null):

{{
  "company_name": "{company_name}",
  "sector": "...",
  "report_date": "...",
  "company_description": "2-3 sentences about the company",
  "highlights": ["bullet 1", "bullet 2", "bullet 3", "bullet 4", "bullet 5"],
  "outlook_valuation": "paragraph text",
  "company_data": {{"market_cap":"-","high_low":"-","enterprise_value":"-","outstanding_shares":"-","free_float":"-","dividend_yield":"-","avg_volume":"-","beta":"-","face_value":"-"}},
  "valuation": {{"rating":"HOLD","target":"-","cmp":"-","upside":"-","bloomberg":"-","sensex":"-","nse_code":"-","bse_code":"-","time_frame":"12 Months","stock_type":"Large Cap"}},
  "shareholding": [{{"quarter":"Q1FY26","promoters":"-","fiis":"-","mfs_institutions":"-","public":"-","others":"-","promoter_pledge":"-"}}],
  "price_performance": [
    {{"period":"3 Month","absolute_return":"-","absolute_sensex":"-","relative_return":"-"}},
    {{"period":"6 Month","absolute_return":"-","absolute_sensex":"-","relative_return":"-"}},
    {{"period":"1 Year","absolute_return":"-","absolute_sensex":"-","relative_return":"-"}}
  ],
  "estimates": [
    {{"metric":"Revenue","old_estimate_fy26":"-","old_estimate_fy27":"-","new_estimate_fy26":"-","new_estimate_fy27":"-","change_fy26":"-","change_fy27":"-"}},
    {{"metric":"EBITDA","old_estimate_fy26":"-","old_estimate_fy27":"-","new_estimate_fy26":"-","new_estimate_fy27":"-","change_fy26":"-","change_fy27":"-"}},
    {{"metric":"Adj. PAT","old_estimate_fy26":"-","old_estimate_fy27":"-","new_estimate_fy26":"-","new_estimate_fy27":"-","change_fy26":"-","change_fy27":"-"}},
    {{"metric":"EPS","old_estimate_fy26":"-","old_estimate_fy27":"-","new_estimate_fy26":"-","new_estimate_fy27":"-","change_fy26":"-","change_fy27":"-"}}
  ],
  "financials": {{
    "income_statement": [
      {{"metric":"Sales","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"EBITDA","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"Reported PAT","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"Adj. PAT","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"Adj EPS","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}}
    ],
    "balance_sheet": [
      {{"metric":"Total Assets","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"Shareholder Funds","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}}
    ],
    "cash_flow": [
      {{"metric":"C.F. Operation","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"Closing Cash","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}}
    ],
    "ratios": [
      {{"metric":"EBITDA margin (%)","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"ROE (%)","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}},
      {{"metric":"P/E (x)","fy23a":"-","fy24a":"-","fy25a":"-","fy26e":"-","fy27e":"-"}}
    ]
  }},
  "recommendation_history": []
}}

Document text (first 10000 characters):
---
{text}
---

Return only the JSON object:"""


def extract_with_groq(company_name: str, document_text: str) -> GeojitReportData:
    """Extract structured financial data from text using Groq Llama 3.1 70B."""
    if not GROQ_AVAILABLE:
        raise ImportError("groq package not installed")

    from config import GROQ_API_KEY
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    client = Groq(api_key=GROQ_API_KEY)

    prompt = _PROMPT_TEMPLATE.format(
        company_name=company_name,
        text=document_text[:200000],  # Increased from 10k to 200k to include all pages + OCR data
    )

    print(f"Extracting with Groq Llama 3.3 70B for {company_name}...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a financial data extraction engine. Return only valid JSON."},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    data = json.loads(raw)
    print(f"SUCCESS: Groq extracted data for {company_name}")
    return _build_report_data(data, company_name)
