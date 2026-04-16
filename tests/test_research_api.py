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
from backend.app.models.research_task import ResearchTask
from backend.app.models.research_task import ResearchTaskStatus
from backend.app.models.user import User
from backend.app.core.orchestrator import ResearchOrchestrator
from backend.app.research.agent import ResearchAgent
from backend.app.research.models import ResearchSource
from backend.app.research.models import SubQueryContext
from backend.app.services.research_repository import ResearchRepository
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
    async def fake_conduct_research(
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ):
        yield {"type": "planning", "message": "planning", "data": None}
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-1",
                "user_id": user_id,
                "guest_id": guest_id,
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
        "backend.app.api.research.research_orchestrator.run",
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
    async def fake_conduct_research(
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ):
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-anon",
                "user_id": user_id,
                "guest_id": guest_id,
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
        "backend.app.api.research.research_orchestrator.run",
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
    async def failing_conduct_research(
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ):
        raise RuntimeError("boom")
        yield {"type": "report_complete", "message": "unused", "data": None}

    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.run",
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
    assert "研究过程中发生错误，请稍后重试" in body
    assert "boom" not in body


def test_stream_research_can_include_error_detail_when_enabled(
    monkeypatch, client: TestClient
) -> None:
    async def failing_conduct_research(
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ):
        raise RuntimeError("boom")
        yield {"type": "report_complete", "message": "unused", "data": None}

    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.run",
        failing_conduct_research,
    )
    monkeypatch.setenv("RESEARCH_STREAM_INCLUDE_ERROR_DETAIL", "true")

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
    assert '"detail": "boom"' in body


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
    async def fake_resume(
        task_id: str,
        user_id: int | None = None,
        guest_id: str | None = None,
    ):
        yield {
            "type": "report_complete",
            "message": "研究已完成",
            "data": {
                "id": task_id,
                "user_id": user_id,
                "guest_id": guest_id,
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


def test_anonymous_history_only_returns_guest_scoped_tasks(tmp_path) -> None:
    repository = ResearchRepository(str(tmp_path / "research.db"))
    repository.save_task(
        ResearchTask(
            id="anon-task-a",
            user_id=None,
            guest_id="guestscope_a",
            query="public query a",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    repository.save_task(
        ResearchTask(
            id="anon-task-b",
            user_id=None,
            guest_id="guestscope_b",
            query="public query b",
            status=ResearchTaskStatus.COMPLETED,
        )
    )

    history = repository.load_tasks(guest_id="guestscope_a")
    anonymous_task_ids = [item["id"] for item in history]

    assert anonymous_task_ids == ["anon-task-a"]


def test_anonymous_history_endpoint_is_scoped_by_guest_id(monkeypatch, tmp_path) -> None:
    repository = ResearchRepository(str(tmp_path / "research.db"))
    repository.save_task(
        ResearchTask(
            id="guest-task-a",
            user_id=None,
            guest_id="guestscope_a",
            query="guest a",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    repository.save_task(
        ResearchTask(
            id="guest-task-b",
            user_id=None,
            guest_id="guestscope_b",
            query="guest b",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.repository",
        repository,
    )

    with TestClient(app) as anonymous_client:
        response = anonymous_client.get(
            "/api/research/history",
            headers={"X-Guest-Id": "guestscope_a"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["history"]] == ["guest-task-a"]


def test_clear_research_history_only_deletes_current_user_tasks(
    client: TestClient,
    monkeypatch,
    tmp_path,
) -> None:
    repository = ResearchOrchestrator().repository
    repository.db_path = str(tmp_path / "research.db")
    repository._ensure_db()
    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.repository",
        repository,
    )

    repository.save_task(
        ResearchTask(
            id="user-task-to-clear",
            user_id=1,
            query="owned query",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    repository.save_task(
        ResearchTask(
            id="other-user-task",
            user_id=2,
            query="other query",
            status=ResearchTaskStatus.COMPLETED,
        )
    )
    repository.save_task(
        ResearchTask(
            id="anonymous-task",
            user_id=None,
            guest_id="guestscope_a",
            query="anonymous query",
            status=ResearchTaskStatus.COMPLETED,
        )
    )

    response = client.delete("/api/research/history", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()["cleared"] == 1
    assert repository.load_task("user-task-to-clear", user_id=1) is None
    assert repository.load_task("other-user-task", user_id=2) is not None
    assert repository.load_task("anonymous-task", guest_id="guestscope_a") is not None


def test_resume_reruns_incomplete_task_with_research_agent(monkeypatch, tmp_path) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()

    task = ResearchTask(
        id="task-resume",
        user_id=1,
        query="resume query",
        status=ResearchTaskStatus.RESEARCHING,
    )
    orchestrator.repository.save_task(task)

    async def fake_agent_run(self, task):  # noqa: ANN001
        task.status = ResearchTaskStatus.COMPLETED
        task.final_report = "# rerun"
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": task.id,
                "query": task.query,
                "status": "completed",
                "report": task.final_report,
            },
        }

    monkeypatch.setattr("backend.app.core.orchestrator.ResearchAgent.run", fake_agent_run)

    events = []

    async def collect() -> None:
        async for event in orchestrator.resume_task("task-resume", user_id=1):
            events.append(event)

    import asyncio

    asyncio.run(collect())

    assert events[0]["type"] == "resume"
    report_complete = next(
        event for event in events if event["type"] == "report_complete"
    )
    assert report_complete["data"]["report"] == "# rerun"


def test_resume_task_clears_old_evidence_before_rerun(tmp_path) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()

    task = ResearchTask(
        id="task-resume-evidence",
        user_id=1,
        query="resume query",
        status=ResearchTaskStatus.RESEARCHING,
    )
    orchestrator.repository.save_task(task)
    from backend.app.models.research_task import EvidenceItem

    orchestrator.repository.save_evidence(
        task.id,
        EvidenceItem(
            id="evidence-old",
            section_id="subquery-1",
            query=task.query,
            source_type="web",
            title="Old Evidence",
            link="https://example.com/old",
            snippet="old",
        ),
    )

    async def fake_agent_run(self, task):  # noqa: ANN001
        task.status = ResearchTaskStatus.COMPLETED
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": task.id,
                "query": task.query,
                "status": "completed",
                "report": "# rerun",
            },
        }

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("backend.app.core.orchestrator.ResearchAgent.run", fake_agent_run)

    events = []

    async def collect() -> None:
        async for event in orchestrator.resume_task(task.id, user_id=1):
            events.append(event)

    import asyncio
    import sqlite3

    asyncio.run(collect())
    monkeypatch.undo()

    with sqlite3.connect(orchestrator.repository.db_path) as conn:
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM evidence_items WHERE task_id = ?",
            (task.id,),
        ).fetchone()[0]

    assert events[0]["type"] == "resume"
    assert evidence_count == 0


def test_orchestrator_run_emits_task_id_before_research(monkeypatch, tmp_path) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()

    async def fake_agent_run(self, task):  # noqa: ANN001
        task.status = ResearchTaskStatus.COMPLETED
        task.final_report = "# report"
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": task.id,
                "query": task.query,
                "status": task.status.value,
                "report": task.final_report,
            },
        }

    monkeypatch.setattr("backend.app.core.orchestrator.ResearchAgent.run", fake_agent_run)

    events = []

    async def collect() -> None:
        async for event in orchestrator.run("new query", user_id=1):
            events.append(event)

    import asyncio

    asyncio.run(collect())

    assert events[0]["type"] == "planning"
    assert events[0]["data"]["task_id"] == events[1]["data"]["id"]
    assert events[0]["data"]["query"] == "new query"
    assert orchestrator.repository.load_task(events[0]["data"]["task_id"], user_id=1)


def test_orchestrator_stop_task_marks_task_failed(tmp_path) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()
    task = ResearchTask(
        id="task-stop",
        user_id=1,
        query="stop query",
        status=ResearchTaskStatus.RESEARCHING,
    )
    orchestrator.repository.save_task(task)

    stopped = orchestrator.stop_task("task-stop", user_id=1)
    saved = orchestrator.repository.load_task("task-stop", user_id=1)

    assert stopped is not None
    assert stopped["status"] == "failed"
    assert stopped["error"] == "研究已停止"
    assert saved is not None
    assert saved.status == ResearchTaskStatus.FAILED
    assert saved.error == "研究已停止"


def test_research_agent_emits_gpt_researcher_payload(monkeypatch) -> None:
    agent = ResearchAgent(query="DeepSeek enterprise", max_concurrency=1)
    task = ResearchTask(id="task-gptr", query="DeepSeek enterprise")
    context = SubQueryContext(
        step=1,
        query="DeepSeek 企业落地案例有哪些？",
        context="发现 A",
        evidence_ids=["evidence-1"],
        compressed_evidence="研究主题: DeepSeek 企业落地案例有哪些？",
        verification={
            "passed": True,
            "score": 1.0,
            "issues": [],
            "summary": "证据充分",
        },
        citations=[
            Citation(
                title="Source A",
                link="https://example.com/a",
                source="web",
                query="DeepSeek enterprise case study",
            )
        ],
        sources=[
            ResearchSource(
                title="Source A",
                link="https://example.com/a",
                source="web",
                query="DeepSeek enterprise case study",
                summary="摘要 A",
            )
        ],
    )

    async def fake_conduct_research(on_event=None):  # noqa: ANN001
        if on_event:
            await on_event(
                {
                    "type": "plan",
                    "message": "子查询规划完成",
                    "data": [context.query],
                }
            )
            await on_event(
                {
                    "type": "step_complete",
                    "message": "done",
                    "data": {"step": 1, "title": context.query},
                }
            )
        agent.research_sources = context.sources
        return [context]

    async def fake_write_report(**kwargs):  # noqa: ANN003
        agent.cost_tracker.track_llm_call(
            step="report_writing",
            prompt="prompt",
            response="response",
        )
        return "# report"

    monkeypatch.setattr(agent.conductor, "conduct_research", fake_conduct_research)
    monkeypatch.setattr(agent.writer, "write_report", fake_write_report)

    events = []

    async def collect() -> None:
        async for event in agent.run(task):
            events.append(event)

    import asyncio

    asyncio.run(collect())

    report_complete = next(
        event for event in events if event["type"] == "report_complete"
    )
    assert report_complete["data"]["architecture"] == "gpt_researcher"
    assert report_complete["data"]["report"] == "# report"
    assert report_complete["data"]["cost_summary"]["total_tokens"] > 0
    assert report_complete["data"]["results"][0]["title"] == context.query
    assert report_complete["data"]["results"][0]["verification"]["passed"] is True
    assert report_complete["data"]["results"][0]["compressed_evidence"] == context.compressed_evidence
    assert report_complete["data"]["sections"][0]["evidence_ids"] == context.evidence_ids
    assert task.cost_summary["total_tokens"] > 0
    assert task.sections[0].tool == "research_conductor"
