import argparse
import os
import sys

from src.database.pdf_processor import ingest_pdf_to_qdrant


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a local PDF into the Aegis Qdrant compliance index.")
    parser.add_argument("pdf_path", help="Path to the PDF file to ingest.")
    parser.add_argument("--jurisdiction", default="European Union")
    parser.add_argument("--execution-year", type=int, default=2026)
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: file '{args.pdf_path}' not found.")
        sys.exit(1)

    ingest_pdf_to_qdrant(
        file_path=args.pdf_path,
        document_name=os.path.basename(args.pdf_path),
        jurisdiction=args.jurisdiction,
        execution_year=args.execution_year,
    )


if __name__ == "__main__":
    main()
