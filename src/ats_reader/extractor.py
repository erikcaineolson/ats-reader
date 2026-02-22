"""Format-agnostic field extraction from plain text.

Detects sections, then extracts contact info, experience, education, and skills.
"""

from __future__ import annotations

import re

from ats_reader.models import (
    ContactInfo,
    Education,
    ParsedResume,
    WorkExperience,
)


# ---------------------------------------------------------------------------
# Section heading patterns
# ---------------------------------------------------------------------------

SECTION_KEYWORDS: dict[str, list[str]] = {
    "experience": [
        "experience", "work experience", "professional experience",
        "employment", "employment history", "work history",
    ],
    "education": [
        "education", "academic background", "academic history",
        "degrees", "qualifications",
    ],
    "skills": [
        "skills", "technical skills", "core competencies",
        "competencies", "proficiencies", "areas of expertise",
        "technologies", "tools",
    ],
    "summary": [
        "summary", "professional summary", "profile",
        "objective", "career objective", "about",
    ],
    "certifications": [
        "certifications", "certificates", "licenses",
        "professional development", "credentials",
    ],
    "projects": [
        "projects", "key projects", "selected projects",
    ],
    "volunteer": [
        "volunteer", "volunteering", "community involvement",
    ],
    "publications": [
        "publications", "papers", "research",
    ],
    "awards": [
        "awards", "honors", "achievements",
    ],
}


def extract_fields(raw_text: str) -> ParsedResume:
    """Parse structured fields from raw resume text."""
    lines = raw_text.splitlines()
    sections = _detect_sections(lines)
    contact = _extract_contact(raw_text, lines)
    summary = _extract_summary(sections)
    experience = _extract_experience(sections)
    education = _extract_education(sections)
    skills = _extract_skills(sections)
    certifications = _extract_certifications(sections)

    return ParsedResume(
        contact=contact,
        summary=summary,
        experience=experience,
        education=education,
        skills=skills,
        certifications=certifications,
        sections={k: v for k, v in sections.items()},
    )


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

def _detect_sections(lines: list[str]) -> dict[str, str]:
    """Identify sections by matching heading lines to known keywords."""
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        matched = _match_section_heading(stripped)
        if matched:
            if current_section is not None:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = matched
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    if current_section is not None:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def _match_section_heading(line: str) -> str | None:
    """Return the canonical section name if this line looks like a heading."""
    if not line or len(line) > 80:
        return None

    cleaned = re.sub(r"[:\-–—_|/\\#*]", "", line).strip().lower()

    for section_key, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if cleaned == kw:
                return section_key
            # Handle lines like "PROFESSIONAL EXPERIENCE" with extra whitespace
            if re.fullmatch(rf"\s*{re.escape(kw)}\s*", cleaned):
                return section_key

    return None


# ---------------------------------------------------------------------------
# Contact info
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?1[\s.\-]?)?"
    r"(?:\(?\d{3}\)?[\s.\-]?)"
    r"\d{3}[\s.\-]?\d{4}"
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?", re.I)
URL_RE = re.compile(r"https?://[^\s,;]+|(?:www\.)[^\s,;]+")
LOCATION_RE = re.compile(
    r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2}\b"
)


def _extract_contact(raw_text: str, lines: list[str]) -> ContactInfo:
    """Extract contact details from the resume text."""
    contact = ContactInfo()

    # Email
    m = EMAIL_RE.search(raw_text)
    if m:
        contact.email = m.group()

    # Phone
    m = PHONE_RE.search(raw_text)
    if m:
        contact.phone = m.group().strip()

    # LinkedIn
    m = LINKEDIN_RE.search(raw_text)
    if m:
        contact.linkedin = m.group().strip().rstrip("/")

    # Website (non-LinkedIn URL)
    for m in URL_RE.finditer(raw_text):
        url = m.group()
        if "linkedin.com" not in url.lower():
            contact.website = url.strip()
            break

    # Location (City, ST pattern)
    m = LOCATION_RE.search(raw_text)
    if m:
        contact.location = m.group()

    # Name: first non-empty, non-contact line (heuristic)
    contact.name = _guess_name(lines, contact)

    return contact


def _guess_name(lines: list[str], contact: ContactInfo) -> str | None:
    """Guess the candidate's name from the first meaningful line."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that are clearly contact info
        if contact.email and contact.email in stripped:
            continue
        if contact.phone and contact.phone in stripped:
            continue
        if EMAIL_RE.search(stripped) or PHONE_RE.search(stripped):
            continue
        if LINKEDIN_RE.search(stripped):
            continue
        # Skip section headings
        if _match_section_heading(stripped):
            continue
        # Likely the name if it's short-ish and has no digits
        if len(stripped) < 60 and not re.search(r"\d", stripped):
            return stripped
    return None


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

DATE_RANGE_RE = re.compile(
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\d{4}"
    r"\s*[\-–—to]+\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?"
    r"(?:\d{4}|[Pp]resent|[Cc]urrent)",
    re.I,
)

SINGLE_DATE_RE = re.compile(
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\d{4}",
    re.I,
)

BULLET_RE = re.compile(r"^[\s]*[•●○■◆▪–—\-►➢✓✔]\s*")


def _extract_experience(sections: dict[str, str]) -> list[WorkExperience]:
    """Parse work experience entries from the experience section."""
    text = sections.get("experience", "")
    if not text:
        return []

    entries: list[WorkExperience] = []
    current: WorkExperience | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        date_match = DATE_RANGE_RE.search(stripped)
        is_bullet = bool(BULLET_RE.match(stripped))

        if date_match and not is_bullet:
            # New entry
            if current:
                entries.append(current)
            current = WorkExperience(dates=date_match.group().strip())
            remaining = DATE_RANGE_RE.sub("", stripped).strip().strip("|,;–—-").strip()
            parts = re.split(r"\s{2,}|\s*[|,;]\s*|\s+at\s+|\s+@\s+", remaining, maxsplit=1)
            if parts:
                current.title = parts[0].strip() or None
            if len(parts) > 1:
                current.company = parts[1].strip() or None
        elif is_bullet and current:
            desc = BULLET_RE.sub("", stripped).strip()
            if desc:
                current.descriptions.append(desc)
        elif current and not current.title:
            current.title = stripped
        elif current and not current.company:
            current.company = stripped
        elif current:
            # Continuation text — treat as description
            current.descriptions.append(stripped)

    if current:
        entries.append(current)

    return entries


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

DEGREE_RE = re.compile(
    r"\b(?:B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?|Ph\.?D\.?|"
    r"Associate|Bachelor|Master|Doctor|Diploma|Certificate)\b",
    re.I,
)


def _extract_education(sections: dict[str, str]) -> list[Education]:
    """Parse education entries from the education section."""
    text = sections.get("education", "")
    if not text:
        return []

    entries: list[Education] = []
    current: Education | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        has_degree = bool(DEGREE_RE.search(stripped))
        date_match = SINGLE_DATE_RE.search(stripped)

        if has_degree or (date_match and len(stripped) < 100 and current is None):
            if current:
                entries.append(current)
            current = Education()
            if has_degree:
                current.degree = stripped
            if date_match:
                current.dates = date_match.group().strip()
        elif current and not current.school and not BULLET_RE.match(stripped):
            current.school = stripped
        elif current:
            detail = BULLET_RE.sub("", stripped).strip()
            if detail:
                current.details.append(detail)

    if current:
        entries.append(current)

    return entries


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

SKILL_SPLIT_RE = re.compile(r"[,;|•●○■◆▪►➢✓✔]\s*|\n")


def _extract_skills(sections: dict[str, str]) -> list[str]:
    """Parse skills list from the skills section."""
    text = sections.get("skills", "")
    if not text:
        return []

    items = SKILL_SPLIT_RE.split(text)
    skills = []
    for item in items:
        cleaned = item.strip().strip("-–—").strip()
        if cleaned and len(cleaned) < 80:
            skills.append(cleaned)
    return skills


# ---------------------------------------------------------------------------
# Summary / Certifications
# ---------------------------------------------------------------------------

def _extract_summary(sections: dict[str, str]) -> str | None:
    text = sections.get("summary", "")
    return text.strip() or None


def _extract_certifications(sections: dict[str, str]) -> list[str]:
    text = sections.get("certifications", "")
    if not text:
        return []
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            items.append(BULLET_RE.sub("", stripped).strip())
    return [i for i in items if i]
