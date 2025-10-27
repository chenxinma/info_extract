from typing import TypeAlias

from pydantic import BaseModel

ExtractRows: TypeAlias = list[dict[str, str]]

class ExtractResult(BaseModel):
    document: str
    data: ExtractRows
