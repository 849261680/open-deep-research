"""
纯逻辑单元测试 — 不依赖任何外部 API / 网络 / 数据库。
覆盖范围：
  - ResearchOrchestrator._event
  - VerifierService._deterministic_verify / _parse_json
  - ContentExtractionService._extract_content_sync (HTML 清洗，本地字符串)
  - DeepSeekService._truncate_prompt / _build_payload
  - CostTracker / estimate_tokens
  - SourceCurator 可信度评分
"""
from __future__ import annotations

import json
import os

# ── 避免导入时触发真实 DB / env 初始化 ──────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_logic.db")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

# ── 被测模块 ─────────────────────────────────────────────────────────────────
from backend.app.core.orchestrator import ResearchOrchestrator
from backend.app.models.research_task import Citation
from backend.app.research.source_curator import SourceCurator, _score_source
from backend.app.research.models import ResearchSource
from backend.app.services.content_extraction_service import ContentExtractionService
from backend.app.services.deepseek_service import DeepSeekService
from backend.app.services.verifier_service import VerifierService
from backend.app.research.cost_tracker import CostTracker
from backend.app.research.cost_tracker import estimate_tokens


# ═══════════════════════════════════════════════════════════════════
# ResearchOrchestrator
# ═══════════════════════════════════════════════════════════════════

class TestEventHelper:
    orch = ResearchOrchestrator()

    def test_event_contains_all_keys(self):
        event = self.orch._event("planning", "开始规划", {"key": "value"})
        assert event == {"type": "planning", "message": "开始规划", "data": {"key": "value"}}

    def test_event_data_can_be_none(self):
        event = self.orch._event("done", "完成", None)
        assert event["data"] is None


# ═══════════════════════════════════════════════════════════════════
# SourceCurator — 可信度评分
# ═══════════════════════════════════════════════════════════════════

class TestScoreSource:
    def test_gov_domain_gets_high_score(self):
        source = ResearchSource(title="T", link="https://data.gov.cn/report", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score >= 0.7

    def test_academic_domain_gets_high_score(self):
        source = ResearchSource(title="T", link="https://arxiv.org/abs/1234", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score >= 0.7

    def test_social_media_gets_low_score(self):
        source = ResearchSource(title="T", link="https://reddit.com/r/test", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score < 0.5

    def test_empty_link_returns_zero(self):
        source = ResearchSource(title="T", link="", snippet="s")
        assert _score_source(source) == 0.0

    def test_authoritative_media_gets_bonus(self):
        source = ResearchSource(title="T", link="https://www.reuters.com/article/123", snippet="s" * 60, extracted_content="c" * 300)
        score = _score_source(source)
        assert score >= 0.7

    def test_no_content_slightly_lower(self):
        source_with = ResearchSource(title="T", link="https://example.com/a", snippet="s" * 60, extracted_content="c" * 300)
        source_without = ResearchSource(title="T", link="https://example.com/b", snippet="short", extracted_content="")
        assert _score_source(source_with) > _score_source(source_without)


class TestSourceCurator:
    curator = SourceCurator()

    def test_deduplicates_by_link(self):
        sources = [
            ResearchSource(title="A", link="https://a.com", snippet="content"),
            ResearchSource(title="A2", link="https://a.com", snippet="other"),
        ]
        result = self.curator.curate(sources)
        assert len(result) == 1

    def test_filters_empty_link(self):
        sources = [
            ResearchSource(title="A", link="", snippet="content"),
        ]
        result = self.curator.curate(sources)
        assert len(result) == 0

    def test_respects_max_sources(self):
        sources = [
            ResearchSource(title=f"T{i}", link=f"https://{i}.com", snippet="s" * 60, extracted_content="c" * 300)
            for i in range(20)
        ]
        result = self.curator.curate(sources, max_sources=5)
        assert len(result) == 5

    def test_sorts_by_credibility(self):
        sources = [
            ResearchSource(title="Reddit", link="https://reddit.com/r/test", snippet="s" * 60, extracted_content="c" * 300),
            ResearchSource(title="Gov", link="https://stats.gov.cn/data", snippet="s" * 60, extracted_content="c" * 300),
            ResearchSource(title="Random", link="https://random-blog.xyz/post", snippet="s" * 60, extracted_content="c" * 300),
        ]
        result = self.curator.curate(sources)
        # Gov should be first
        assert "gov.cn" in result[0].link


# ═══════════════════════════════════════════════════════════════════
# VerifierService
# ═══════════════════════════════════════════════════════════════════

class TestDeterministicVerify:
    svc = VerifierService()

    def _verify(self, analysis="ok", citations=None, evidence="ev " * 30):
        if citations is None:
            citations = [
                Citation(title="A", link="https://a.com", source="web"),
                Citation(title="B", link="https://b.com", source="web"),
            ]
        return self.svc._deterministic_verify(
            analysis=analysis, citations=citations, compressed_evidence=evidence
        )

    def test_passes_when_all_conditions_met(self):
        result = self._verify()
        assert result["passed"] is True
        assert result["issues"] == []
        assert result["score"] == 1.0
        assert result["method"] == "deterministic_fallback"

    def test_fails_on_empty_analysis(self):
        result = self._verify(analysis="")
        assert result["passed"] is False
        assert any("分析" in issue for issue in result["issues"])

    def test_fails_on_fewer_than_two_citations(self):
        result = self._verify(citations=[Citation(title="A", link="https://a.com", source="web")])
        assert result["passed"] is False
        assert any("来源" in issue for issue in result["issues"])

    def test_fails_on_short_evidence(self):
        result = self._verify(evidence="short")
        assert result["passed"] is False
        assert any("证据" in issue for issue in result["issues"])

    def test_score_decreases_with_more_issues(self):
        r_zero = self._verify()
        r_one  = self._verify(analysis="")
        r_two  = self._verify(analysis="", citations=[])
        assert r_zero["score"] > r_one["score"] > r_two["score"]


class TestParseJson:
    svc = VerifierService()

    def test_parses_plain_json(self):
        raw = '{"passed": true, "score": 0.9}'
        result = self.svc._parse_json(raw)
        assert result["passed"] is True

    def test_parses_fenced_json(self):
        raw = "```json\n{\"passed\": false}\n```"
        result = self.svc._parse_json(raw)
        assert result["passed"] is False

    def test_returns_none_on_invalid_json(self):
        assert self.svc._parse_json("not json") is None

    def test_returns_none_when_root_is_list(self):
        assert self.svc._parse_json("[1, 2, 3]") is None


# ═══════════════════════════════════════════════════════════════════
# ContentExtractionService — HTML 清洗（无网络）
# ═══════════════════════════════════════════════════════════════════

class TestContentExtraction:
    svc = ContentExtractionService()

    def _mock_response(self, monkeypatch, html: str, content_type: str = "text/html"):
        import requests

        class FakeResponse:
            status_code = 200
            text = html
            headers = {"Content-Type": content_type}

            def raise_for_status(self):
                pass

        monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())

    def test_strips_script_tags(self, monkeypatch):
        html = "<html><body>Hello<script>alert(1)</script> World</body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "alert" not in result
        assert "Hello" in result

    def test_strips_style_tags(self, monkeypatch):
        html = "<html><body>Text<style>.foo{color:red}</style></body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "color" not in result

    def test_strips_html_tags(self, monkeypatch):
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "<h1>" not in result
        assert "Title" in result
        assert "Content" in result

    def test_decodes_html_entities(self, monkeypatch):
        html = "<html><body>&lt;b&gt;bold&lt;/b&gt;</body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert "<b>" in result

    def test_truncates_to_3000_chars(self, monkeypatch):
        html = "<html><body>" + "x" * 5000 + "</body></html>"
        self._mock_response(monkeypatch, html)
        result = self.svc._extract_content_sync("https://example.com")
        assert len(result) <= 3000

    def test_non_html_content_returned_as_text(self, monkeypatch):
        self._mock_response(monkeypatch, "plain text content", content_type="text/plain")
        result = self.svc._extract_content_sync("https://example.com")
        assert result == "plain text content"

    def test_request_exception_returns_empty_string(self, monkeypatch):
        import requests

        monkeypatch.setattr(requests, "get", lambda *a, **kw: (_ for _ in ()).throw(
            requests.exceptions.ConnectionError("fail")
        ))
        result = self.svc._extract_content_sync("https://example.com")
        assert result == ""


# ═══════════════════════════════════════════════════════════════════
# DeepSeekService
# ═══════════════════════════════════════════════════════════════════

class TestTruncatePrompt:
    svc = DeepSeekService()

    def test_short_prompt_is_unchanged(self):
        text = "hello"
        assert self.svc._truncate_prompt(text) == text

    def test_research_context_sized_prompt_is_unchanged(self):
        text = "x" * 12_000
        assert self.svc._truncate_prompt(text) == text

    def test_configured_prompt_limit_truncates(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_PROMPT_CHARS", "3000")
        svc = DeepSeekService()
        text = "x" * 5000
        result = svc._truncate_prompt(text)
        assert len(result) <= 3100  # 3000 + suffix
        assert "请基于以上内容生成简洁摘要" in result

    def test_truncation_can_be_disabled(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_PROMPT_CHARS", "0")
        svc = DeepSeekService()
        text = "x" * 100_000
        assert svc._truncate_prompt(text) == text


class TestBuildPayload:
    svc = DeepSeekService()

    def test_payload_has_required_keys(self):
        payload = self.svc._build_payload("hello", max_tokens=500, stream=False)
        assert payload["model"] == "deepseek-chat"
        assert payload["stream"] is False
        assert payload["messages"][0]["content"] == "hello"

    def test_max_tokens_is_capped_at_default_limit(self):
        payload = self.svc._build_payload("x", max_tokens=9999, stream=False)
        assert payload["max_tokens"] == 4000

    def test_max_tokens_cap_can_be_configured(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_OUTPUT_TOKENS", "1200")
        svc = DeepSeekService()
        payload = svc._build_payload("x", max_tokens=9999, stream=False)
        assert payload["max_tokens"] == 1200

    def test_max_tokens_defaults_to_configured_limit(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MAX_OUTPUT_TOKENS", "1200")
        svc = DeepSeekService()
        payload = svc._build_payload("x", max_tokens=None, stream=False)
        assert payload["max_tokens"] == 1200

    def test_model_and_temperature_default_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        monkeypatch.setenv("DEEPSEEK_TEMPERATURE", "0.2")
        svc = DeepSeekService()
        payload = svc._build_payload("hello", max_tokens=500, stream=False)
        assert payload["model"] == "deepseek-reasoner"
        assert payload["temperature"] == 0.2

    def test_model_and_temperature_can_be_overridden_per_call(self):
        payload = self.svc._build_payload(
            "hello",
            max_tokens=500,
            stream=False,
            model="custom-model",
            temperature=0.1,
        )
        assert payload["model"] == "custom-model"
        assert payload["temperature"] == 0.1

    def test_stream_flag_is_forwarded(self):
        payload = self.svc._build_payload("x", max_tokens=100, stream=True)
        assert payload["stream"] is True


# ═══════════════════════════════════════════════════════════════════
# CostTracker
# ═══════════════════════════════════════════════════════════════════

class TestCostTracker:
    def test_estimates_tokens_from_characters(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("a" * 40) == 10

    def test_tracks_llm_call_with_configured_rates(self):
        tracker = CostTracker(
            input_cost_per_1m_tokens=1.0,
            output_cost_per_1m_tokens=2.0,
        )
        tracker.track_llm_call(
            step="query_planning",
            prompt="a" * 400,
            response="b" * 200,
        )
        summary = tracker.summary()
        assert summary["pricing_source"] == "defaults_or_env"
        assert summary["total_input_tokens"] == 100
        assert summary["total_output_tokens"] == 50
        assert summary["estimated_cost_usd"] == 0.0002
        assert summary["calls"][0]["step"] == "query_planning"

    def test_model_defaults_to_deepseek_config(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        tracker = CostTracker()
        assert tracker.summary()["model"] == "deepseek-reasoner"
