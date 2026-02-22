# ATS Reader

Simulate how an Applicant Tracking System parses your resume — see what it sees.

ATS Reader is a Python CLI tool that extracts and analyzes resume content the same way automated hiring systems do. It surfaces structural issues that cause data to be silently dropped during parsing, giving you actionable feedback before your resume reaches a recruiter.

## The Problem

Even well-formatted resumes lose critical data in ATS parsing due to structural issues that are invisible to human readers:

- **Untagged PDFs** — forces the ATS to guess reading order, scrambling content
- **Multi-column layouts** — parsed left-to-right across columns, mangling job history
- **Manual formatting** — bold text and font-size changes are ignored; only semantic heading styles are recognized
- **Manual bullets** — characters typed as bullets are not recognized as list items
- **Text boxes** — ignored entirely by most ATS parsers
- **Headers and footers** — contact information placed here is frequently lost

## Installation

Requires Python 3.10 or higher.

```bash
# Clone the repository
git clone https://github.com/erikcaineolson/ats-reader.git
cd ats-reader

# Install with pip
pip install .

# Or install in editable mode for development
pip install -e .
```

## Usage

```bash
# Analyze a resume (default rich terminal output)
ats-reader resume.pdf

# Analyze a DOCX file
ats-reader resume.docx

# Output results as JSON
ats-reader resume.pdf --json

# Print only the raw extracted text
ats-reader resume.pdf --raw-only

# Show version
ats-reader --version
```

Also runnable as a module:

```bash
python -m ats_reader resume.pdf
```

## Features

### Parsing

**PDF**
- Text extraction with layout awareness via `pdfplumber`
- PDF tagging detection (MarkInfo / StructTreeRoot)
- Multi-column layout detection
- Table and image presence detection
- Header and footer identification

**DOCX**
- Paragraph text and style extraction via `python-docx`
- Heading level analysis (semantic vs. manual bold)
- List style detection (proper vs. manual bullet characters)
- Text box, table, and image detection
- Header and footer content extraction

### Field Extraction

Extracts the following fields from raw resume text using pattern matching:

- Contact info: name, email, phone, LinkedIn, website, location
- Work experience: job titles, companies, dates, descriptions
- Education: degrees, institutions, dates
- Skills, certifications, and summary
- Section detection for: Experience, Education, Skills, Summary, Certifications, Projects, Volunteer, Publications, Awards

### Warnings and Feedback

Issues are categorized by severity:

| Severity | Meaning |
|----------|---------|
| CRITICAL | Data will be lost |
| WARNING  | Data may be compromised |
| INFO     | Best practice recommendation |

**Critical issues flagged:** untagged PDF, no name detected, no email detected, no sections detected, tables present, multi-column layout, text boxes detected.

**Warnings flagged:** missing phone number, missing standard sections, images present, content in headers/footers, character encoding issues.

**Info flags:** resume exceeds 2 pages, more than 3 fonts in use.

### Output Formats

- **Default** — Rich terminal output with color-coded panels, field tables, and categorized feedback
- `--json` — Full structured result serialized to JSON for programmatic use
- `--raw-only` — Plain extracted text as the ATS would receive it

## Architecture

```
CLI (cli.py)
  └── parser_pdf.py or parser_docx.py   # Format-specific extraction
        └── extractor.py                # Field extraction from raw text
        └── structure.py                # Document structure analysis
        └── warnings.py                 # ATS warning generation
              └── output.py             # Terminal, JSON, or raw output
```

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Click-based entry point, argument handling |
| `parser_pdf.py` | PDF text and metadata extraction |
| `parser_docx.py` | DOCX text, styles, and structure extraction |
| `extractor.py` | Regex-based field extraction from raw text |
| `structure.py` | Document structure analysis and feedback |
| `warnings.py` | ATS warning generation logic |
| `models.py` | Shared dataclass models |
| `output.py` | Rich terminal formatting and JSON serialization |

## Requirements

- Python >= 3.10
- [pdfplumber](https://github.com/jsvine/pdfplumber) >= 0.10
- [python-docx](https://python-docx.readthedocs.io/) >= 1.0
- [click](https://click.palletsprojects.com/) >= 8.0
- [rich](https://rich.readthedocs.io/) >= 13.0

## License

MIT License. See `LICENSE` for details.
