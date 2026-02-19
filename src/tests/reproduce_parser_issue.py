
import os
import sys
import django
from pathlib import Path

# Setup Django
# We are in /app, so 'apps' is directly importable if /app is in path?
# tests/reproduce_parser_issue.py is running.
# Let's add /app to sys.path just in case.
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.pdf_parser import PDFParserService
import fitz

def test_parser_reproduce():
    # PDF was copied to src/tests/405140.pdf
    # Inside container: /app/tests/405140.pdf
    pdf_path = Path("/app/tests/405140.pdf")

    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} not found.")
        # Try relative path
        pdf_path = Path("tests/405140.pdf")
        if not pdf_path.exists():
             print(f"ERROR: {pdf_path} also not found.")
             return

    print(f"Testing with file: {pdf_path}")

    # 1. Test with File Path
    print("\n--- Test 1: File Path ---")
    try:
        parser = PDFParserService(file_path=str(pdf_path))
        data = parser.parse()
        print(f"Text Length: {len(data['raw_text_preview'])}")
        print(f"Sample: {data['raw_text_preview'][:50]}")
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    # 2. Test with Bytes Stream
    print("\n--- Test 2: Bytes Stream ---")
    try:
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()

        parser = PDFParserService(file_stream=file_bytes)
        data = parser.parse()
        print(f"Text Length: {len(data['raw_text_preview'])}")
        print(f"Sample: {data['raw_text_preview'][:50]}")
    except Exception as e:
        print(f"Test 2 Failed: {e}")

if __name__ == "__main__":
    test_parser_reproduce()
