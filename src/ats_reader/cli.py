"""CLI entry point for ATS Reader."""

from __future__ import annotations

from pathlib import Path

import click

from ats_reader.extractor import extract_fields
from ats_reader.models import ATSResult, ExtractionMetadata
from ats_reader.output import console, print_json, print_raw_only, print_result
from ats_reader.structure import analyze_docx_structure, analyze_pdf_structure
from ats_reader.warnings import generate_warnings

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
DEFAULT_MAX_PAGES = 20


@click.command()
@click.argument("resume", type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--raw-only", is_flag=True, help="Output only the raw extracted text.")
@click.option(
    "--max-pages",
    type=int,
    default=DEFAULT_MAX_PAGES,
    show_default=True,
    help="Maximum number of PDF pages to process.",
)
@click.version_option(package_name="ats-reader")
def main(resume: Path, as_json: bool, raw_only: bool, max_pages: int) -> None:
    """Simulate how an ATS parses your resume.

    RESUME is the path to a .pdf or .docx file.
    """
    suffix = resume.suffix.lower()

    # Reject .doc (legacy binary format) — python-docx cannot parse it.
    if suffix == ".doc":
        raise click.BadParameter(
            "The legacy .doc format is not supported. "
            "Please convert to .docx (File → Save As → .docx) and try again.",
            param_hint="RESUME",
        )

    if suffix not in (".pdf", ".docx"):
        raise click.BadParameter(
            f"Unsupported file type: {suffix}. Use .pdf or .docx.",
            param_hint="RESUME",
        )

    # Guard against oversized files.
    file_size = resume.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        raise click.BadParameter(
            f"File is {size_mb:.1f} MB — maximum supported size is {MAX_FILE_SIZE_MB} MB.",
            param_hint="RESUME",
        )

    try:
        if suffix == ".pdf":
            result = _process_pdf(resume, max_pages)
        else:
            result = _process_docx(resume)
    except click.exceptions.Exit:
        raise
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] Could not parse {resume.name}.")
        console.print(f"[dim]{type(exc).__name__}: {exc}[/dim]")
        raise SystemExit(1) from exc

    if as_json:
        print_json(result)
    elif raw_only:
        print_raw_only(result)
    else:
        print_result(result)


def _process_pdf(path: Path, max_pages: int) -> ATSResult:
    from ats_reader.parser_pdf import parse_pdf

    raw_text, meta = parse_pdf(path, max_pages=max_pages)
    parsed = extract_fields(raw_text)
    structure = analyze_pdf_structure(meta)
    warnings = generate_warnings(parsed, meta, raw_text)

    return ATSResult(
        raw_text=raw_text,
        parsed=parsed,
        metadata=meta,
        warnings=warnings,
        structure_feedback=structure,
    )


def _process_docx(path: Path) -> ATSResult:
    from ats_reader.parser_docx import parse_docx

    raw_text, meta, paragraph_styles = parse_docx(path)
    parsed = extract_fields(raw_text)
    structure = analyze_docx_structure(meta, paragraph_styles)
    warnings = generate_warnings(parsed, meta, raw_text)

    return ATSResult(
        raw_text=raw_text,
        parsed=parsed,
        metadata=meta,
        warnings=warnings,
        structure_feedback=structure,
    )
