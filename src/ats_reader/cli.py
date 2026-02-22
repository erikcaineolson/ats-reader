"""CLI entry point for ATS Reader."""

from __future__ import annotations

from pathlib import Path

import click

from ats_reader.extractor import extract_fields
from ats_reader.models import ATSResult, ExtractionMetadata
from ats_reader.output import console, print_json, print_raw_only, print_result
from ats_reader.structure import analyze_docx_structure, analyze_pdf_structure
from ats_reader.warnings import generate_warnings


@click.command()
@click.argument("resume", type=click.Path(exists=True, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option("--raw-only", is_flag=True, help="Output only the raw extracted text.")
@click.version_option(package_name="ats-reader")
def main(resume: Path, as_json: bool, raw_only: bool) -> None:
    """Simulate how an ATS parses your resume.

    RESUME is the path to a .pdf or .docx file.
    """
    suffix = resume.suffix.lower()

    if suffix == ".pdf":
        result = _process_pdf(resume)
    elif suffix in (".docx", ".doc"):
        if suffix == ".doc":
            console.print(
                "[yellow]Warning: .doc format has limited support. "
                "Convert to .docx for best results.[/yellow]"
            )
        result = _process_docx(resume)
    else:
        raise click.BadParameter(
            f"Unsupported file type: {suffix}. Use .pdf or .docx.",
            param_hint="RESUME",
        )

    if as_json:
        print_json(result)
    elif raw_only:
        print_raw_only(result)
    else:
        print_result(result)


def _process_pdf(path: Path) -> ATSResult:
    from ats_reader.parser_pdf import parse_pdf

    raw_text, meta = parse_pdf(path)
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
