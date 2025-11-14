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


@dataclass
class Example:
    """Represents an example for extraction in the configuration."""
    id: int
    fragment: str
