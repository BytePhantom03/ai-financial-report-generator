# Bull AI — Financial Research Report Generator
## Complete Implementation Plan

> **Goal:** Build a web app that takes a company's financial context document and auto-generates a downloadable PDF research report matching the Geojit-style sample.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [AI Model Selection — Gemini vs Groq](#2-ai-model-selection--gemini-vs-groq)
3. [Tech Stack](#3-tech-stack)
4. [System Architecture](#4-system-architecture)
5. [Geojit Template Reverse Engineering](#5-geojit-template-reverse-engineering)
6. [Directory Structure](#6-directory-structure)
7. [Phase-by-Phase Implementation](#7-phase-by-phase-implementation)
8. [Detailed Module Breakdown](#8-detailed-module-breakdown)
9. [Prompt Engineering](#9-prompt-engineering)
10. [PDF Generation Strategy](#10-pdf-generation-strategy)
11. [Chart Generation Strategy](#11-chart-generation-strategy)
12. [Frontend UI Plan](#12-frontend-ui-plan)
13. [API Endpoints](#13-api-endpoints)
14. [Testing with JSW Energy PDF](#14-testing-with-jsw-energy-pdf)
15. [Error Handling & Missing Fields](#15-error-handling--missing-fields)
16. [README Template](#16-readme-template)
17. [Acceptance Criteria Checklist](#17-acceptance-criteria-checklist)
18. [Timeline](#18-timeline)

---

## 1. Project Overview

### What You're Building

A full-stack web application that:

1. Accepts a **company name** + **financial document** (PDF, CSV, or TXT)
2. Uses an **AI model** to extract and structure all key financial data
3. Generates a **Geojit-style multi-page PDF** with:
   - Cover block (company name, rating, CMP, target, return %)
   - Key highlights (bullet points)
   - Company Data table + Shareholding table
   - Price Performance table
   - Quarterly Financials Consolidated table
   - Revenue, EBITDA, PAT, Gross Order Value charts
   - Outlook & Valuation narrative paragraph
   - Change in Estimates table
   - Consolidated Financials (P&L, Balance Sheet, Cash Flow, Ratios)
   - Recommendation Summary + Disclaimer page
4. Provides a **one-click download** of the generated PDF

### Input Formats Supported
- PDF (primary — Eternal/Geojit sample, JSW Energy test doc)
- TXT / plain text
- CSV (for structured financial data)

---

## 2. AI Model Selection — Gemini vs Groq

### Recommendation: **Use Gemini (Primary) + Groq (Fallback)**

| Feature | Gemini 1.5 Pro / 2.0 Flash | Groq (Llama 3.1 70B) |
|---|---|---|
| **PDF Native Input** | ✅ Yes — send PDF bytes directly | ❌ No — must extract text first |
| **Context Window** | 1M tokens (Pro), 1M (Flash) | 128K tokens |
| **Structured Output (JSON)** | ✅ `response_mime_type="application/json"` | ✅ via prompt instruction |
| **Speed** | Flash: ~3-5s, Pro: ~10-15s | Very fast (~1-2s) |
| **Long Document Handling** | Excellent — handles 40-page PDFs natively | Good after text extraction |
| **Financial Reasoning** | Excellent | Very good |
| **Free Tier** | Generous (Flash especially) | Generous |
| **API Reliability** | High | High |
| **Best For** | Full pipeline (PDF in → JSON out) | Fast text-only extraction, fallback |

### Decision Logic

```
IF input is PDF:
    → Use Gemini (send raw PDF bytes, extract everything in one call)

IF input is CSV or TXT:
    → Use Groq (fastest for structured text) OR Gemini Flash

IF Gemini fails/rate-limits:
    → Extract text via pdfplumber → send to Groq as fallback
```

### Recommended Model

```
Primary:  gemini-2.0-flash-exp   (fast, free, 1M context, native PDF)
Fallback: llama-3.1-70b-versatile via Groq
```

### Why Gemini Wins for This Use Case

The JSW Energy document is a 49-page PDF with tables, charts, and images. Gemini can ingest the raw PDF file directly via the Files API — no preprocessing needed. It reads tables from slide images, understands chart data, and returns structured JSON in one API call. Groq requires you to first extract text (losing table structure from image-heavy PDFs like JSW), then send it. For this project, that preprocessing step is lossy and error-prone.

---

## 3. Tech Stack

### Backend
```
Python 3.11+
FastAPI              — REST API server
google-generativeai  — Gemini API client
groq                 — Groq API client (fallback)
pdfplumber           — PDF text/table extraction (preprocessing)
reportlab            — PDF generation (primary)
matplotlib           — Chart generation (PNG → embed in PDF)
pandas               — Data manipulation
python-multipart     — File upload handling
uvicorn              — ASGI server
```

### Frontend
```
React 18 + Vite
Tailwind CSS         — Styling
axios                — API calls
react-dropzone       — File upload UI
```

### Why ReportLab for PDF Generation?

ReportLab gives pixel-perfect control over layout. The Geojit report has a very specific multi-column layout, color-coded tables, sidebar ratings box, and embedded charts. ReportLab's `Platypus` framework (flowable elements) plus low-level `Canvas` drawing handles all of this. WeasyPrint (HTML→PDF) is an alternative but table rendering is less reliable. pdfkit/wkhtmltopdf has font/image issues in containers.

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│   [Company Name Input]  [File Upload]  [Generate Button]     │
│                      [Download PDF Button]                   │
└────────────────────┬────────────────────────────────────────┘
                     │ POST /api/generate  (multipart form)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                          │
│                                                              │
│  1. File Handler        → detect format (PDF/CSV/TXT)        │
│  2. Preprocessor        → extract raw text if needed         │
│  3. AI Extractor        → Gemini/Groq → structured JSON      │
│  4. Data Validator      → fill missing fields with "N/A"     │
│  5. Chart Generator     → matplotlib → PNG buffers           │
│  6. PDF Builder         → ReportLab → final PDF bytes        │
│  7. Response            → return PDF as file download        │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Input File
    │
    ▼
[Format Detector]
    │
    ├── PDF ──────────────────► [Gemini Files API] ──────────────┐
    │                           (native PDF input)               │
    ├── TXT/CSV ──► [pdfplumber/pandas text extract] ──► [Groq]  │
    │                                                            │
    └─────────────────────────────────────────────────────────── ▼
                                                    [Structured JSON]
                                                         │
                                                    [Validator]
                                                         │
                                              ┌──────────┴──────────┐
                                              │                     │
                                        [Chart Gen]           [PDF Builder]
                                        matplotlib             ReportLab
                                              │                     │
                                              └──────────┬──────────┘
                                                         │
                                                   [Final PDF]
                                                         │
                                                   [Download]
```

---

## 5. Geojit Template Reverse Engineering

### Page 1 Layout Breakdown

```
┌─────────────────────────────────────────────────────────┐
│ [Geojit Logo - top right]    "Retail Equity Research"   │
│                                                          │
│  Company Name (H1, bold, dark blue)    ┌──────────────┐ │
│                                        │  HOLD/BUY/   │ │
│  Sector: ____    Date: ____            │  SELL Badge  │ │
│                                        └──────────────┘ │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Key Changes │ Target ▲ │ Rating ▼ │ Earnings ▼    │   │
│ │ Stock Type  │ Bloomberg │ Sensex │ NSE │ BSE │ TF │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ Data as of: ____                                         │
│                                                          │
│ ┌──────────────────┐  ┌────────────────────────────┐   │
│ │  Company Data    │  │  HEADLINE TITLE (bold blue)│   │
│ │  ─────────────── │  │                            │   │
│ │  Market Cap      │  │  Company description para  │   │
│ │  52W High-Low    │  │                            │   │
│ │  Enterprise Val  │  │  • Bullet highlight 1      │   │
│ │  Outstanding Sh  │  │  • Bullet highlight 2      │   │
│ │  Free Float      │  │  • Bullet highlight 3      │   │
│ │  Dividend Yield  │  │  • Bullet highlight 4      │   │
│ │  6m avg volume   │  │  • Bullet highlight 5      │   │
│ │  Beta / FV       │  │  • Bullet highlight 6      │   │
│ ├──────────────────┤  └────────────────────────────┘   │
│ │  Shareholding %  │                                    │
│ │  Q3/Q4/Q1        │  ┌────────────────────────────┐   │
│ │  Promoters       │  │  Outlook & Valuation       │   │
│ │  FIIs / MFs      │  │  (paragraph text)          │   │
│ │  Public/Others   │  │                            │   │
│ ├──────────────────┤  └────────────────────────────┘   │
│ │  Price Perf      │                                    │
│ │  3M / 6M / 1Y    │  ┌────────────────────────────┐   │
│ │  Abs/Sensex/Rel  │  │  Quarterly Financials      │   │
│ ├──────────────────┤  │  Consolidated Table        │   │
│ │  [Stock Chart]   │  │  (Q1FY26/Q1FY25/YoY/QoQ)  │   │
│ └──────────────────┘  └────────────────────────────┘   │
│                                                          │
│ ┌─────────────────────────────────────────────────┐     │
│ │  Annual Estimates Table (FY25A/FY26E/FY27E)     │     │
│ └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### Page 2 Layout

```
┌─────────────────────────────────────────────────────────┐
│  Key Highlights (bullets)                               │
│                                                          │
│  [Revenue Chart]          [Gross Order Value Chart]     │
│  Bar + line (QoQ growth)  Bar + line (QoQ growth)       │
│                                                          │
│  [EBITDA Chart]           [PAT Chart]                   │
│  Bar + margin line        Bar + margin line              │
│                                                          │
│  Change in Estimates Table                              │
│  (Old vs New, FY26E/FY27E, % Change)                   │
└─────────────────────────────────────────────────────────┘
```

### Page 3 Layout

```
┌─────────────────────────────────────────────────────────┐
│  Consolidated Financials                                │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐    │
│  │  Profit & Loss       │  │  Balance Sheet       │    │
│  │  FY23A-FY27E table   │  │  FY23A-FY27E table   │    │
│  └──────────────────────┘  └──────────────────────┘    │
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐    │
│  │  Cashflow            │  │  Ratios              │    │
│  │  FY23A-FY27E table   │  │  FY23A-FY27E table   │    │
│  └──────────────────────┘  └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Page 4 Layout

```
┌─────────────────────────────────────────────────────────┐
│  Recommendation Summary (last 3 years)                  │
│  [Price Chart]          | [Dates/Rating/Target Table]   │
│                                                          │
│  Investment Rating Criteria Table                       │
│  (Buy/Accumulate/Hold/Reduce — Large/Mid/Small caps)    │
│                                                          │
│  Disclaimer & Disclosures (small text block)            │
│  Symbols: Upgrade / No Change / Downgrade               │
└─────────────────────────────────────────────────────────┘
```

### Color Palette (from Geojit sample)

```python
GEOJIT_COLORS = {
    "dark_blue":     "#1B3A6B",   # Company name, section headers
    "header_blue":   "#1E4D8C",   # Table headers background
    "light_blue":    "#2E75B6",   # Highlights, bullets
    "table_header":  "#1B3A6B",   # Dark header rows
    "table_row_alt": "#E8F0F7",   # Alternating table rows
    "table_border":  "#A0B4C8",   # Table borders
    "green_pos":     "#00B050",   # Positive values
    "red_neg":       "#FF0000",   # Negative values
    "rating_hold":   "#FFC000",   # HOLD badge background
    "rating_buy":    "#00B050",   # BUY badge background
    "rating_sell":   "#FF0000",   # SELL badge background
    "section_bg":    "#EBF3FA",   # Section label backgrounds
    "text_primary":  "#000000",   # Main text
    "text_secondary":"#404040",   # Secondary text
    "white":         "#FFFFFF",
}
```

---

## 6. Directory Structure

```
bull-ai-report-generator/
│
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example               # GEMINI_API_KEY, GROQ_API_KEY
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings, API keys, constants
│   │   └── models.py              # Pydantic models for extracted data
│   │
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base_extractor.py      # Abstract base class
│   │   ├── gemini_extractor.py    # Gemini PDF extraction
│   │   ├── groq_extractor.py      # Groq text extraction
│   │   └── preprocessor.py       # pdfplumber, CSV/TXT parsing
│   │
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── chart_generator.py    # matplotlib chart functions
│   │   ├── pdf_builder.py        # ReportLab PDF assembly
│   │   ├── template_fields.py    # All field definitions & mappings
│   │   └── styles.py             # ReportLab style definitions
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validators.py          # Fill missing fields with N/A
│       └── formatters.py         # Number formatting helpers
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── UploadForm.jsx
│       │   ├── StatusIndicator.jsx
│       │   └── DownloadButton.jsx
│       └── api/
│           └── client.js
│
├── templates/
│   └── geojit_fields.json         # Master field definitions
│
├── examples/
│   ├── outputs/
│   │   ├── eternal_ltd_report.pdf
│   │   └── jsw_energy_report.pdf
│   └── inputs/
│       ├── Eternal-Geojit.pdf
│       └── JSW_Energy_Q2FY26.pdf
│
├── tests/
│   ├── test_extractor.py
│   ├── test_pdf_builder.py
│   └── test_charts.py
│
├── docker-compose.yml             # Optional containerization
├── Dockerfile
└── README.md
```

---

## 7. Phase-by-Phase Implementation

### Phase 1 — Template & Data Model (Day 1-2)

**Goal:** Define every field in the Geojit report as a structured Python model.

1. Study all 4 pages of the Geojit Eternal report carefully
2. Create `template_fields.py` with every field name, type, and section
3. Create Pydantic `ReportData` model in `models.py`
4. Define `FIELD_REGISTRY` dict mapping AI-extracted keys to PDF positions

**Deliverable:** `models.py` with complete `ReportData` dataclass

---

### Phase 2 — AI Extraction Pipeline (Day 2-3)

**Goal:** Given any financial document, return a populated `ReportData` JSON.

1. Build `gemini_extractor.py`:
   - Upload file to Gemini Files API
   - Send extraction prompt (see Section 9)
   - Parse JSON response into `ReportData`
2. Build `preprocessor.py`:
   - PDF → text via pdfplumber
   - CSV → DataFrame → text summary
   - TXT → direct string
3. Build `groq_extractor.py` as fallback
4. Build `validators.py` to handle missing fields

**Deliverable:** `extract_financial_data(file_path, company_name) → ReportData`

---

### Phase 3 — Chart Generation (Day 3-4)

**Goal:** Generate 4 Geojit-style charts as PNG images.

1. Revenue chart (bar + line for QoQ growth)
2. EBITDA chart (bar + margin % line)
3. PAT chart (bar + margin % line)
4. Gross Order Value / Key Metric chart

**Deliverable:** `generate_charts(data: ReportData) → dict[str, bytes]`

---

### Phase 4 — PDF Builder (Day 4-6)

**Goal:** Produce a pixel-accurate Geojit-style PDF.

1. Build `styles.py` — all ReportLab ParagraphStyles and TableStyles
2. Build `pdf_builder.py` page by page:
   - Page 1: Header, company data, highlights, quarterly table
   - Page 2: Key highlights, 4 charts, change in estimates
   - Page 3: Consolidated financials (P&L, BS, CF, Ratios)
   - Page 4: Recommendation, rating criteria, disclaimer
3. Integrate charts as embedded PNG images

**Deliverable:** `build_pdf(data: ReportData, charts: dict) → bytes`

---

### Phase 5 — FastAPI Backend (Day 6-7)

**Goal:** Wire everything into a REST API.

1. `POST /api/generate` endpoint
2. File validation (size, type)
3. Pipeline orchestration
4. Return PDF as streaming response

**Deliverable:** Running FastAPI server

---

### Phase 6 — React Frontend (Day 7-8)

**Goal:** Clean, functional UI.

1. Company name input + file drag-drop upload
2. Processing state with progress indicator
3. Download button for generated PDF

**Deliverable:** Working React UI

---

### Phase 7 — Testing & Polish (Day 8-10)

**Goal:** Generate both example PDFs, fix issues.

1. Run with `Eternal-Geojit.pdf` → compare output to sample
2. Run with `JSW_Energy_Q2FY26.pdf` → verify extraction accuracy
3. Fix layout issues, improve prompt precision
4. Add error handling for edge cases

---

## 8. Detailed Module Breakdown

### `models.py` — Complete ReportData Structure

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class CompanyData(BaseModel):
    market_cap: Optional[str] = "N/A"
    week_52_high_low: Optional[str] = "N/A"
    enterprise_value: Optional[str] = "N/A"
    outstanding_shares: Optional[str] = "N/A"
    free_float: Optional[str] = "N/A"
    dividend_yield: Optional[str] = "N/A"
    avg_volume_6m: Optional[str] = "N/A"
    beta: Optional[str] = "N/A"
    face_value: Optional[str] = "N/A"

class ShareholdingRow(BaseModel):
    category: str
    q3: Optional[str] = "N/A"
    q4: Optional[str] = "N/A"
    q1: Optional[str] = "N/A"

class PricePerformance(BaseModel):
    absolute_return_3m: Optional[str] = "N/A"
    absolute_return_6m: Optional[str] = "N/A"
    absolute_return_1y: Optional[str] = "N/A"
    sensex_3m: Optional[str] = "N/A"
    sensex_6m: Optional[str] = "N/A"
    sensex_1y: Optional[str] = "N/A"
    relative_return_3m: Optional[str] = "N/A"
    relative_return_6m: Optional[str] = "N/A"
    relative_return_1y: Optional[str] = "N/A"

class QuarterlyFinancials(BaseModel):
    # Rows: Sales, EBITDA, Margin, EBIT, PBT, Rep.PAT, Adj.PAT, EPS
    rows: List[dict] = []  # [{metric, q1_current, q1_prior, yoy_pct, q4_prior, qoq_pct}]

class AnnualEstimates(BaseModel):
    # FY25A, FY26E, FY27E
    rows: List[dict] = []  # [{metric, fy25a, fy26e, fy27e}]

class ChangeInEstimates(BaseModel):
    rows: List[dict] = []  # [{metric, fy26e_old, fy27e_old, fy26e_new, fy27e_new, fy26e_chg, fy27e_chg}]

class ConsolidatedPL(BaseModel):
    rows: List[dict] = []  # [{metric, fy23a, fy24a, fy25a, fy26e, fy27e}]

class BalanceSheet(BaseModel):
    rows: List[dict] = []

class Cashflow(BaseModel):
    rows: List[dict] = []

class Ratios(BaseModel):
    rows: List[dict] = []

class ChartData(BaseModel):
    # Quarterly revenue data for chart
    quarters: List[str] = []        # ["Q2FY24", "Q3FY24", ...]
    revenue: List[float] = []
    revenue_growth_qoq: List[float] = []
    ebitda: List[float] = []
    ebitda_margin: List[float] = []
    pat: List[float] = []
    pat_margin: List[float] = []
    gov: List[float] = []           # Gross Order Value (or key sector metric)
    gov_growth_qoq: List[float] = []

class ReportData(BaseModel):
    # Header
    company_name: str
    sector: Optional[str] = "N/A"
    report_date: Optional[str] = "N/A"
    stock_type: Optional[str] = "Large Cap"
    bloomberg_code: Optional[str] = "N/A"
    sensex: Optional[str] = "N/A"
    nse_code: Optional[str] = "N/A"
    bse_code: Optional[str] = "N/A"
    time_frame: Optional[str] = "12 Months"

    # Rating box
    rating: Optional[str] = "N/A"           # BUY / HOLD / SELL
    target_price: Optional[str] = "N/A"
    cmp: Optional[str] = "N/A"
    return_pct: Optional[str] = "N/A"
    key_changes_target: Optional[str] = "—"  # ▲ ▼ —
    key_changes_rating: Optional[str] = "—"
    key_changes_earnings: Optional[str] = "—"

    # Headline
    headline: Optional[str] = "N/A"
    company_description: Optional[str] = "N/A"
    key_highlights: List[str] = []          # Bullet points (6-8)
    outlook_valuation: Optional[str] = "N/A"

    # Data tables
    company_data: CompanyData = CompanyData()
    shareholding: List[ShareholdingRow] = []
    price_performance: PricePerformance = PricePerformance()
    quarterly_financials: QuarterlyFinancials = QuarterlyFinancials()
    annual_estimates: AnnualEstimates = AnnualEstimates()
    change_in_estimates: ChangeInEstimates = ChangeInEstimates()
    consolidated_pl: ConsolidatedPL = ConsolidatedPL()
    balance_sheet: BalanceSheet = BalanceSheet()
    cashflow: Cashflow = Cashflow()
    ratios: Ratios = Ratios()

    # Chart data
    chart_data: ChartData = ChartData()

    # Recommendation history
    recommendation_history: List[dict] = []  # [{date, rating, target}]
```

---

### `template_fields.py` — Field Registry

```python
# This is the single source of truth for all fields.
# Add new fields here — they auto-propagate to extraction prompts and PDF layout.

FIELD_REGISTRY = {
    "company_name":         {"section": "header",    "type": "str",   "required": True},
    "sector":               {"section": "header",    "type": "str",   "required": False},
    "report_date":          {"section": "header",    "type": "str",   "required": False},
    "rating":               {"section": "rating",    "type": "str",   "required": True,
                             "valid_values": ["BUY", "HOLD", "SELL", "ACCUMULATE", "REDUCE"]},
    "target_price":         {"section": "rating",    "type": "float", "required": True},
    "cmp":                  {"section": "rating",    "type": "float", "required": True},
    "return_pct":           {"section": "rating",    "type": "float", "required": False},
    "headline":             {"section": "highlights","type": "str",   "required": True},
    "key_highlights":       {"section": "highlights","type": "list",  "required": True,
                             "min_items": 3, "max_items": 8},
    "outlook_valuation":    {"section": "highlights","type": "str",   "required": True},
    # ... all other fields
}
```

---

## 9. Prompt Engineering

### Master Extraction Prompt (for Gemini)

```python
EXTRACTION_PROMPT = """
You are a senior financial analyst. Extract all financial data from the provided document for {company_name}.

Return ONLY a valid JSON object matching exactly this schema. 
Do not include markdown fences, no backticks, no explanatory text.
If a field cannot be found, use null.
If a table row cannot be found, omit it.

JSON Schema to populate:
{schema}

Rules:
1. For monetary values: preserve units (cr, Bn, %). If value is "Rs. 295,735 cr", return "295,735".
2. For growth percentages: return as number e.g. -35.0 not "-35.0%".  
3. For rating: return exactly one of: BUY, HOLD, SELL, ACCUMULATE, REDUCE.
4. For key_highlights: extract 5-8 bullet points verbatim from the document.
5. For quarterly_financials: extract the most recent quarter table.
6. For chart_data: extract quarterly series (last 6-8 quarters minimum).
7. For consolidated_pl/balance_sheet/cashflow/ratios: extract multi-year annual data.
8. headline: the main title/thesis (e.g. "Blinkit propels growth; valuation limits upside").
9. outlook_valuation: the full paragraph text from Outlook & Valuation section.

Begin JSON output now:
"""

def build_extraction_prompt(company_name: str, schema: dict) -> str:
    import json
    schema_str = json.dumps(schema, indent=2)
    return EXTRACTION_PROMPT.format(
        company_name=company_name,
        schema=schema_str
    )
```

### Extraction Prompt for Groq (text-only fallback)

```python
GROQ_PROMPT = """
You are a financial data extraction engine. Given the following text from a financial report for {company_name}, extract all available data and return ONLY valid JSON.

Document text:
---
{document_text}
---

Extract and return JSON with these fields (use null for missing values):
{field_list}

Return only the JSON. No explanation.
"""
```

---

## 10. PDF Generation Strategy

### ReportLab Architecture

The PDF is built using ReportLab's **Platypus** (page layout engine) combined with low-level **Canvas** calls for precise positioning.

```python
# backend/generators/pdf_builder.py

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether, HRFlowable
)
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io

PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 x 841.89 points
MARGIN_LEFT = 15 * mm
MARGIN_RIGHT = 15 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 15 * mm

def build_pdf(data: ReportData, charts: dict) -> bytes:
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    
    story = []
    story += build_page1(data, charts)
    story += build_page2(data, charts)
    story += build_page3(data)
    story += build_page4(data)
    
    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    
    return buffer.getvalue()
```

### Key ReportLab Table Pattern (for Geojit-style tables)

```python
def make_financial_table(headers, rows, col_widths):
    """Creates a Geojit-style colored table."""
    
    table_data = [headers] + rows
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',  (0,0), (-1,0),  HEADER_BLUE),
        ('TEXTCOLOR',   (0,0), (-1,0),  colors.white),
        ('FONTNAME',    (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,0),  7),
        ('ALIGN',       (0,0), (-1,0),  'CENTER'),
        
        # Data rows
        ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,1), (-1,-1), 7),
        ('ALIGN',       (1,1), (-1,-1), 'RIGHT'),  # Numbers right-aligned
        ('ALIGN',       (0,1), (0,-1),  'LEFT'),   # Labels left-aligned
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, TABLE_ROW_ALT]),
        
        # Borders
        ('GRID',        (0,0), (-1,-1), 0.5, TABLE_BORDER),
        ('LINEBELOW',   (0,0), (-1,0),  1.5, HEADER_BLUE),
        
        # Italic rows (margins, EPS etc.)
        ('FONTNAME',    (0,2), (-1,2),  'Helvetica-Oblique'),  # Margin row
    ]))
    return table
```

### Two-Column Layout (left sidebar + right content)

```python
from reportlab.platypus import Frame, BaseDocTemplate, PageTemplate

def build_two_column_page1(data: ReportData) -> list:
    """Returns flowables for the two-column page 1 layout."""
    
    # Left column: Company Data + Shareholding + Price Perf + Chart
    left_content = []
    left_content.append(make_company_data_table(data.company_data))
    left_content.append(Spacer(1, 4*mm))
    left_content.append(make_shareholding_table(data.shareholding))
    left_content.append(Spacer(1, 4*mm))
    left_content.append(make_price_performance_table(data.price_performance))
    
    # Right column: Headline + Highlights + Outlook + Quarterly Table
    right_content = []
    right_content.append(make_headline(data.headline))
    right_content.append(make_highlights(data.key_highlights))
    right_content.append(make_outlook(data.outlook_valuation))
    right_content.append(make_quarterly_table(data.quarterly_financials))
    
    # Use Table with 2 cells for two-column layout
    layout = Table(
        [[left_content, right_content]],
        colWidths=[LEFT_COL_WIDTH, RIGHT_COL_WIDTH]
    )
    layout.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    return [layout]
```

---

## 11. Chart Generation Strategy

### Geojit Chart Style

Each chart is a **dual-axis chart**: bar chart for the primary metric + line chart for growth/margin % on the secondary Y-axis. The style matches Geojit exactly.

```python
# backend/generators/chart_generator.py

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import numpy as np

GEOJIT_BAR_COLOR  = "#4472C4"   # Blue bars
GEOJIT_LINE_COLOR = "#FF0000"   # Red line for growth
GEOJIT_TEXT_SIZE  = 7
CHART_FIGSIZE     = (3.2, 2.2)  # Inches (fits A4 two-column)

def generate_revenue_chart(quarters, revenue, growth_qoq) -> bytes:
    """Bar chart of revenue + red line for QoQ growth %."""
    fig, ax1 = plt.subplots(figsize=CHART_FIGSIZE)
    
    x = np.arange(len(quarters))
    bars = ax1.bar(x, revenue, color=GEOJIT_BAR_COLOR, width=0.6, alpha=0.85)
    
    # Add value labels on bars
    for bar, val in zip(bars, revenue):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                 f'{val:,.0f}', ha='center', va='bottom', fontsize=5.5, color='#333')
    
    # Secondary axis for growth line
    ax2 = ax1.twinx()
    ax2.plot(x, growth_qoq, color=GEOJIT_LINE_COLOR, marker='o',
             markersize=3, linewidth=1.5, zorder=5)
    
    # Add % labels on line
    for xi, val in zip(x, growth_qoq):
        ax2.text(xi, val + 0.5, f'{val:.1f}%', ha='center', va='bottom',
                fontsize=5, color=GEOJIT_LINE_COLOR)
    
    # Style
    ax1.set_xticks(x)
    ax1.set_xticklabels(quarters, fontsize=5.5, rotation=0)
    ax1.tick_params(axis='y', labelsize=5.5)
    ax2.tick_params(axis='y', labelsize=5.5)
    ax1.set_title('Revenue (Rs.cr)', fontsize=7, fontweight='bold', pad=4, loc='left')
    ax2.set_ylabel('Growth (QoQ)', fontsize=5, color=GEOJIT_LINE_COLOR)
    
    # Legend
    bar_patch = mpatches.Patch(color=GEOJIT_BAR_COLOR, label='Revenue (Rs.cr)')
    line_patch = plt.Line2D([0],[0], color=GEOJIT_LINE_COLOR, label='Growth (QoQ)', lw=1.5)
    ax1.legend(handles=[bar_patch, line_patch], fontsize=5, loc='upper left',
               framealpha=0.7, edgecolor='none')
    
    fig.tight_layout(pad=0.5)
    
    buf = io.BytesIO()
    fig.savefig(buf, format='PNG', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_all_charts(data: ReportData) -> dict:
    cd = data.chart_data
    return {
        "revenue":   generate_revenue_chart(cd.quarters, cd.revenue, cd.revenue_growth_qoq),
        "ebitda":    generate_ebitda_chart(cd.quarters, cd.ebitda, cd.ebitda_margin),
        "pat":       generate_pat_chart(cd.quarters, cd.pat, cd.pat_margin),
        "gov":       generate_gov_chart(cd.quarters, cd.gov, cd.gov_growth_qoq),
    }
```

---

## 12. Frontend UI Plan

### React Component Tree

```
App
├── Header ("Bull AI — Research Report Generator")
├── UploadForm
│   ├── CompanyNameInput    (text field)
│   ├── FileDropzone        (PDF/CSV/TXT — react-dropzone)
│   └── GenerateButton      (triggers POST /api/generate)
├── StatusIndicator
│   ├── UploadingState
│   ├── ExtractingState     ("Extracting financial data with AI...")
│   ├── BuildingState       ("Generating PDF report...")
│   └── ErrorState
└── DownloadSection
    └── DownloadButton      (shown after success)
```

### `App.jsx` Core Logic

```jsx
const handleGenerate = async () => {
  setStatus('uploading');
  const formData = new FormData();
  formData.append('company_name', companyName);
  formData.append('file', file);

  try {
    setStatus('extracting');
    const response = await axios.post('/api/generate', formData, {
      responseType: 'blob',
      onUploadProgress: (e) => setProgress(Math.round(e.loaded / e.total * 30)),
    });

    setStatus('done');
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    setPdfUrl(url);
    setPdfName(`${companyName}_Research_Report.pdf`);
  } catch (err) {
    setStatus('error');
    setError(err.response?.data?.detail || 'Generation failed');
  }
};
```

---

## 13. API Endpoints

### `POST /api/generate`

```
Request:  multipart/form-data
  company_name: string (required)
  file: File (required — PDF, CSV, or TXT)

Response (success):
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="{company_name}_Report.pdf"
  Body: PDF bytes

Response (error):
  400 { "detail": "Unsupported file type. Use PDF, CSV, or TXT." }
  422 { "detail": "company_name is required" }
  500 { "detail": "AI extraction failed: <reason>" }
```

### `GET /api/health`

```
Response: { "status": "ok", "gemini": true, "groq": true }
```

### `GET /api/fields`

```
Response: Full FIELD_REGISTRY — useful for frontend to show expected fields
```

---

## 14. Testing with JSW Energy PDF

### What the Extractor Will Find

From the JSW Energy Q2 FY26 presentation:

| Field | Expected Extraction |
|---|---|
| company_name | JSW Energy Limited |
| sector | Power / Utilities |
| report_date | 17 October 2025 |
| quarterly revenue | ₹5,361 Cr (Q2 FY26), ₹3,459 Cr (Q2 FY25) |
| quarterly EBITDA | ₹3,180 Cr (67% YoY) |
| quarterly PAT | ₹705 Cr (−17% YoY) |
| EBITDA margin | 59% (Q2 FY26), 55% (Q2 FY25) |
| net generation | 14.9 BUs (+52% YoY) |
| installed capacity | 13,211 MW |
| cash & equivalents | ₹6,181 Cr |
| net debt | ₹61,960 Cr |
| key highlights | 6 bullets from page 5-6 |

### Extraction Test Script

```python
# tests/test_extractor.py
import pytest
from extractors.gemini_extractor import GeminiExtractor

def test_jsw_energy_extraction():
    extractor = GeminiExtractor()
    data = extractor.extract("examples/inputs/JSW_Energy_Q2FY26.pdf", "JSW Energy")
    
    assert data.company_name == "JSW Energy Limited"
    assert data.quarterly_financials.rows[0]["q1_current"] is not None  # Revenue row
    assert len(data.key_highlights) >= 3
    assert data.chart_data.revenue is not None and len(data.chart_data.revenue) > 0
    print(f"Extracted {len(data.key_highlights)} highlights")
    print(f"Revenue series: {data.chart_data.revenue}")
```

---

## 15. Error Handling & Missing Fields

### Validator Strategy

```python
# backend/utils/validators.py

def validate_and_fill(data: ReportData) -> ReportData:
    """
    Fill all None/missing fields with appropriate defaults.
    Never crash the PDF builder — show N/A instead.
    """
    
    # Required fields that must exist for basic report
    if not data.company_name:
        raise ValueError("company_name is required")
    
    # Fill string fields
    for field in ["sector", "report_date", "headline", "outlook_valuation"]:
        if not getattr(data, field):
            setattr(data, field, "N/A")
    
    # Fill rating fields
    if not data.rating:
        data.rating = "N/R"  # Not Rated
    if not data.target_price:
        data.target_price = "—"
    if not data.cmp:
        data.cmp = "—"
    
    # Ensure lists are never empty (prevents table crashes)
    if not data.key_highlights:
        data.key_highlights = ["Refer to source document for detailed analysis."]
    
    if not data.quarterly_financials.rows:
        data.quarterly_financials.rows = [
            {"metric": "Sales", "q1_current": "N/A", "q1_prior": "N/A",
             "yoy_pct": "N/A", "q4_prior": "N/A", "qoq_pct": "N/A"}
        ]
    
    # Handle empty chart data gracefully
    if not data.chart_data.quarters:
        data.chart_data.quarters = ["N/A"]
        data.chart_data.revenue = [0]
        data.chart_data.revenue_growth_qoq = [0]
    
    return data
```

### PDF Builder Null Safety

```python
def safe_value(val, default="N/A"):
    if val is None or val == "":
        return default
    return str(val)

def color_value(val_str):
    """Red for negatives, green for positives, black for N/A."""
    try:
        v = float(str(val_str).replace('%','').replace(',',''))
        if v < 0: return colors.red
        if v > 0: return colors.HexColor("#00B050")
    except:
        pass
    return colors.black
```

---

## 16. README Template

```markdown
# Bull AI — Financial Research Report Generator

Generates Geojit-style equity research PDF reports from any financial document.

## Quick Start

### Backend
\```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add GEMINI_API_KEY and GROQ_API_KEY to .env
uvicorn main:app --reload --port 8000
\```

### Frontend
\```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
\```

## Usage

1. Enter company name
2. Upload a financial document (PDF, CSV, or TXT)
3. Click **Generate Report**
4. Download the PDF

## Tech Stack

| Layer | Technology |
|---|---|
| AI Extraction | Gemini 2.0 Flash (primary), Groq Llama 3.1 (fallback) |
| PDF Generation | ReportLab (Python) |
| Charts | Matplotlib |
| Backend | FastAPI + Python 3.11 |
| Frontend | React 18 + Vite + Tailwind |

## Template Fields

All report fields are defined in `backend/generators/template_fields.py`.  
To add a new field: (1) add to `FIELD_REGISTRY`, (2) add to `ReportData` model,  
(3) add to extraction prompt, (4) add to PDF builder.

## Example Outputs

- `examples/outputs/eternal_ltd_report.pdf` — Generated from Eternal/Zomato Q1FY26 data  
- `examples/outputs/jsw_energy_report.pdf` — Generated from JSW Energy Q2FY26 presentation

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GROQ_API_KEY` | Groq Cloud API key |
| `MAX_FILE_SIZE_MB` | Max upload size (default: 50) |
| `OUTPUT_DIR` | Directory for generated PDFs |
```

---

## 17. Acceptance Criteria Checklist

| Requirement | Implementation | Status |
|---|---|---|
| Template matches Geojit layout + section order | ReportLab 4-page builder with exact color/font matching | ✅ Planned |
| Financial tables populated | Gemini extraction → quarterly + annual tables | ✅ Planned |
| Narrative sections populated | key_highlights + outlook_valuation fields | ✅ Planned |
| At least one chart | Revenue chart (bar + line) mandatory | ✅ Planned |
| Works with PDF input | Gemini native PDF input | ✅ Planned |
| Works with CSV input | pandas → text → Groq extraction | ✅ Planned |
| Missing fields handled gracefully | validators.py fills with "N/A" | ✅ Planned |
| One-click download | React download button → blob URL | ✅ Planned |
| Multiple chart types (nice-to-have) | Revenue, EBITDA, PAT, GOV charts | ✅ Planned |
| Modular code (nice-to-have) | FIELD_REGISTRY single source of truth | ✅ Planned |
| Two example PDFs | Eternal + JSW Energy | ✅ Planned |

---

## 18. Timeline

```
Day 1-2:   models.py + template_fields.py + styles.py
           → Foundation complete

Day 2-3:   gemini_extractor.py + groq_extractor.py + validators.py
           → Can extract JSON from any doc

Day 3-4:   chart_generator.py (all 4 charts)
           → Charts match Geojit style

Day 4-6:   pdf_builder.py pages 1-4
           → Full PDF output (compare to Eternal sample)

Day 6-7:   FastAPI main.py + all endpoints
           → API working end-to-end

Day 7-8:   React frontend
           → UI working with upload + download

Day 8-10:  Testing with JSW Energy + polish
           → Both example PDFs generated
           → README + repo clean-up
```

---

## Key Implementation Notes

### Why Not WeasyPrint or Puppeteer?

WeasyPrint converts HTML→PDF but struggles with complex multi-column layouts and precise table cell control that Geojit requires. Puppeteer (headless Chrome) works but adds Node.js dependency and is overkill. ReportLab gives direct control over every pixel — necessary for faithfully replicating the Geojit template.

### Why Gemini for PDF Input?

The JSW Energy document is 49 slides with data embedded in chart images and table screenshots. Gemini's multimodal capability reads the visual content directly. Text-only extraction via pdfplumber would miss all data in images/charts.

### Adding a New Company (Modularity)

1. No code changes needed
2. Just upload a new financial document
3. The AI extracts all fields automatically
4. Missing fields → "N/A" via validators

### Adding a New Template Field

1. Add to `FIELD_REGISTRY` in `template_fields.py`
2. Add to `ReportData` Pydantic model in `models.py`
3. Add to extraction prompt in `gemini_extractor.py`
4. Add rendering logic in `pdf_builder.py`

