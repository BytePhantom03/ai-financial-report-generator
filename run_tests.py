"""
Test runner: generates the two required example PDFs.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from extractor import extract_text_from_file
from llm_parser import parse_financial_document
from pdf_generator import build_pdf

def generate_example(company_name, input_filepath, output_pdfname):
    print(f"\n{'='*60}")
    print(f"  Generating: {company_name}")
    print(f"  Source: {input_filepath}")
    print(f"{'='*60}")

    with open(input_filepath, "rb") as f:
        file_bytes = f.read()

    print("  [1/3] Extracting text...")
    text = extract_text_from_file(os.path.basename(input_filepath), file_bytes)
    print(f"  -> Extracted {len(text)} characters")

    print("  [2/3] Parsing financial data...")
    parsed_data = parse_financial_document(company_name, text)
    print(f"  -> Company: {parsed_data.company_name}")
    print(f"  -> Sector: {parsed_data.sector}")
    print(f"  -> Highlights: {len(parsed_data.highlights)} bullet points")
    print(f"  -> Income Statement rows: {len(parsed_data.financials.income_statement)}")
    print(f"  -> Balance Sheet rows: {len(parsed_data.financials.balance_sheet)}")
    print(f"  -> Ratio rows: {len(parsed_data.financials.ratios)}")

    print("  [3/3] Compiling PDF...")
    os.makedirs("output", exist_ok=True)
    pdf_path = os.path.join("output", output_pdfname)
    build_pdf(parsed_data, pdf_path)
    
    file_size = os.path.getsize(pdf_path) / 1024
    print(f"\n  [OK] SUCCESS: {pdf_path} ({file_size:.1f} KB)")


if __name__ == "__main__":
    # Example 1: ICICI Bank (PDF input)
    if os.path.exists("ICICI Q2FY26.pdf"):
        generate_example("ICICI Bank Ltd.", "ICICI Q2FY26.pdf", "ICICI_Bank_Research_Report.pdf")
    else:
        print("WARNING: ICICI Q2FY26.pdf not found")

    # Example 2: Eternal/Zomato (TXT input - proving multi-format support)
    if os.path.exists("geojit_text.txt"):
        generate_example("Eternal Ltd. (Zomato)", "geojit_text.txt", "Eternal_Zomato_Research_Report.pdf")
    else:
        print("WARNING: geojit_text.txt not found")

    print(f"\n{'='*60}")
    print("  All examples generated in ./output/")
    print(f"{'='*60}")
