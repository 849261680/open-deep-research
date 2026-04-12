from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{(Path('backend/data/test_app.db').resolve())}",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from backend.app.core.deps import get_current_user
from backend.app.main import app
from backend.app.models.research_task import Citation
from backend.app.models.research_task import ResearchSection
from backend.app.models.research_task import ResearchTask
from backend.app.models.research_task import ResearchTaskStatus
from backend.app.models.user import User
from backend.app.core.orchestrator import ResearchOrchestrator
from backend.app.services.verifier_service import VerifierService


async def override_current_user() -> User:
    return User(id=1, email="test@example.com", hashed_password="hashed")


AUTH_HEADERS = {"Authorization": "Bearer test-token"}


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)


def test_non_stream_research_returns_final_payload(monkeypatch, client: TestClient) -> None:
    async def fake_conduct_research(query: str, user_id: int | None = None):
        yield {"type": "planning", "message": "planning", "data": None}
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-1",
                "user_id": user_id,
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
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["data"]["report"] == "# report"
    assert payload["data"]["query"] == "test query"


def test_non_stream_research_allows_anonymous_access(monkeypatch) -> None:
    async def fake_conduct_research(query: str, user_id: int | None = None):
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-anon",
                "user_id": user_id,
                "query": query,
                "status": "completed",
                "plan": [],
                "sections": [],
                "results": [],
                "report": "# anonymous",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        }

    monkeypatch.setattr(
        "backend.app.api.research.langchain_research_agent.conduct_research",
        fake_conduct_research,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/research",
            json={"query": "anonymous query", "stream": False},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["query"] == "anonymous query"
    assert payload["data"]["user_id"] is None


def test_stream_research_emits_error_event_on_failure(
    monkeypatch, client: TestClient
) -> None:
    async def failing_conduct_research(query: str, user_id: int | None = None):
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
        headers=AUTH_HEADERS,
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

    result = app is not None  # keep import usage minimal for lint
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


def test_resume_research_returns_existing_completed_payload(
    monkeypatch, client: TestClient
) -> None:
    async def fake_resume(task_id: str, user_id: int | None = None):
        yield {
            "type": "report_complete",
            "message": "研究已完成",
            "data": {
                "id": task_id,
                "user_id": user_id,
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
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["report"] == "# restored"
    assert payload["data"]["id"] == "task-123"


def test_get_research_task_requires_authenticated_owner(client: TestClient) -> None:
    repository = ResearchOrchestrator().repository
    task = ResearchTask(
        id="owned-task",
        user_id=999,
        query="secret query",
        status=ResearchTaskStatus.COMPLETED,
    )
    repository.save_task(task)

    response = client.get("/api/research/owned-task", headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.json()["detail"] == "研究任务不存在"


def test_anonymous_history_only_returns_anonymous_tasks(tmp_path) -> None:
    repository = ResearchOrchestrator().repository
    repository.db_path = str(tmp_path / "research.db")
    repository._ensure_db()

    repository.save_task(
        ResearchTask(
            id="anon-task",
            user_id=None,
            query="public query",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    repository.save_task(
        ResearchTask(
            id="user-task",
            user_id=42,
            query="private query",
            status=ResearchTaskStatus.COMPLETED,
        )
    )

    history = repository.load_tasks(user_id=None)
    anonymous_task_ids = [item["id"] for item in history]

    assert anonymous_task_ids == ["anon-task"]


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


def test_resume_only_executes_pending_sections(monkeypatch, tmp_path) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()

    completed_section = ResearchSection(
        id="section-done",
        step=1,
        title="Done",
        description="done",
        status="completed",
        analysis="existing analysis",
    )
    pending_section = ResearchSection(
        id="section-pending",
        step=2,
        title="Pending",
        description="pending",
        search_queries=["pending"],
    )
    task = ResearchTask(
        id="task-resume",
        user_id=1,
        query="resume query",
        status=ResearchTaskStatus.RESEARCHING,
        sections=[completed_section, pending_section],
    )
    orchestrator.repository.save_task(task)

    executed_sections: list[str] = []

    async def fake_execute(step, query):  # noqa: ANN001
        executed_sections.append(step["id"])
        yield {
            "type": "step_complete",
            "message": "completed",
            "data": {
                "step": step["step"],
                "title": step["title"],
                "status": "completed",
                "analysis": f"analysis for {step['id']}",
                "search_results": {},
                "search_sources": [],
            },
        }

    async def fake_verify(**kwargs):  # noqa: ANN003
        return {"passed": True, "issues": [], "score": 1.0, "method": "test"}

    async def fake_report(results, query):  # noqa: ANN001
        return f"report for {query} with {len(results)} sections"

    monkeypatch.setattr(
        orchestrator.executor,
        "execute_research_step_with_updates",
        fake_execute,
    )
    monkeypatch.setattr(
        "backend.app.core.orchestrator.verifier_service.verify_section",
        fake_verify,
    )
    monkeypatch.setattr(
        orchestrator.report_generator,
        "generate_final_report",
        fake_report,
    )

    events = []

    async def collect() -> None:
        async for event in orchestrator.resume_task("task-resume", user_id=1):
            events.append(event)

    import asyncio

    asyncio.run(collect())

    assert executed_sections == ["section-pending"]
    report_complete = next(
        event for event in events if event["type"] == "report_complete"
    )
    assert len(report_complete["data"]["results"]) == 2
