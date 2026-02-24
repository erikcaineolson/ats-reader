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
from ats_reader.structure import detect_design_tool


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
                fix=(
                    "Replace tables with plain paragraphs and use tab stops or "
                    "spacing to align content (e.g. 'Job Title — Company — Dates' "
                    "on one line)."
                ),
            )
        )

    if meta.has_columns:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Multi-column layout detected",
                "ATS may read across columns instead of down each column, "
                "jumbling your content.",
                fix=(
                    "Reformat your resume to use a single-column layout. Remove "
                    "column breaks or section columns in your word processor."
                ),
            )
        )

    if meta.has_text_boxes:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Text boxes detected",
                "Most ATS systems completely ignore text inside text boxes. "
                "Move content into normal paragraphs.",
                fix=(
                    "Select each text box, copy its content, delete the text box, "
                    "then paste the content as a regular paragraph."
                ),
            )
        )

    if not parsed.contact.email:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "No email address found",
                "ATS could not extract an email. Ensure your email is in "
                "plain text in the document body (not a header/footer).",
                fix=(
                    "Add your email address as plain text near the top of the "
                    "document body. Don't put it in a header, footer, or text box, "
                    "and don't use a mailto: hyperlink without visible text."
                ),
            )
        )

    if not parsed.contact.name:
        warnings.append(
            ATSWarning(
                Severity.CRITICAL,
                "Could not identify candidate name",
                "The ATS couldn't determine your name. Make sure it's the "
                "first line of your resume in plain text.",
                fix=(
                    "Make your full name the very first line of the document, "
                    "using a larger font or Heading style. Don't put it inside "
                    "a header, text box, or image."
                ),
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
                fix=(
                    "Add section headings like 'Experience', 'Education', and "
                    "'Skills' using your word processor's Heading styles (not "
                    "just bold text). Use standard names — avoid creative labels "
                    "like 'Where I've Been' instead of 'Experience'."
                ),
            )
        )

    if meta.file_type == "pdf" and meta.is_tagged_pdf is False:
        tool = detect_design_tool(meta)
        if tool:
            warnings.append(
                ATSWarning(
                    Severity.CRITICAL,
                    f"PDF is not tagged (created with {tool})",
                    f"This PDF was built in {tool}, which produces visually "
                    "polished but untagged PDFs. ATS systems cannot reliably "
                    "read the structure, so your data is likely getting lost.",
                    fix=(
                        f"Copy your content into a Word or Google Docs template "
                        f"with Heading styles and a single-column layout, then "
                        f"export to PDF. Keep the {tool} version for networking "
                        f"or direct emails where you know a human will read it."
                    ),
                )
            )
        else:
            warnings.append(
                ATSWarning(
                    Severity.CRITICAL,
                    "PDF is not tagged",
                    "Untagged PDFs force the ATS to guess at structure from "
                    "text coordinates — the #1 reason data gets missed.",
                    fix=(
                        "Re-export from Word (File > Save As > PDF with 'Best for "
                        "electronic distribution' or 'Tagged PDF' checked). In Google "
                        "Docs, download as DOCX first, then export to PDF from Word."
                    ),
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
                fix=(
                    "Remove decorative images. Replace skill-bar graphics or "
                    "icon-based contact info with plain text equivalents."
                ),
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
                fix=(
                    "Double-click the header/footer area in Word to edit it, "
                    "cut the content, then paste it into the main document body "
                    "near the top of page 1."
                ),
            )
        )

    if not parsed.contact.phone:
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                "No phone number found",
                "Consider adding a phone number in a standard format.",
                fix=(
                    "Add a phone number in a standard format like (555) 123-4567 "
                    "or 555-123-4567 near your other contact information."
                ),
            )
        )

    expected = {"experience", "education", "skills"}
    found = set(parsed.sections.keys())
    missing = expected - found
    if missing:
        missing_names = ", ".join(sorted(missing))
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                f"Missing common section(s): {missing_names}",
                "Standard ATS sections include Experience, Education, and Skills. "
                "Missing sections may mean the ATS can't categorize your data.",
                fix=(
                    f"Add a section heading for each missing section ({missing_names}). "
                    "Use the exact conventional name and apply a Heading style in "
                    "your word processor."
                ),
            )
        )

    # Check for encoding issues
    if "\ufffd" in raw_text:
        warnings.append(
            ATSWarning(
                Severity.WARNING,
                "Encoding issues detected",
                "Replacement characters (\ufffd) found in extracted text. "
                "Some characters may not parse correctly.",
                fix=(
                    "Open your resume and replace special characters (smart quotes, "
                    "em dashes, bullet symbols) with standard ASCII equivalents. "
                    "Re-save and check again."
                ),
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
                fix=(
                    "Trim older or less-relevant positions to brief mentions, "
                    "and cut bullet points to your top 3-5 per role."
                ),
            )
        )

    if meta.fonts_used and len(meta.fonts_used) > 3:
        warnings.append(
            ATSWarning(
                Severity.INFO,
                f"{len(meta.fonts_used)} different fonts used",
                "Consider limiting to 1-2 fonts for cleaner parsing.",
                fix=(
                    "Pick one font for body text and optionally a second for "
                    "headings. Select all (Ctrl+A / Cmd+A) and apply your body "
                    "font, then re-style headings."
                ),
            )
        )

    # Sort: CRITICAL first, then WARNING, then INFO
    order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    warnings.sort(key=lambda w: order.get(w.severity, 3))

    return warnings
