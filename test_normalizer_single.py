import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path so we can import Django/Services
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Set up minimal django environment if needed in the future,
# although our services should be pure Python right now.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.core.services.imports.pdf_parser import PDFParserService
from apps.core.services.imports.normalize import normalize_booking_text

def process_single_pdf(pdf_path: str):
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"Error: Could not find file {pdf_file}")
        sys.exit(1)

    print(f"--- Processing: {pdf_file.name} ---")

    # 1. Run Parser
    print("1. Running PDFParserService...")
    with open(pdf_file, "rb") as f:
        parser = PDFParserService(f)
        raw_data = parser.parse()
        parser.close()

    raw_text = raw_data.get('raw_text_preview', '')
    if not raw_text:
        print("Warning: parser returned no raw text.")

    # Try to extract Booking ID to use as filename
    import re
    bk_guess = re.findall(r"\d{5,6}", pdf_file.stem)
    bk = bk_guess[0] if bk_guess else "UNKNOWN"

    # 2. Run Normalizer
    print("2. Running NormalizationService...")
    print("--- RAW TEXT HEAD ---")
    print(raw_text[:1000]) # Look at the top of the file where clients usually are
    print("---------------------")

    normalized_plan = normalize_booking_text(bk, raw_text)

    # 3. Save Output
    output_dir = Path("pdf/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    out_file = output_dir / f"{pdf_file.stem}_normalized.json"

    with open(out_file, "w", encoding="utf-8") as out_f:
        json.dump(normalized_plan, out_f, indent=2, ensure_ascii=False)

    print(f"SUCCESS! Output saved to: {out_file}")
    print(f"  Notifications generated: {len(normalized_plan.get('notifications', []))}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Parser + Normalizer against a single PDF.")
    parser.add_argument("pdf_path", help="Path to the raw PDF file to test.")
    args = parser.parse_args()

    process_single_pdf(args.pdf_path)
