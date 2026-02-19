import json
from pathlib import Path
import fitz  # PyMuPDF


def extract_text(pdf_path: Path):
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            pages.append({"page": i, "text": text})

    return pages


def main():
    # Directory containing PDFs (current directory by default)
    pdf_dir = Path(".")

    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")

        pages = extract_text(pdf_path)

        out_txt = pdf_path.with_suffix(".txt")
        out_json = pdf_path.with_suffix(".json")

        # Write TXT
        with out_txt.open("w", encoding="utf-8") as f:
            for p in pages:
                f.write(f"=== Page {p['page']} ===\n")
                f.write(p["text"] + "\n\n")

        # Write JSON
        with out_json.open("w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=2)

        print(f"  Saved: {out_txt}")
        print(f"  Saved: {out_json}")
        print(f"  Pages extracted: {len(pages)}\n")


if __name__ == "__main__":
    main()

