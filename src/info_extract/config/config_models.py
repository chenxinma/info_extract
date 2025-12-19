"""
Data models for configuration items in the info_extract project.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class InfoItem:
    """Represents an information item in the configuration."""
    id: int
    label: str
    describe: Optional[str]
    data_type: str
    sort_no: int
    sample_col_name: str
    profile_id: int


@dataclass
class Example:
    """Represents an example for extraction in the configuration."""
    id: int
    fragment: str
    profile_id: int


@dataclass
class ExtractionRecord:
    """Represents an extraction record for a marked text."""
    id: int
    example_id: int
    extraction_info_item_id: int
    extraction_text: str
    profile_id: int
    info_item_label: str


@dataclass
class ExtractionAttribute:
    """Represents an attribute for an extraction record."""
    id: int
    extraction_id: int
    key: str
    value: str
    profile_id: int