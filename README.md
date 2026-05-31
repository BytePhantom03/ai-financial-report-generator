# Bull AI — Financial Research Report Generator

An AI-powered full-stack web app that ingests any corporate financial document (PDF, CSV, TXT) and generates a downloadable **Geojit-style 4-page equity research report** in seconds.

## How It Works

```
Upload PDF/CSV/TXT
     │
     ▼
[Gemini 2.0 Flash]  ← primary  (reads PDFs natively, including image-embedded charts)
     │ fail
     ▼
[Groq Llama 3.1 70B]  ← fallback  (fast, text-only)
     │ fail
     ▼
[Rule-based Engine]  ← always works  (no API key needed)
     │
     ▼
[ReportLab PDF Builder]  →  4-page Geojit-style report
```

## Tech Stack

| Layer | Technology |
|---|---|
| **AI — Primary** | Google Gemini 2.0 Flash (native PDF multimodal) |
| **AI — Fallback** | Groq Llama 3.1 70B Versatile |
| **PDF Generation** | ReportLab Platypus + Canvas |
| **Charts** | Matplotlib (bar + line combo) |
| **Backend** | FastAPI + Python 3.11 |
| **Frontend** | React 18 + Vite |

## Report Layout (4 pages, matching Geojit sample)

- **Page 1**: Company overview · Rating badge · Key Changes · Shareholding · Price Performance · Quarterly Financials Consolidated · Annual Estimates
- **Page 2**: Key Highlights bullets · 4-chart grid (Revenue, GOV, EBITDA, PAT) · Change in Estimates table
- **Page 3**: Consolidated Financials 4-quadrant (P&L / Balance Sheet / Cashflow / Ratios)
- **Page 4**: Recommendation History · Investment Rating Criteria · Disclaimer & Disclosures

## Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt

# Optional: add API keys for AI-powered extraction
copy .env.example .env
# Edit .env and add GEMINI_API_KEY and/or GROQ_API_KEY

python main.py
# → API running at http://localhost:8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# → App running at http://localhost:5173
```

### 3. Generate Example PDFs (no UI needed)
```bash
# From root directory:
backend\venv\Scripts\python.exe run_tests.py
# → output/ICICI_Bank_Research_Report.pdf
```

## API Keys (Optional but Recommended)

| Key | Provider | Effect |
|---|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) — Free | **Best** — reads PDF images, extracts from charts |
| `GROQ_API_KEY` | [Groq Cloud](https://console.groq.com) — Free | Fast text extraction (Llama 3.1 70B) |

Without any key, the rule-based regex engine handles everything — works great for structured text PDFs.

## Project Structure

```
bull-ai/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # API key loader (.env)
│   ├── schema.py            # Pydantic data models
│   ├── extractor.py         # PDF/CSV/TXT text extraction
│   ├── llm_parser.py        # AI cascade orchestrator
│   ├── gemini_extractor.py  # Gemini 2.0 Flash (primary)
│   ├── groq_extractor.py    # Groq Llama 3.1 (fallback)
│   ├── pdf_generator.py     # ReportLab 4-page builder
│   ├── charts.py            # Matplotlib chart generator
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx          # React UI with status tracker
│       └── index.css        # Premium glassmorphism design
└── run_tests.py             # Batch PDF generator (no UI)
```

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (recommended) |
| `GROQ_API_KEY` | Groq API key (fallback) |
| `OPENAI_API_KEY` | OpenAI API key (legacy fallback) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (legacy fallback) |
