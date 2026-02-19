
import sys
import os
from pathlib import Path

# Mock Django setup not needed for just fitz, but useful if we import service
# We will just use fitz directly to be raw and pure.
import fitz

def check_for_gremlins():
    pdf_path = Path("/app/tests/405140.pdf")
    if not pdf_path.exists():
        # Fallback for local run
        pdf_path = Path("tests/405140.pdf")

    print(f"Analyzing: {pdf_path}")

    try:
        # Simulate Stream Read
        with open(pdf_path, 'rb') as f:
            file_bytes = f.read()

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text("text")

        print(f"\n--- Analysis ---")
        print(f"Total Length: {len(full_text)}")

        # Check for Null Bytes
        null_count = full_text.count('\x00')
        print(f"Null Bytes (\\x00) count: {null_count}")

        # Check for non-printables (ASCII 0-31, excl \n, \r, \t)
        bad_chars = [ord(c) for c in full_text if ord(c) < 32 and c not in '\n\r\t']
        print(f"Other Control Chars count: {len(bad_chars)}")
        if len(bad_chars) > 0:
            print(f"Sample Control Chars: {[hex(c) for c in bad_chars[:10]]}")

        print(f"\n--- Raw Repr (First 100 chars) ---")
        print(repr(full_text[:100]))

        if null_count > 0:
            print("\nCONCLUSION: Null Bytes Detected. This confirms the Display Issue hypothesis.")
        else:
            print("\nCONCLUSION: No Null Bytes. The Null Byte hypothesis is WRONG.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_for_gremlins()
