from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field

from ..models.research_task import Citation


class ResearchQuestion(BaseModel):
    id: str
    step: int
    question: str
    rationale: str = ""
    search_queries: list[str] = Field(default_factory=list)


class ResearchSource(BaseModel):
    title: str
    link: str
    source: str = "web"
    query: str = ""
    snippet: str = ""
    extracted_content: str = ""
    summary: str = ""


class QuestionResearchResult(BaseModel):
    question: ResearchQuestion
    status: str = "completed"
    sources: list[ResearchSource] = Field(default_factory=list)
    findings: str = ""


class ResearchContext(BaseModel):
    query: str
    questions: list[ResearchQuestion] = Field(default_factory=list)
    results: list[QuestionResearchResult] = Field(default_factory=list)


class SubQueryContext(BaseModel):
    step: int
    query: str
    sources: list[ResearchSource] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    compressed_evidence: str = ""
    verification: dict[str, object] = Field(default_factory=dict)
    context: str = ""
