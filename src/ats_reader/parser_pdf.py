"""PDF resume extraction via pdfplumber."""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from ats_reader.models import ExtractionMetadata


def parse_pdf(path: Path) -> tuple[str, ExtractionMetadata]:
    """Extract text and metadata from a PDF resume.

    Returns (raw_text, metadata).
    """
    meta = ExtractionMetadata(file_type="pdf")
    pages_text: list[str] = []

    with pdfplumber.open(path) as pdf:
        meta.page_count = len(pdf.pages)

        # Check tagged PDF structure
        meta.is_tagged_pdf = _check_tagged(pdf)

        fonts: set[str] = set()

        for page in pdf.pages:
            # Text extraction (layout-aware)
            text = page.extract_text(layout=True) or ""
            pages_text.append(text)

            # Tables
            tables = page.find_tables()
            if tables:
                meta.has_tables = True

            # Images
            if page.images:
                meta.has_images = True

            # Column detection via word x-coordinate clustering
            words = page.extract_words()
            if _detect_columns(words, page.width):
                meta.has_columns = True

            # Header/footer regions (top/bottom 10%)
            h_texts, f_texts = _extract_header_footer(words, page.height)
            meta.header_footer_text.extend(h_texts)
            meta.header_footer_text.extend(f_texts)
            if h_texts or f_texts:
                meta.has_headers_footers = True

            # Fonts
            if hasattr(page, "chars"):
                for char in page.chars:
                    fontname = char.get("fontname", "")
                    if fontname:
                        fonts.add(fontname)

        meta.fonts_used = sorted(fonts)

    raw_text = "\n".join(pages_text)
    return raw_text, meta


def _check_tagged(pdf: pdfplumber.PDF) -> bool:
    """Check if the PDF has tagged structure (MarkInfo / StructTreeRoot)."""
    try:
        catalog = pdf.doc.catalog
        if catalog is None:
            return False
        has_mark_info = "MarkInfo" in catalog
        has_struct_tree = "StructTreeRoot" in catalog
        return has_mark_info or has_struct_tree
    except Exception:
        return False


def _detect_columns(words: list[dict], page_width: float) -> bool:
    """Detect multi-column layout by clustering word x-coordinates."""
    if not words or page_width == 0:
        return False

    # Group words by approximate y-coordinate (same line)
    lines: dict[int, list[float]] = {}
    for w in words:
        y_bucket = round(w["top"] / 5) * 5
        lines.setdefault(y_bucket, []).append(w["x0"])

    # Look for lines where there's a large gap in the middle
    column_lines = 0
    total_lines = 0
    mid_zone_start = page_width * 0.3
    mid_zone_end = page_width * 0.7

    for y_bucket, x_positions in lines.items():
        if len(x_positions) < 2:
            continue
        total_lines += 1
        x_sorted = sorted(x_positions)
        for i in range(1, len(x_sorted)):
            gap = x_sorted[i] - x_sorted[i - 1]
            gap_start = x_sorted[i - 1]
            if gap > page_width * 0.15 and mid_zone_start < gap_start < mid_zone_end:
                column_lines += 1
                break

    if total_lines == 0:
        return False
    return column_lines / total_lines > 0.3


def _extract_header_footer(
    words: list[dict], page_height: float
) -> tuple[list[str], list[str]]:
    """Extract text in top/bottom 10% of the page."""
    header_words: list[str] = []
    footer_words: list[str] = []
    threshold = page_height * 0.10

    for w in words:
        text = w.get("text", "").strip()
        if not text:
            continue
        if w["top"] < threshold:
            header_words.append(text)
        elif w["bottom"] > page_height - threshold:
            footer_words.append(text)

    header = [" ".join(header_words)] if header_words else []
    footer = [" ".join(footer_words)] if footer_words else []
    return header, footer
