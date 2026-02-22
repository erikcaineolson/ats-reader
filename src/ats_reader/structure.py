"""Document structure analysis — the differentiator.

Analyzes *why* an ATS might miss data based on document tagging and styles.
"""

from __future__ import annotations

from ats_reader.models import ExtractionMetadata, Severity, StructureFeedback
from ats_reader.parser_docx import ParagraphStyle


# ---------------------------------------------------------------------------
# PDF structure analysis
# ---------------------------------------------------------------------------

def analyze_pdf_structure(meta: ExtractionMetadata) -> list[StructureFeedback]:
    """Produce structure feedback for a PDF document."""
    feedback: list[StructureFeedback] = []

    if meta.is_tagged_pdf is False:
        feedback.append(
            StructureFeedback(
                severity=Severity.CRITICAL,
                element="PDF Structure",
                issue=(
                    "This PDF has no tagged structure. ATS systems must guess "
                    "at sections and reading order purely from text coordinates, "
                    "which is unreliable."
                ),
                suggestion=(
                    "Export from Word/Docs with 'Tagged PDF' enabled, or use "
                    "Adobe Acrobat to add tags. A tagged PDF explicitly defines "
                    "headings, lists, and reading order so the ATS doesn't have to guess."
                ),
            )
        )
    elif meta.is_tagged_pdf is True:
        feedback.append(
            StructureFeedback(
                severity=Severity.INFO,
                element="PDF Structure",
                issue="This PDF has tagged structure — reading order and sections are defined.",
                suggestion="Good. The ATS can follow the document's defined structure.",
            )
        )

    if meta.has_columns:
        feedback.append(
            StructureFeedback(
                severity=Severity.WARNING,
                element="Column Layout",
                issue=(
                    "Multi-column layout detected. Without tags, ATS may read "
                    "across columns (left-right) instead of down each column."
                ),
                suggestion=(
                    "Use a single-column layout, or ensure the PDF is tagged "
                    "so reading order is explicit."
                ),
            )
        )

    if meta.has_tables:
        feedback.append(
            StructureFeedback(
                severity=Severity.WARNING,
                element="Tables",
                issue=(
                    "Tables detected. Some ATS systems skip table content or "
                    "scramble cell reading order."
                ),
                suggestion=(
                    "Avoid using tables for layout. If you must, keep them "
                    "simple (no merged cells) and ensure the PDF is tagged."
                ),
            )
        )

    return feedback


# ---------------------------------------------------------------------------
# DOCX structure analysis
# ---------------------------------------------------------------------------

def analyze_docx_structure(
    meta: ExtractionMetadata,
    paragraph_styles: list[ParagraphStyle],
) -> list[StructureFeedback]:
    """Produce structure feedback for a DOCX document."""
    feedback: list[StructureFeedback] = []

    # --- Heading style usage ---
    heading_paras = [p for p in paragraph_styles if p.is_heading]
    bold_non_heading = [
        p
        for p in paragraph_styles
        if p.is_bold
        and not p.is_heading
        and p.text
        and len(p.text) < 60
        and p.font_size is not None
        and p.font_size >= 12
    ]

    if not heading_paras and bold_non_heading:
        feedback.append(
            StructureFeedback(
                severity=Severity.CRITICAL,
                element="Section Headings",
                issue=(
                    "No Heading styles are used anywhere in the document. "
                    "Section titles appear to use manual bold/font-size formatting. "
                    "ATS systems key off named styles to find sections — manual "
                    "formatting is invisible to them."
                ),
                suggestion=(
                    "Apply 'Heading 1' or 'Heading 2' styles to your section titles "
                    "(Experience, Education, Skills, etc.) instead of just making "
                    "text bold or larger."
                ),
            )
        )
        # Give specific examples
        for p in bold_non_heading[:3]:
            size_note = f" ({p.font_size}pt)" if p.font_size else ""
            feedback.append(
                StructureFeedback(
                    severity=Severity.WARNING,
                    element="Possible Heading",
                    issue=(
                        f'"{p.text}" uses bold{size_note} with style '
                        f'"{p.style_name}" — ATS may not recognize it as a section heading.'
                    ),
                    suggestion=(
                        f'Change the style of "{p.text}" to Heading 1 or Heading 2.'
                    ),
                )
            )
    elif heading_paras:
        feedback.append(
            StructureFeedback(
                severity=Severity.INFO,
                element="Section Headings",
                issue=f"{len(heading_paras)} Heading style(s) found — ATS can identify sections.",
                suggestion="Good. Named Heading styles give the ATS clear section markers.",
            )
        )
        # Check for mixed approach
        if bold_non_heading:
            feedback.append(
                StructureFeedback(
                    severity=Severity.WARNING,
                    element="Mixed Heading Styles",
                    issue=(
                        f"{len(bold_non_heading)} bold short paragraph(s) don't use "
                        "Heading styles. These may be section headings the ATS misses."
                    ),
                    suggestion=(
                        "Review bold short lines and apply Heading styles where appropriate."
                    ),
                )
            )

    # --- List style usage ---
    manual_bullet_paras = [p for p in paragraph_styles if p.has_manual_bullet and not p.is_list_style]
    list_style_paras = [p for p in paragraph_styles if p.is_list_style]

    if manual_bullet_paras and not list_style_paras:
        feedback.append(
            StructureFeedback(
                severity=Severity.WARNING,
                element="List Items",
                issue=(
                    f"{len(manual_bullet_paras)} line(s) use manual bullet characters "
                    "(•, -, etc.) instead of Word's List Paragraph style. ATS may merge "
                    "these into a single paragraph or lose the bullet structure."
                ),
                suggestion=(
                    "Use Word's built-in bullet list feature (List Paragraph / List Bullet "
                    "style) instead of typing bullet characters manually."
                ),
            )
        )
    elif manual_bullet_paras and list_style_paras:
        feedback.append(
            StructureFeedback(
                severity=Severity.INFO,
                element="List Items",
                issue=(
                    f"{len(list_style_paras)} list-styled items found, but "
                    f"{len(manual_bullet_paras)} also use manual bullets."
                ),
                suggestion="Convert remaining manual bullets to proper list styles for consistency.",
            )
        )

    # --- Body text style ---
    normal_paras = [p for p in paragraph_styles if p.style_name == "Normal"]
    non_standard = [
        p
        for p in paragraph_styles
        if p.style_name
        and p.style_name not in (
            "Normal", "List Paragraph", "List Bullet", "List Number",
        )
        and not p.is_heading
        and p.text
    ]
    custom_count = len(non_standard)
    if custom_count > 5 and not normal_paras:
        feedback.append(
            StructureFeedback(
                severity=Severity.WARNING,
                element="Body Text Styles",
                issue=(
                    f"No 'Normal' style paragraphs found; {custom_count} paragraphs use "
                    "custom or unnamed styles. Some ATS may not process non-standard styles."
                ),
                suggestion="Use the 'Normal' style for body text paragraphs.",
            )
        )

    # --- Text boxes ---
    if meta.has_text_boxes:
        feedback.append(
            StructureFeedback(
                severity=Severity.CRITICAL,
                element="Text Boxes",
                issue=(
                    "Text boxes detected. Most ATS systems completely ignore "
                    "text inside text boxes — that content is invisible to the parser."
                ),
                suggestion=(
                    "Move all content out of text boxes into regular paragraphs."
                ),
            )
        )

    # --- Tables ---
    if meta.has_tables:
        feedback.append(
            StructureFeedback(
                severity=Severity.WARNING,
                element="Tables",
                issue=(
                    "Tables detected. ATS may scramble cell order or skip table content."
                ),
                suggestion=(
                    "Avoid using tables for layout. Use them only for genuinely "
                    "tabular data, and keep them simple (no merged cells)."
                ),
            )
        )

    # --- Headers/footers ---
    if meta.has_headers_footers:
        feedback.append(
            StructureFeedback(
                severity=Severity.WARNING,
                element="Headers/Footers",
                issue=(
                    "Content found in headers/footers. Many ATS systems skip "
                    "header and footer regions entirely."
                ),
                suggestion=(
                    "Don't put critical info (name, email, phone) in headers "
                    "or footers. Move it into the document body."
                ),
            )
        )

    return feedback
