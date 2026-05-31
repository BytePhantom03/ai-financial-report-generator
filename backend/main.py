import uuid
import os
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from extractor import extract_text_from_file
from llm_parser import parse_financial_document
from pdf_generator import build_pdf

app = FastAPI(title="Geojit AI Research Report Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}


def process_document_job(
    job_id: str,
    company_name: str,
    filename: str,
    file_bytes: bytes,
):
    try:
        jobs[job_id]["status"] = "EXTRACTING_TEXT"
        text = extract_text_from_file(filename, file_bytes)

        jobs[job_id]["status"] = "ANALYZING_WITH_LLM"
        parsed_data = parse_financial_document(
            company_name,
            text,
            filename=filename,
            file_bytes=file_bytes,
        )
        jobs[job_id]["extracted_data"] = parsed_data.model_dump()
        jobs[job_id]["ai_provider"] = _detect_provider()

        jobs[job_id]["status"] = "COMPILING_PDF"
        pdf_path = f"temp_charts/{job_id}_report.pdf"
        os.makedirs("temp_charts", exist_ok=True)
        build_pdf(parsed_data, pdf_path)

        jobs[job_id]["pdf_path"] = pdf_path
        jobs[job_id]["status"] = "COMPLETED"
    except Exception as e:
        jobs[job_id]["status"] = "FAILED"
        jobs[job_id]["error"] = str(e)
        import traceback
        print(traceback.format_exc())


def _detect_provider() -> str:
    from config import GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY
    if GEMINI_API_KEY:
        return "Gemini 2.0 Flash"
    if GROQ_API_KEY:
        return "Groq Llama 3.1"
    if OPENAI_API_KEY:
        return "OpenAI GPT-4o-mini"
    return "Rule-based Engine"


@app.post("/api/extract")
async def extract_document(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    file: UploadFile = File(...),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in {"pdf", "csv", "txt"}:
        return JSONResponse(status_code=400, content={"error": "Only PDF, CSV, and TXT files are supported."})

    job_id = str(uuid.uuid4())
    file_bytes = await file.read()

    jobs[job_id] = {
        "id": job_id,
        "company_name": company_name,
        "filename": file.filename,
        "status": "PENDING",
    }

    background_tasks.add_task(
        process_document_job, job_id, company_name, file.filename or "document", file_bytes
    )
    return JSONResponse(status_code=202, content={"id": job_id, "status": "PENDING", "company_name": company_name})


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return jobs[job_id]


@app.get("/api/download/{job_id}")
async def download_pdf(job_id: str):
    if job_id not in jobs or jobs[job_id]["status"] != "COMPLETED":
        return JSONResponse(status_code=400, content={"error": "PDF not ready"})
    pdf_path = jobs[job_id]["pdf_path"]
    filename = f"{jobs[job_id]['company_name'].replace(' ', '_')}_Research_Report.pdf"
    return FileResponse(pdf_path, filename=filename, media_type="application/pdf")


@app.get("/api/health")
async def health():
    from config import GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY
    return {
        "status": "ok",
        "gemini": bool(GEMINI_API_KEY),
        "groq":   bool(GROQ_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "active_provider": _detect_provider(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
