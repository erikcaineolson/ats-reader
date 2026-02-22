"""Output formatting — Rich terminal display and JSON."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ats_reader.models import ATSResult, Severity


console = Console()

SEVERITY_STYLE = {
    Severity.CRITICAL: ("bold red", "CRITICAL"),
    Severity.WARNING: ("bold yellow", "WARNING"),
    Severity.INFO: ("bold blue", "INFO"),
}


def print_result(result: ATSResult) -> None:
    """Display the full ATS analysis in the terminal."""
    _print_raw_text(result)
    console.print()
    _print_parsed_fields(result)
    console.print()
    _print_structure_feedback(result)
    console.print()
    _print_warnings(result)


def print_raw_only(result: ATSResult) -> None:
    """Display only the raw extracted text."""
    console.print(result.raw_text)


def print_json(result: ATSResult) -> None:
    """Display the result as JSON."""
    console.print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Raw text panel
# ---------------------------------------------------------------------------

def _print_raw_text(result: ATSResult) -> None:
    page_info = f" ({result.metadata.page_count} page{'s' if result.metadata.page_count != 1 else ''})"
    console.print(
        Panel(
            result.raw_text or "[dim]No text extracted[/dim]",
            title=f"[bold]Raw Text — What the ATS Sees[/bold]{page_info}",
            border_style="cyan",
            expand=True,
        )
    )


# ---------------------------------------------------------------------------
# Parsed fields
# ---------------------------------------------------------------------------

def _print_parsed_fields(result: ATSResult) -> None:
    parsed = result.parsed

    # Contact info table
    table = Table(title="Contact Information", show_header=False, expand=True)
    table.add_column("Field", style="bold", width=12)
    table.add_column("Value")

    c = parsed.contact
    _add_field_row(table, "Name", c.name)
    _add_field_row(table, "Email", c.email)
    _add_field_row(table, "Phone", c.phone)
    _add_field_row(table, "LinkedIn", c.linkedin)
    _add_field_row(table, "Website", c.website)
    _add_field_row(table, "Location", c.location)
    console.print(table)

    # Summary
    if parsed.summary:
        console.print()
        console.print(Panel(parsed.summary, title="[bold]Summary[/bold]", border_style="green"))

    # Experience
    if parsed.experience:
        console.print()
        console.print("[bold]Experience[/bold]")
        for i, exp in enumerate(parsed.experience, 1):
            title = exp.title or "[unknown title]"
            company = exp.company or "[unknown company]"
            dates = exp.dates or ""
            console.print(f"  [bold]{i}. {title}[/bold] — {company}")
            if dates:
                console.print(f"     [dim]{dates}[/dim]")
            for desc in exp.descriptions:
                console.print(f"     • {desc}")

    # Education
    if parsed.education:
        console.print()
        console.print("[bold]Education[/bold]")
        for edu in parsed.education:
            degree = edu.degree or "[unknown degree]"
            school = edu.school or ""
            dates = edu.dates or ""
            console.print(f"  [bold]{degree}[/bold]")
            if school:
                console.print(f"     {school}")
            if dates:
                console.print(f"     [dim]{dates}[/dim]")
            for d in edu.details:
                console.print(f"     • {d}")

    # Skills
    if parsed.skills:
        console.print()
        console.print("[bold]Skills[/bold]")
        console.print(f"  {', '.join(parsed.skills)}")

    # Certifications
    if parsed.certifications:
        console.print()
        console.print("[bold]Certifications[/bold]")
        for cert in parsed.certifications:
            console.print(f"  • {cert}")

    # Sections found
    console.print()
    section_names = list(parsed.sections.keys())
    if section_names:
        console.print(f"[dim]Sections detected: {', '.join(section_names)}[/dim]")
    else:
        console.print("[dim]No standard sections detected[/dim]")


def _add_field_row(table: Table, label: str, value: str | None) -> None:
    if value:
        table.add_row(label, value)
    else:
        table.add_row(label, Text("not found", style="dim red"))


# ---------------------------------------------------------------------------
# Structure feedback
# ---------------------------------------------------------------------------

def _print_structure_feedback(result: ATSResult) -> None:
    if not result.structure_feedback:
        return

    console.print("[bold]Document Structure Analysis[/bold]")
    for fb in result.structure_feedback:
        style, label = SEVERITY_STYLE.get(fb.severity, ("", ""))
        console.print(f"  [{style}][{label}][/{style}] [bold]{fb.element}[/bold]")
        console.print(f"          {fb.issue}")
        console.print(f"          [green]→ {fb.suggestion}[/green]")


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------

def _print_warnings(result: ATSResult) -> None:
    if not result.warnings:
        console.print("[bold green]No ATS warnings — looking good![/bold green]")
        return

    console.print("[bold]ATS Warnings[/bold]")
    for w in result.warnings:
        style, label = SEVERITY_STYLE.get(w.severity, ("", ""))
        console.print(f"  [{style}][{label}][/{style}] {w.message}")
        if w.detail:
            console.print(f"          [dim]{w.detail}[/dim]")
