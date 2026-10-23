
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PolicyDocument(BaseModel):
    """Metadata for one CMS policy document."""

    doc_id: str
    doc_type: Literal["LCD", "billing_article"]
    title: str
    version: int = Field(gt=0)
    contractor: str
    source_url: HttpUrl
    original_effective_date: date | None = None
    revision_effective_date: date | None = None
    retrieved_at: date | None = None
    sha256: str | None = None
    related_docs: list[str] = Field(default_factory=list)


class PolicyMetadata(BaseModel):
    """Metadata for a medical procedure and its CMS documents."""

    procedure: str
    documents: list[PolicyDocument] = Field(min_length=1)
