"""Research task configuration loaded from requests or environment."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class ResearchConfig(BaseModel):
    """Runtime options that shape one research task."""

    max_sub_queries: int = Field(default=5, ge=1, le=10)
    max_concurrency: int = Field(default=3, ge=1, le=8)
    max_read_pages_per_section: int = Field(default=8, ge=1, le=30)
    deep_research_breadth: int = Field(default=2, ge=0, le=5)
    deep_research_depth: int = Field(default=2, ge=1, le=4)
    retriever: str = "auto"
    report_type: str = "research_report"
    tone: str = "objective"
    source: str = "web"
    query_domains: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    enabled_tools: list[str] = Field(default_factory=lambda: ["python_code_execution"])

    @classmethod
    def from_env(cls) -> "ResearchConfig":
        """Create task config from RESEARCH_* environment variables."""
        data: dict[str, Any] = {}
        _set_int_from_env(data, "max_sub_queries", "RESEARCH_MAX_SUB_QUERIES")
        _set_int_from_env(data, "max_concurrency", "RESEARCH_MAX_CONCURRENCY")
        _set_int_from_env(
            data,
            "max_read_pages_per_section",
            "RESEARCH_MAX_READ_PAGES_PER_SECTION",
        )
        _set_int_from_env(data, "deep_research_breadth", "RESEARCH_DEEP_RESEARCH_BREADTH")
        _set_int_from_env(data, "deep_research_depth", "RESEARCH_DEEP_RESEARCH_DEPTH")
        _set_str_from_env(data, "retriever", "RESEARCH_RETRIEVER")
        _set_str_from_env(data, "report_type", "RESEARCH_REPORT_TYPE")
        _set_str_from_env(data, "tone", "RESEARCH_TONE")
        _set_str_from_env(data, "source", "RESEARCH_SOURCE")
        _set_list_from_env(data, "query_domains", "RESEARCH_QUERY_DOMAINS")
        _set_list_from_env(data, "source_urls", "RESEARCH_SOURCE_URLS")
        _set_list_from_env(data, "enabled_tools", "RESEARCH_ENABLED_TOOLS")
        return cls(**data)

    def tool_schemas(self) -> list[dict[str, Any]]:
        """Return schemas for tools enabled in this research task."""
        from .tools import CodeExecutionTool

        schemas_by_name = {CodeExecutionTool.name: CodeExecutionTool.schema()}
        return [
            schemas_by_name[name]
            for name in self.enabled_tools
            if name in schemas_by_name
        ]

    @field_validator("retriever")
    @classmethod
    def validate_retriever(cls, value: str) -> str:
        """Normalize and validate the search backend selector."""
        normalized = value.strip().lower()
        allowed = {"auto", "tavily", "serpapi", "duckduckgo"}
        if normalized not in allowed:
            raise ValueError("retriever 不支持")
        return normalized

    @field_validator("report_type", "tone", "source")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        """Normalize simple string labels used by prompts and routing."""
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("配置项不能为空")
        return normalized

    @field_validator("query_domains", "source_urls")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        """Trim, dedupe, and drop empty list entries."""
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = item.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)
        return normalized

    @field_validator("enabled_tools")
    @classmethod
    def validate_enabled_tools(cls, value: list[str]) -> list[str]:
        """Normalize and validate research tool names."""
        normalized: list[str] = []
        allowed = {"python_code_execution"}
        for item in value:
            tool_name = item.strip()
            if not tool_name:
                continue
            if tool_name not in allowed:
                raise ValueError("研究工具不支持")
            if tool_name not in normalized:
                normalized.append(tool_name)
        return normalized


def _set_int_from_env(data: dict[str, object], field: str, env_name: str) -> None:
    """Copy an integer env var into model data when present."""
    raw_value = os.getenv(env_name)
    if raw_value is not None:
        data[field] = int(raw_value)


def _set_str_from_env(data: dict[str, object], field: str, env_name: str) -> None:
    """Copy a string env var into model data when present."""
    raw_value = os.getenv(env_name)
    if raw_value is not None:
        data[field] = raw_value


def _set_list_from_env(data: dict[str, object], field: str, env_name: str) -> None:
    """Copy a comma-separated env var into model data when present."""
    raw_value = os.getenv(env_name)
    if raw_value is not None:
        data[field] = raw_value.split(",")
