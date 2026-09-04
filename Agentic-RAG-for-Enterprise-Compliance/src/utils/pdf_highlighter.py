from __future__ import annotations

import logging
from pathlib import Path

import fitz

logger = logging.getLogger("aegis.highlighter")


def highlight_contract_pdf(source_pdf_path: str, output_pdf_path: str, quotes_to_highlight: list[str]) -> str:
    """
    Opens the source contract PDF, searches for non-compliant evidence quotes,
    and draws translucent yellow highlight annotations over matching text.
    """
    if not Path(source_pdf_path).exists():
        logger.warning("Source PDF %s not found for highlighting.", source_pdf_path)
        return source_pdf_path

    try:
        doc = fitz.open(source_pdf_path)
        highlights_count = 0

        for quote in quotes_to_highlight:
            quote_clean = quote.strip()
            if len(quote_clean) < 10:
                continue

            # Target key sub-phrases if full quote spans formatting boundaries
            search_snippets = [quote_clean[:60], quote_clean[-60:]] if len(quote_clean) > 80 else [quote_clean]

            for snippet in search_snippets:
                for page in doc:
                    quads = page.search_for(snippet)
                    if quads:
                        annot = page.add_highlight_annot(quads)
                        annot.set_colors(stroke=(1, 0.9, 0.3))  # Soft gold highlight
                        annot.update()
                        highlights_count += 1

        doc.save(output_pdf_path)
        doc.close()
        logger.info("Successfully highlighted %s target quotes in %s", highlights_count, output_pdf_path)
        return output_pdf_path
    except Exception as exc:
        logger.error("Failed to generate highlighted PDF: %s", exc)
        return source_pdf_path
