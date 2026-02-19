
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append('src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.pdf_parser import PDFParserService
import fitz

def test_parser_reproduce():
    # Use the same file the user mentioned
    pdf_path = Path("pdf/405140.pdf")

    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} not found.")
        return

    print(f"Testing with file: {pdf_path}")

    # 1. Test with File Path (Like User's Script)
    print("\n--- Test 1: File Path ---")
    try:
        # Note: PDFParserService currently only accepts 'file_stream',
        # but I updated it earlier to accept file_path?
        # Let's check the code I wrote in Step 2959 (ish).
        # Ah, I updated __init__ to accept file_path too.
        parser = PDFParserService(file_path=str(pdf_path))
        data = parser.parse()
        print(f"Text Length: {len(data['raw_text_preview'])}")
        print(f"Sample: {data['raw_text_preview'][:50]}")
    except Exception as e:
        print(f"Test 1 Failed: {e}")

    # 2. Test with Bytes Stream (Like Django Upload)
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
