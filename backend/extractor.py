import io
import csv
import pypdf


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    ext = filename.split(".")[-1].lower()

    try:
        if ext == "pdf":
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [reader.pages[i].extract_text() for i in range(min(25, len(reader.pages)))]
            return "\n\n".join(pages)

        elif ext == "csv":
            rows = list(csv.reader(io.StringIO(file_bytes.decode("utf-8"))))
            return "\n".join(", ".join(r) for r in rows)

        elif ext in ("txt", "md"):
            return file_bytes.decode("utf-8")

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    except Exception as e:
        raise ValueError(f"Failed to extract text from {filename}: {e}")
