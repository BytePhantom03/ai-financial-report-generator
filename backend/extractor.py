import io
import csv
import pypdf

# Try to import OCR tools (installed dynamically)
try:
    import pypdfium2 as pdfium
    import easyocr
    import numpy as np
    OCR_AVAILABLE = True
    reader = None # Initialize lazily
except ImportError:
    OCR_AVAILABLE = False


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    ext = filename.split(".")[-1].lower()

    try:
        if ext == "pdf":
            # 1. Standard text extraction (fast)
            pdf = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            
            for i in range(min(25, len(pdf.pages))):
                page_text = pdf.pages[i].extract_text()
                pages_text.append(page_text)
            
            full_text = "\n\n".join(pages_text)
            
            # 2. If OCR is available, ALSO run OCR to get text from charts/images
            if OCR_AVAILABLE:
                print("Running EasyOCR to extract text from charts and images...")
                global reader
                if reader is None:
                    # Load model into memory once (English)
                    reader = easyocr.Reader(['en'], gpu=False)
                
                ocr_text_blocks = []
                pdf_doc = pdfium.PdfDocument(file_bytes)
                
                # Limit to first 10 pages for OCR to prevent timeouts
                for i in range(min(10, len(pdf_doc))):
                    page = pdf_doc[i]
                    # Render page to a numpy array image (scale=2 for decent resolution)
                    bitmap = page.render(scale=2.0)
                    img_array = bitmap.to_numpy()
                    
                    # Run OCR on the rendered image
                    results = reader.readtext(img_array, detail=0)
                    ocr_text_blocks.append(" ".join(results))
                    
                full_text += "\n\n--- OCR EXTRACTED CONTENT (CHARTS/IMAGES) ---\n\n"
                full_text += "\n\n".join(ocr_text_blocks)

            return full_text

        elif ext == "csv":
            rows = list(csv.reader(io.StringIO(file_bytes.decode("utf-8"))))
            return "\n".join(", ".join(r) for r in rows)

        elif ext in ("txt", "md"):
            return file_bytes.decode("utf-8")

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    except Exception as e:
        raise ValueError(f"Failed to extract text from {filename}: {e}")
