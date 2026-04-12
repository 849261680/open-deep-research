from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.research_task import Citation
from backend.app.models.research_task import ResearchSection
from backend.app.models.research_task import ResearchTask
from backend.app.models.research_task import ResearchTaskStatus
from backend.app.core.orchestrator import ResearchOrchestrator
from backend.app.services.verifier_service import VerifierService


client = TestClient(app)


def test_non_stream_research_returns_final_payload(monkeypatch) -> None:
    async def fake_conduct_research(query: str):
        yield {"type": "planning", "message": "planning", "data": None}
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-1",
                "query": query,
                "status": "completed",
                "plan": [],
                "sections": [],
                "results": [],
                "report": "# report",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        }

    monkeypatch.setattr(
        "backend.app.api.research.langchain_research_agent.conduct_research",
        fake_conduct_research,
    )

    response = client.post(
        "/api/research",
        json={"query": "test query", "stream": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["data"]["report"] == "# report"
    assert payload["data"]["query"] == "test query"


def test_stream_research_emits_error_event_on_failure(monkeypatch) -> None:
    async def failing_conduct_research(query: str):
        raise RuntimeError("boom")
        yield {"type": "report_complete", "message": "unused", "data": None}

    monkeypatch.setattr(
        "backend.app.api.research.langchain_research_agent.conduct_research",
        failing_conduct_research,
    )

    with client.stream(
        "POST",
        "/api/research",
        json={"query": "test query", "stream": True},
    ) as response:
        body = "".join(
            chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            for chunk in response.iter_text()
        )

    assert response.status_code == 200
    assert '"type": "error"' in body
    assert "boom" in body


def test_verifier_falls_back_when_llm_json_is_invalid(monkeypatch) -> None:
    service = VerifierService()

    async def bad_llm(self, prompt: str, stop=None, run_manager=None, **kwargs):  # noqa: ANN001
        return "not json"

    monkeypatch.setattr(service.llm.__class__, "_acall", bad_llm)

    result = client.app is not None  # keep import usage minimal for lint
    assert result is True

    import asyncio

    verification = asyncio.run(
        service.verify_section(
            analysis="some analysis",
            citations=[Citation(title="a", link="https://a", source="web")],
            compressed_evidence="evidence " * 20,
        )
    )

    assert verification["method"] == "deterministic_fallback"
    assert verification["passed"] is False


def test_resume_research_returns_existing_completed_payload(monkeypatch) -> None:
    async def fake_resume(task_id: str):
        yield {
            "type": "report_complete",
            "message": "研究已完成",
            "data": {
                "id": task_id,
                "query": "restored query",
                "status": "completed",
                "plan": [],
                "sections": [],
                "results": [],
                "report": "# restored",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        }

    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.resume_task",
        fake_resume,
    )

    response = client.post(
        "/api/research/resume",
        json={"task_id": "task-123", "stream": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["report"] == "# restored"
    assert payload["data"]["id"] == "task-123"


def test_orchestrator_retries_failed_section(monkeypatch, tmp_path) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()

    task = ResearchTask(
        id="task-1",
        query="retry query",
        status=ResearchTaskStatus.RESEARCHING,
        sections=[
            ResearchSection(
                id="section-1",
                step=1,
                title="Step 1",
                description="desc",
                search_queries=["retry query"],
            )
        ],
    )

    call_count = {"count": 0}

    async def fake_execute(step, query):  # noqa: ANN001
        call_count["count"] += 1
        yield {
            "type": "step_complete",
            "message": "failed" if call_count["count"] == 1 else "completed",
            "data": {
                "step": 1,
                "title": "Step 1",
                "status": "failed" if call_count["count"] == 1 else "completed",
                "analysis": "analysis text",
                "search_results": {},
                "search_sources": [],
            },
        }

    async def fake_verify(**kwargs):  # noqa: ANN003
        return {"passed": True, "issues": [], "score": 1.0, "method": "test"}

    monkeypatch.setattr(
        orchestrator.executor,
        "execute_research_step_with_updates",
        fake_execute,
    )
    monkeypatch.setattr(
        "backend.app.core.orchestrator.verifier_service.verify_section",
        fake_verify,
    )

    events = []

    async def collect() -> None:
        async for event in orchestrator._run_section(task, task.sections[0]):
            events.append(event)

    import asyncio

    asyncio.run(collect())

    assert any(event["type"] == "step_retry" for event in events)
    assert any(
        event["type"] == "step_complete"
        and event["data"]["status"] == "completed"
        for event in events
    )
