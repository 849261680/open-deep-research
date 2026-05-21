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
from backend.app.core.deps import get_optional_current_user
from backend.app.main import app
from backend.app.models.research_task import Citation
from backend.app.models.research_task import EvidenceItem
from backend.app.models.research_task import ResearchSection
from backend.app.models.research_task import ResearchTask
from backend.app.models.research_task import ResearchTaskStatus
from backend.app.models.user import User
from backend.app.core.orchestrator import ResearchOrchestrator
from backend.app.research.agent import ResearchAgent
from backend.app.research.models import DeepResearchDecision
from backend.app.research.models import ResearchPlanItem
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
    app.dependency_overrides[get_optional_current_user] = override_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)


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


def test_research_request_passes_config_to_orchestrator(
    monkeypatch, client: TestClient
) -> None:
    captured_config = None

    async def fake_conduct_research(
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
        config=None,  # noqa: ANN001
    ):
        nonlocal captured_config
        captured_config = config
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-config",
                "user_id": user_id,
                "guest_id": guest_id,
                "query": query,
                "status": "completed",
                "plan": [],
                "sections": [],
                "results": [],
                "report": "# configured",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        }

    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.run",
        fake_conduct_research,
    )

    response = client.post(
        "/api/research",
        json={
            "query": "configured query",
            "stream": False,
            "config": {
                "max_sub_queries": 2,
                "max_concurrency": 1,
                "retriever": "duckduckgo",
                "report_type": "detailed_report",
                "tone": "analytical",
                "source": "web",
                "query_domains": ["example.com", "docs.example.com"],
                "source_urls": ["https://example.com/a"],
            },
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert captured_config is not None
    assert captured_config.max_sub_queries == 2
    assert captured_config.max_concurrency == 1
    assert captured_config.retriever == "duckduckgo"
    assert captured_config.report_type == "detailed_report"
    assert captured_config.tone == "analytical"
    assert captured_config.source == "web"
    assert captured_config.query_domains == ["example.com", "docs.example.com"]
    assert captured_config.source_urls == ["https://example.com/a"]


def test_research_plan_endpoint_returns_confirmable_plan(
    monkeypatch, client: TestClient
) -> None:
    async def fake_preview_plan(query: str, config=None):  # noqa: ANN001
        return {
            "query": query,
            "plan_items": [
                {
                    "step": 1,
                    "title": "AI 产业采用率",
                    "dimension": "数据趋势",
                    "rationale": "需要量化趋势。",
                    "search_queries": ["AI adoption survey"],
                    "expected_outcome": "获得采用率数据。",
                    "evidence_targets": ["统计数据"],
                }
            ],
            "sub_queries": ["AI 产业采用率"],
            "cost_summary": {},
        }

    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.preview_plan",
        fake_preview_plan,
    )

    response = client.post(
        "/api/research/plan",
        json={"query": "AI 产业趋势"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "planned"
    assert payload["data"]["plan_items"][0]["dimension"] == "数据趋势"


def test_research_request_passes_confirmed_plan_items(
    monkeypatch, client: TestClient
) -> None:
    captured_plan_items = None

    async def fake_conduct_research(
        query: str,
        user_id: int | None = None,
        guest_id: str | None = None,
        config=None,  # noqa: ANN001
        plan_items=None,  # noqa: ANN001
    ):
        nonlocal captured_plan_items
        captured_plan_items = plan_items
        yield {
            "type": "report_complete",
            "message": "done",
            "data": {
                "id": "task-plan",
                "user_id": user_id,
                "guest_id": guest_id,
                "query": query,
                "status": "completed",
                "plan": [],
                "sections": [],
                "results": [],
                "report": "# planned",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        }

    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.run",
        fake_conduct_research,
    )

    response = client.post(
        "/api/research",
        json={
            "query": "AI 产业趋势",
            "stream": False,
            "plan_items": [
                {
                    "step": 1,
                    "title": "AI 产业采用率",
                    "dimension": "数据趋势",
                    "rationale": "需要量化趋势。",
                    "search_queries": ["AI adoption survey"],
                    "expected_outcome": "获得采用率数据。",
                    "evidence_targets": ["统计数据"],
                }
            ],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert captured_plan_items is not None
    assert captured_plan_items[0].title == "AI 产业采用率"


def test_stream_research_emits_error_event_on_failure(
    monkeypatch, client: TestClient, caplog
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
    caplog.set_level("ERROR", logger="backend.app.api.research")

    with client.stream(
        "POST",
        "/api/research",
        json={"query": "test query", "stream": True},
        headers={**AUTH_HEADERS, "X-Request-ID": "req-stream-error"},
    ) as response:
        body = "".join(
            chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            for chunk in response.iter_text()
        )

    assert response.status_code == 200
    assert '"type": "error"' in body
    assert "研究过程中发生错误，请稍后重试" in body
    assert "boom" not in body
    error_log = next(
        record for record in caplog.records if record.getMessage().startswith("研究任务执行失败")
    )
    assert error_log.request_id == "req-stream-error"


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


def test_get_research_task_returns_authenticated_owner_payload(
    client: TestClient,
    monkeypatch,
    tmp_path,
) -> None:
    repository = ResearchRepository(str(tmp_path / "research.db"))
    repository.save_task(
        ResearchTask(
            id="current-user-task",
            user_id=1,
            query="visible query",
            status=ResearchTaskStatus.COMPLETED,
            final_report="# visible",
        )
    )
    monkeypatch.setattr(
        "backend.app.api.research.research_orchestrator.repository",
        repository,
    )

    response = client.get("/api/research/current-user-task", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "current-user-task"
    assert payload["query"] == "visible query"
    assert payload["final_report"] == "# visible"


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


def test_resume_task_preserves_old_evidence_before_rerun(monkeypatch, tmp_path) -> None:
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

    monkeypatch.setattr("backend.app.core.orchestrator.ResearchAgent.run", fake_agent_run)

    events = []

    async def collect() -> None:
        async for event in orchestrator.resume_task(task.id, user_id=1):
            events.append(event)

    import asyncio
    import sqlite3

    asyncio.run(collect())

    with sqlite3.connect(orchestrator.repository.db_path) as conn:
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM evidence_items WHERE task_id = ?",
            (task.id,),
        ).fetchone()[0]

    assert events[0]["type"] == "resume"
    assert evidence_count == 1


def test_repository_loads_unfinished_checkpoint_after_restart(tmp_path) -> None:
    db_path = str(tmp_path / "research.db")
    repository = ResearchRepository(db_path)
    task = ResearchTask(
        id="task-checkpoint",
        user_id=1,
        query="checkpoint query",
        status=ResearchTaskStatus.RESEARCHING,
        sections=[
            ResearchSection(
                id="subquery-1",
                step=1,
                title="done query",
                description="已完成切片",
                status="completed",
                analysis="saved analysis",
                evidence_ids=["evidence-old"],
            )
        ],
        stream_events=[
            {"type": "plan", "message": "saved plan", "data": [{"step": 1}]}
        ],
    )
    repository.save_task(task)

    restarted_repository = ResearchRepository(db_path)
    loaded = restarted_repository.load_task("task-checkpoint", user_id=1)

    assert loaded is not None
    assert loaded.status == ResearchTaskStatus.RESEARCHING
    assert loaded.sections[0].analysis == "saved analysis"
    assert loaded.sections[0].evidence_ids == ["evidence-old"]
    assert loaded.stream_events[0]["message"] == "saved plan"


def test_resume_reuses_completed_checkpoint_sections_after_restart(
    monkeypatch,
    tmp_path,
) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()
    task = ResearchTask(
        id="task-resume-checkpoint",
        user_id=1,
        query="pending query",
        status=ResearchTaskStatus.RESEARCHING,
        sections=[
            ResearchSection(
                id="subquery-1",
                step=1,
                title="done query",
                description="已完成切片",
                status="completed",
                analysis="saved analysis",
                citations=[
                    Citation(
                        title="Old Source",
                        link="https://example.com/old",
                        source="web",
                    )
                ],
                search_sources=[
                    {
                        "title": "Old Source",
                        "link": "https://example.com/old",
                        "source": "web",
                        "query": "done query",
                        "status": "cited",
                    }
                ],
                evidence_ids=["evidence-old"],
            ),
            ResearchSection(
                id="subquery-2",
                step=2,
                title="pending query",
                description="待恢复切片",
            ),
        ],
    )
    orchestrator.repository.save_task(task)
    orchestrator.repository.save_evidence(
        task.id,
        EvidenceItem(
            id="evidence-old",
            section_id="subquery-1",
            query="done query",
            source_type="web",
            title="Old Evidence",
            link="https://example.com/old",
            snippet="old",
        ),
    )
    processed_queries: list[str] = []

    async def fake_plan_items(self, on_event=None):  # noqa: ANN001
        return [
            ResearchPlanItem(
                step=1,
                title="done query",
                dimension="已完成",
                rationale="checkpoint",
            ),
            ResearchPlanItem(
                step=2,
                title="pending query",
                dimension="待恢复",
                rationale="resume",
            ),
        ]

    async def fake_process_query_tree(
        self,  # noqa: ANN001
        *,
        step: int,
        query: str,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event=None,  # noqa: ANN001
        depth: int = 1,
        parent_query: str = "",
        inherited_plan_item=None,  # noqa: ANN001
    ) -> list[SubQueryContext]:
        processed_queries.append(query)
        return [
            SubQueryContext(
                step=step,
                query=query,
                context="new analysis",
                evidence_ids=["evidence-new"],
            )
        ]

    async def fake_write_report(self, **kwargs):  # noqa: ANN001, ANN003
        return "# resumed"

    monkeypatch.setattr(
        "backend.app.research.conductor.ResearchConductor._plan_items",
        fake_plan_items,
    )
    monkeypatch.setattr(
        "backend.app.research.conductor.ResearchConductor._process_query_tree",
        fake_process_query_tree,
    )
    monkeypatch.setattr(
        "backend.app.research.writer.ResearchWriter.write_report",
        fake_write_report,
    )

    events = []

    async def collect() -> None:
        async for event in orchestrator.resume_task(task.id, user_id=1):
            events.append(event)

    import asyncio
    import sqlite3

    asyncio.run(collect())
    saved = orchestrator.repository.load_task(task.id, user_id=1)

    with sqlite3.connect(orchestrator.repository.db_path) as conn:
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM evidence_items WHERE task_id = ?",
            (task.id,),
        ).fetchone()[0]

    assert events[0]["type"] == "resume"
    assert processed_queries == ["pending query"]
    assert saved is not None
    assert [section.title for section in saved.sections] == [
        "done query",
        "pending query",
    ]
    assert saved.sections[0].analysis == "saved analysis"
    assert saved.sections[0].evidence_ids == ["evidence-old"]
    assert saved.sections[1].analysis == "new analysis"
    assert evidence_count == 1


def test_resume_checkpoint_report_has_one_block_per_section_and_unique_refs(
    monkeypatch,
    tmp_path,
) -> None:
    orchestrator = ResearchOrchestrator()
    orchestrator.repository.db_path = str(tmp_path / "research.db")
    orchestrator.repository._ensure_db()
    task = ResearchTask(
        id="task-resume-report",
        user_id=1,
        query="pending query",
        status=ResearchTaskStatus.RESEARCHING,
        sections=[
            ResearchSection(
                id="subquery-1",
                step=1,
                title="done query",
                description="已完成切片",
                status="completed",
                analysis="saved analysis",
                compressed_evidence="saved evidence",
                citations=[
                    Citation(
                        title="Old Source",
                        link="https://example.com/old",
                        source="web",
                    )
                ],
                search_sources=[
                    {
                        "title": "Old Source",
                        "link": "https://example.com/old",
                        "source": "web",
                        "query": "done query",
                        "snippet": "old snippet",
                        "status": "cited",
                    }
                ],
                evidence_ids=["evidence-old"],
            ),
            ResearchSection(
                id="subquery-2",
                step=2,
                title="pending query",
                description="待恢复切片",
            ),
        ],
    )
    orchestrator.repository.save_task(task)
    processed_queries: list[str] = []
    captured_prompts: list[str] = []

    async def fake_plan_items(self, on_event=None):  # noqa: ANN001
        return [
            ResearchPlanItem(step=1, title="done query"),
            ResearchPlanItem(step=2, title="pending query"),
        ]

    async def fake_process_query_tree(
        self,  # noqa: ANN001
        *,
        step: int,
        query: str,
        plan_items: list[ResearchPlanItem],
        total: int,
        on_event=None,  # noqa: ANN001
        depth: int = 1,
        parent_query: str = "",
        inherited_plan_item=None,  # noqa: ANN001
    ) -> list[SubQueryContext]:
        processed_queries.append(query)
        return [
            SubQueryContext(
                step=step,
                query=query,
                sources=[
                    ResearchSource(
                        title="New Source",
                        link="https://example.com/new",
                        query=query,
                        snippet="new snippet",
                    )
                ],
                citations=[
                    Citation(
                        title="New Source",
                        link="https://example.com/new",
                        source="web",
                    )
                ],
                context="new analysis",
                compressed_evidence="new evidence",
                evidence_ids=["evidence-new"],
            )
        ]

    async def fake_llm_call(self, prompt: str, **kwargs):  # noqa: ANN001, ARG001
        captured_prompts.append(prompt)
        return (
            "# resumed\n\n"
            "旧分析 [1] 与新分析 [2].\n\n"
            "## 8. 参考来源\n\n"
            "- [9] bogus - https://example.com/bogus"
        )

    async def fake_claim_support(self, report, reference_entries):  # noqa: ANN001
        return {
            "claims": [],
            "summary": {
                "claim_count": 0,
                "supported_claim_count": 0,
                "partially_supported_claim_count": 0,
                "unsupported_claim_count": 0,
                "citation_support_rate": 0.0,
            },
        }

    monkeypatch.setattr(
        "backend.app.research.conductor.ResearchConductor._plan_items",
        fake_plan_items,
    )
    monkeypatch.setattr(
        "backend.app.research.conductor.ResearchConductor._process_query_tree",
        fake_process_query_tree,
    )
    monkeypatch.setattr(
        "backend.app.research.writer.DeepSeekLLM._acall",
        fake_llm_call,
    )
    monkeypatch.setattr(
        "backend.app.research.writer.ResearchWriter.evaluate_claim_support",
        fake_claim_support,
    )

    events = []

    async def collect() -> None:
        async for event in orchestrator.resume_task(task.id, user_id=1):
            events.append(event)

    import asyncio

    asyncio.run(collect())
    saved = orchestrator.repository.load_task(task.id, user_id=1)
    report_complete = next(event for event in events if event["type"] == "report_complete")

    assert processed_queries == ["pending query"]
    assert len(captured_prompts) == 1
    assert captured_prompts[0].count("### done query\n") == 1
    assert captured_prompts[0].count("### pending query\n") == 1
    assert captured_prompts[0].count("saved analysis") == 1
    assert saved is not None
    assert saved.status == ResearchTaskStatus.COMPLETED
    assert report_complete["data"]["report"] == saved.final_report
    assert "https://example.com/bogus" not in saved.final_report
    assert saved.final_report.count("https://example.com/old") == 1
    assert saved.final_report.count("https://example.com/new") == 1
    assert "- [1] Old Source - https://example.com/old" in saved.final_report
    assert "- [2] New Source - https://example.com/new" in saved.final_report

def test_orchestrator_run_emits_task_id_before_research(
    monkeypatch, tmp_path, caplog
) -> None:
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
    caplog.set_level("INFO", logger="backend.app.core.orchestrator")

    events = []

    async def collect() -> None:
        async for event in orchestrator.run(
            "new query",
            user_id=1,
            request_id="req-task",
        ):
            events.append(event)

    import asyncio

    asyncio.run(collect())

    assert events[0]["type"] == "task_created"
    assert events[0]["message"] == "研究任务已创建"
    assert events[0]["data"]["task_id"] == events[1]["data"]["id"]
    assert events[0]["data"]["request_id"] == "req-task"
    assert events[0]["data"]["query"] == "new query"
    task_log = next(
        record for record in caplog.records if record.getMessage() == "task_created"
    )
    assert task_log.request_id == "req-task"
    assert task_log.task_id == events[0]["data"]["task_id"]
    saved = orchestrator.repository.load_task(events[0]["data"]["task_id"], user_id=1)
    assert saved
    assert [event["type"] for event in saved.stream_events] == ["report_complete"]


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


def test_research_agent_emits_gpt_researcher_payload(monkeypatch, caplog) -> None:
    agent = ResearchAgent(
        query="DeepSeek enterprise",
        max_concurrency=1,
        request_id="req-gptr",
    )
    task = ResearchTask(id="task-gptr", query="DeepSeek enterprise")
    caplog.set_level("INFO", logger="backend.app.research.agent")
    context = SubQueryContext(
        step=1,
        query="DeepSeek 企业落地案例有哪些？",
        depth=2,
        parent_query="DeepSeek 企业应用",
        context="发现 A",
        evidence_ids=["evidence-1"],
        compressed_evidence="研究主题: DeepSeek 企业落地案例有哪些？",
        verification={
            "passed": True,
            "score": 1.0,
            "issues": [],
            "summary": "证据充分",
        },
        deep_research=DeepResearchDecision(
            should_continue=False,
            reason="证据已覆盖核心案例。",
            evidence_gaps=["缺少海外案例"],
            follow_up_queries=["DeepSeek overseas case study"],
            stop_condition="达到最大深度",
        ),
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
                    "data": {
                        "sub_queries": [context.query],
                        "plan_items": [
                            {
                                "step": 1,
                                "title": context.query,
                                "dimension": "案例研究",
                                "rationale": "用实际案例验证企业落地判断。",
                                "search_queries": [
                                    "DeepSeek enterprise case study",
                                    "DeepSeek 企业 落地 案例",
                                ],
                                "expected_outcome": "获得可引用的企业应用案例。",
                                "evidence_targets": ["案例研究", "客户故事"],
                            }
                        ],
                    },
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
    assert report_complete["data"]["request_id"] == "req-gptr"
    assert report_complete["data"]["workflow_engine"] == "langgraph"
    assert report_complete["data"]["report"] == "# report"
    assert report_complete["data"]["cost_summary"]["total_tokens"] > 0
    assert report_complete["data"]["process_metrics"]["total_tokens"] > 0
    assert report_complete["data"]["process_metrics"]["elapsed_seconds"] >= 0
    assert report_complete["data"]["results"][0]["title"] == context.query
    assert report_complete["data"]["results"][0]["verification"]["passed"] is True
    assert report_complete["data"]["results"][0]["compressed_evidence"] == context.compressed_evidence
    assert report_complete["data"]["results"][0]["depth"] == 2
    assert report_complete["data"]["results"][0]["parent_query"] == "DeepSeek 企业应用"
    assert report_complete["data"]["results"][0]["deep_research"]["reason"] == "证据已覆盖核心案例。"
    assert report_complete["data"]["sections"][0]["evidence_ids"] == context.evidence_ids
    assert report_complete["data"]["sections"][0]["evidence_gaps"] == ["缺少海外案例"]
    assert report_complete["data"]["sections"][0]["follow_up_queries"] == [
        "DeepSeek overseas case study"
    ]
    assert report_complete["data"]["sections"][0]["deep_research_stop_condition"] == "达到最大深度"
    assert report_complete["data"]["plan"][0]["dimension"] == "案例研究"
    assert report_complete["data"]["plan"][0]["rationale"] == "用实际案例验证企业落地判断。"
    assert report_complete["data"]["plan"][0]["search_queries"] == [
        "DeepSeek enterprise case study",
        "DeepSeek 企业 落地 案例",
    ]
    assert report_complete["data"]["plan"][0]["evidence_targets"] == [
        "案例研究",
        "客户故事",
    ]
    assert task.cost_summary["total_tokens"] > 0
    assert task.sections[0].tool == "research_conductor"
    report_log = next(
        record for record in caplog.records if record.getMessage() == "report_complete"
    )
    assert report_log.task_id == "task-gptr"
    assert report_log.request_id == "req-gptr"
    assert report_log.research_event_type == "report_complete"
    assert report_log.section_count == 1
    assert report_log.deep_section_count == 1
    assert report_log.max_depth == 2
