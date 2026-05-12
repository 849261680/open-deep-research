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


class ResearchPlanItem(BaseModel):
    """Structured plan item for one research dimension."""

    step: int
    title: str
    dimension: str = ""
    rationale: str = ""
    search_queries: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    evidence_targets: list[str] = Field(default_factory=list)


class DeepResearchDecision(BaseModel):
    """Decision record for whether one researched item needs deeper follow-up."""

    should_continue: bool = False
    reason: str = ""
    evidence_gaps: list[str] = Field(default_factory=list)
    follow_up_queries: list[str] = Field(default_factory=list)
    stop_condition: str = ""


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
    depth: int = 1
    parent_query: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    compressed_evidence: str = ""
    verification: dict[str, object] = Field(default_factory=dict)
    deep_research: DeepResearchDecision = Field(default_factory=DeepResearchDecision)
    context: str = ""
