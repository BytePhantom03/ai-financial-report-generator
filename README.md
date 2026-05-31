# Geojit AI Research Report Generator

A production-ready startup MVP that automatically ingests corporate financial context documents (PDF/CSV/TXT), structures the raw financial data using AI (OpenAI GPT-4o-mini), and compiles it into a beautiful, downloadable PDF matching the Geojit Research Report template.

## System Architecture

The application is built on a clean, scalable single-repo full-stack architecture:
- **Backend**: Python **FastAPI**. Purely stateless and async for massive scalability. 
- **AI Extraction Engine**: Uses `openai` with strict **Pydantic** structured outputs to guarantee exact extraction of tables, ratios, and narratives.
- **PDF Compilation**: Uses `reportlab` Platypus for complex layout grids matching the exact Geojit templates, and `matplotlib` for dynamic chart rendering.
- **Frontend**: **React** + **Vite**, styled with **Tailwind CSS**. It features a modern HSL-based glassmorphic UI, drag-and-drop uploads, real-time extraction tracking, and a rich multi-tab interactive data preview dashboard.

## Where are the Template Fields Defined?
The exact data structure required to generate the Geojit PDF is defined rigorously in **`backend/schema.py`**.
This includes:
- `CompanyData` (Market Cap, Enterprise Value, Beta, etc.)
- `ShareholdingQuarter` (Promoters, FIIs, Public)
- `PricePerformanceRow` (3m, 6m, 1y returns)
- `ValuationMetric` (Rating, Target, CMP)
- `FinancialsBundle` (Income Statement, Balance Sheet, Cash Flows over FY23A-FY27E)

## How to Run Locally

### 1. Backend Setup (FastAPI)
Open a terminal in the root directory:
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
python main.py
```
The API will run on `http://localhost:8000`.

### 2. Frontend Setup (React/Vite)
Open a second terminal in the root directory:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

## Submission Output
The system includes an automated test runner `run_tests.py` that generates test PDFs directly from the backend pipeline.
