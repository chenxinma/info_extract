from pydantic import BaseModel, Field

class ExtractResult(BaseModel):
    document: str
    data: list[dict[str, str]] = Field(default_factory=list)