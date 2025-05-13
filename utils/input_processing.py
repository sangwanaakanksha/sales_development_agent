# utils/input_processing.py

import os
import re
import pdfplumber
import json

from langchain.llms import OpenAI
from utils.database import save_stage

def process_input_file(file_path: str, event_name: str = None):
    """
    1. Reads a PDF and extracts company names/entities via LLM.
    2. Cleans the names (removes numeric prefixes, trims whitespace).
    3. Uses `event_name` (or the PDF filename) as the key.
    4. Snapshots the cleaned list to db/input.csv.
    5. Returns { event_name: [cleaned_names] }.
    """
    # 1) Read PDF text
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        raise RuntimeError(f"Error reading PDF: {e}")

    # 2) LLM extraction
    llm = OpenAI(temperature=0.1)
    prompt = (
        "Extract a JSON list of company names from the text below:\n\n"
        + text
    )
    resp = llm(prompt)
    try:
        names = json.loads(resp)
    except Exception:
        names = [line.strip() for line in resp.splitlines() if line.strip()]

    # 3) Clean names (remove leading numbers)
    cleaned = [re.sub(r'^\d+\.\s*', '', name).strip() for name in names]

    # 4) Save cleaned list to CSV
    save_stage(cleaned, "input")

    # 5) Build mapping
    if not event_name:
        # Default key = PDF filename without extension
        event_name = os.path.splitext(os.path.basename(file_path))[0]
    return { event_name: cleaned }
