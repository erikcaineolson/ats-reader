"""ATS warning engine.

Combines format metadata + content analysis to flag potential issues.
"""

from __future__ import annotations

from ats_reader.models import (
    ATSWarning,
    ExtractionMetadata,
    ParsedResume,
    Severity,
)


def generate_warnings(
    parsed: ParsedResume,
    meta: ExtractionMetadata,
    raw_text: str,
) -> list[ATSWarning]:
    """Generate a prioritized list of ATS warnings."""
    warnings: list[ATSWarning] = []

    # --- CRITICAL ---

    if meta.has_tables:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Tables detected",
                "Many ATS systems scramble or skip table content. "
                "Avoid using tables for resume layout.",
            )
        )

    if meta.has_columns:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Multi-column layout detected",
                "ATS may read across columns instead of down each column, "
                "jumbling your content.",
            )
        )

    if meta.has_text_boxes:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Text boxes detected",
                "Most ATS systems completely ignore text inside text boxes. "
                "Move content into normal paragraphs.",
            )
        )

    if not parsed.contact.email:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "No email address found",
                "ATS could not extract an email. Ensure your email is in "
                "plain text in the document body (not a header/footer).",
            )
        )

    if not parsed.contact.name:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Could not identify candidate name",
                "The ATS couldn't determine your name. Make sure it's the "
                "first line of your resume in plain text.",
            )
        )

    if not parsed.sections:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "No sections detected",
                "ATS could not identify any standard sections (Experience, "
                "Education, Skills). Use clear section headings with "
                "conventional names.",
            )
        )

    if meta.file_type == "pdf" and meta.is_tagged_pdf is False:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "PDF is not tagged",
                "Untagged PDFs force the ATS to guess at structure from "
                "text coordinates — the #1 reason data gets missed.",
            )
        )

    # --- WARNING ---

    if meta.has_images:
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                "Images detected",
                "ATS cannot read text inside images. Any info in images "
                "(logos, icons, skill bars) will be lost.",
            )
        )

    if meta.has_headers_footers:
        detail_texts = ", ".join(
            f'"{t[:50]}"' for t in meta.header_footer_text[:3]
        )
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                "Content in headers/footers",
                f"Many ATS skip header/footer regions. Found: {detail_texts}. "
                "Move critical info into the document body.",
            )
        )

    if not parsed.contact.phone:
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                "No phone number found",
                "Consider adding a phone number in a standard format.",
            )
        )

    expected = {"experience", "education", "skills"}
    found = set(parsed.sections.keys())
    missing = expected - found
    if missing:
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                f"Missing common section(s): {', '.join(sorted(missing))}",
                "Standard ATS sections include Experience, Education, and Skills. "
                "Missing sections may mean the ATS can't categorize your data.",
            )
        )

    # Check for encoding issues
    if "\ufffd" in raw_text:
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                "Encoding issues detected",
                "Replacement characters (�) found in extracted text. "
                "Some characters may not parse correctly.",
            )
        )

    # --- INFO ---

    if meta.page_count > 2:
        warnings.append(
            ATSWarning(
                Severity.INFO,
                f"Resume is {meta.page_count} pages",
                "Most ATS process all pages, but recruiters typically "
                "prefer 1-2 page resumes.",
            )
        )

    if meta.fonts_used and len(meta.fonts_used) > 3:
        warnings.append(
            ATSWarning(
                Severity.INFO,
                f"{len(meta.fonts_used)} different fonts used",
                "Consider limiting to 1-2 fonts for cleaner parsing.",
            )
        )

    # Sort: CRITICAL first, then WARNING, then INFO
    order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    warnings.sort(key=lambda w: order.get(w.severity, 3))

    return warnings
