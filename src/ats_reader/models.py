"""Data models for ATS Reader output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ContactInfo:
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    website: str | None = None
    location: str | None = None


@dataclass
class WorkExperience:
    title: str | None = None
    company: str | None = None
    dates: str | None = None
    descriptions: list[str] = field(default_factory=list)


@dataclass
class Education:
    degree: str | None = None
    school: str | None = None
    dates: str | None = None
    details: list[str] = field(default_factory=list)


@dataclass
class ParsedResume:
    contact: ContactInfo = field(default_factory=ContactInfo)
    summary: str | None = None
    experience: list[WorkExperience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractionMetadata:
    file_type: str = ""
    page_count: int = 0
    has_tables: bool = False
    has_images: bool = False
    has_columns: bool = False
    has_headers_footers: bool = False
    has_text_boxes: bool = False
    is_tagged_pdf: bool | None = None
    fonts_used: list[str] = field(default_factory=list)
    header_footer_text: list[str] = field(default_factory=list)
    pdf_producer: str | None = None
    pdf_creator: str | None = None


@dataclass
class ATSWarning:
    severity: Severity
    message: str
    detail: str | None = None
    fix: str | None = None


@dataclass
class StructureFeedback:
    severity: Severity
    element: str
    issue: str
    suggestion: str


@dataclass
class ATSResult:
    raw_text: str
    parsed: ParsedResume
    metadata: ExtractionMetadata
    warnings: list[ATSWarning] = field(default_factory=list)
    structure_feedback: list[StructureFeedback] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire result to a JSON-compatible dict."""
        return _to_dict(self)


def _to_dict(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(v) for k, v in obj.__dict__.items()}
    return obj
