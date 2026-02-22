"""ATS Reader — see your resume the way an ATS does."""

__version__ = "0.1.0"

# Patch stdlib XML parsers against entity expansion attacks (billion-laughs).
# Must run before python-docx or any other library parses XML.
import defusedxml
defusedxml.defuse_stdlib()
