from __future__ import annotations

from datetime import datetime
from datetime import timezone
from enum import Enum

from pydantic import BaseModel
from pydantic import Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchTaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class Citation(BaseModel):
    title: str
    link: str
    source: str
    query: str | None = None


class EvidenceItem(BaseModel):
    id: str
    section_id: str
    query: str
    source_type: str
    title: str
    link: str
    snippet: str
    extracted_content: str = ""
    captured_at: str = Field(default_factory=utc_now)


class ResearchSection(BaseModel):
    id: str
    step: int
    title: str
    description: str
    tool: str = "comprehensive_search"
    search_queries: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    status: str = "pending"
    analysis: str = ""
    citations: list[Citation] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    compressed_evidence: str = ""
    verification: dict[str, object] = Field(default_factory=dict)
    retry_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None


class ResearchTask(BaseModel):
    id: str
    query: str
    status: ResearchTaskStatus = ResearchTaskStatus.PENDING
    sections: list[ResearchSection] = Field(default_factory=list)
    final_report: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    completed_at: str | None = None
    error: str | None = None

    def touch(self) -> None:
        self.updated_at = utc_now()
