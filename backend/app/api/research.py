import json
import logging
import os
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from ..core.deps import get_current_user
from ..core.deps import get_optional_current_user
from ..core.logging import bind_request_id
from ..core.logging import get_request_id
from ..core.logging import reset_request_id
from ..core.deps import resolve_guest_id
from ..core.orchestrator import research_orchestrator
from ..models.user import User
from ..research.config import ResearchConfig
from ..research.models import ResearchPlanItem

logger = logging.getLogger(__name__)

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    stream: bool | None = True
    config: ResearchConfig | None = None
    plan_items: list[ResearchPlanItem] | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("研究问题不能为空")
        if len(v) > 500:
            raise ValueError("研究问题不能超过500个字符")
        return v


class ResearchPlanRequest(BaseModel):
    """Request body for generating a confirmable plan."""

    query: str
    config: ResearchConfig | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("研究问题不能为空")
        if len(v) > 500:
            raise ValueError("研究问题不能超过500个字符")
        return v


class ResearchResponse(BaseModel):
    query: str
    status: str
    data: dict


class ResumeResearchRequest(BaseModel):
    task_id: str
    stream: bool | None = True


class StopResearchRequest(BaseModel):
    task_id: str


def _stream_error_payload(
    message: str,
    exc: Exception,
    *,
    request_id: str,
    task_id: str | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {"request_id": request_id}
    if task_id:
        data["task_id"] = task_id
    if os.getenv("RESEARCH_STREAM_INCLUDE_ERROR_DETAIL", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        data["detail"] = str(exc)
    return {
        "type": "error",
        "message": message,
        "data": data,
    }


@router.options("/research")
async def research_options():
    """处理CORS预检请求"""
    return {"message": "OK"}


@router.post("/research", response_model=None)
async def start_research(
    http_request: Request,
    request: ResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse | ResearchResponse:
    """开始研究任务"""
    request_id = get_request_id(http_request)
    user_id = current_user.id if current_user else None
    guest_id = None if current_user else resolve_guest_id(http_request)

    if request.stream:
        async def generate() -> AsyncGenerator[str, None]:
            token = bind_request_id(request_id)
            task_id: str | None = None
            try:
                async for update in _research_updates(request, user_id, guest_id):
                    task_id = _task_id_from_update(update) or task_id
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            except Exception as exc:
                logger.exception(
                    "研究任务执行失败 query=%r user_id=%s",
                    request.query,
                    user_id,
                    extra={"request_id": request_id, "task_id": task_id},
                )
                error_update = _stream_error_payload(
                    "研究过程中发生错误，请稍后重试",
                    exc,
                    request_id=request_id,
                    task_id=task_id,
                )
                yield f"data: {json.dumps(error_update, ensure_ascii=False)}\n\n"
            finally:
                reset_request_id(token)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    try:
        token = bind_request_id(request_id)
        results = []
        final_payload: dict[str, object] | None = None
        try:
            async for update in _research_updates(request, user_id, guest_id):
                results.append(update)
                data = update.get("data")
                if update.get("type") == "report_complete" and isinstance(data, dict):
                    final_payload = data
        finally:
            reset_request_id(token)

        return ResearchResponse(
            query=request.query,
            status="completed",
            data=final_payload or {"updates": results},
        )
    except Exception as e:
        logger.exception(
            "研究任务执行失败（非流式）query=%r user_id=%s",
            request.query,
            user_id,
            extra={"request_id": request_id, "task_id": None},
        )
        raise HTTPException(status_code=500, detail="研究失败，请稍后重试") from e


def _task_id_from_update(update: object) -> str | None:
    """Read the current task id from a streamed event payload."""
    if not isinstance(update, dict):
        return None
    data = update.get("data")
    if not isinstance(data, dict):
        return None
    candidate = data.get("task_id") or data.get("id")
    return candidate if isinstance(candidate, str) and candidate else None


def _research_updates(
    request: ResearchRequest,
    user_id: int | None,
    guest_id: str | None,
) -> AsyncGenerator[dict[str, object], None]:
    """Call orchestrator with only the optional kwargs the client provided."""
    if request.config is None and request.plan_items is None:
        return research_orchestrator.run(
            query=request.query,
            user_id=user_id,
            guest_id=guest_id,
        )
    if request.plan_items is None:
        return research_orchestrator.run(
            query=request.query,
            user_id=user_id,
            guest_id=guest_id,
            config=request.config,
        )
    if request.config is None:
        return research_orchestrator.run(
            query=request.query,
            user_id=user_id,
            guest_id=guest_id,
            plan_items=request.plan_items,
        )
    return research_orchestrator.run(
        query=request.query,
        user_id=user_id,
        guest_id=guest_id,
        config=request.config,
        plan_items=request.plan_items,
    )


@router.post("/research/plan", response_model=ResearchResponse)
async def preview_research_plan(
    request: ResearchPlanRequest,
) -> ResearchResponse:
    """Generate a research plan for user confirmation before execution."""
    try:
        plan_payload = await research_orchestrator.preview_plan(
            request.query,
            config=request.config,
        )
        return ResearchResponse(
            query=request.query,
            status="planned",
            data=plan_payload,
        )
    except Exception as e:
        logger.exception("研究计划生成失败 query=%r", request.query)
        raise HTTPException(status_code=500, detail="研究计划生成失败，请稍后重试") from e


@router.post("/research/resume", response_model=None)
async def resume_research(
    http_request: Request,
    request: ResumeResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse | ResearchResponse:
    """恢复已有研究任务"""
    if not request.task_id.strip():
        raise HTTPException(status_code=400, detail="任务ID不能为空")

    request_id = get_request_id(http_request)
    user_id = current_user.id if current_user else None
    guest_id = None if current_user else resolve_guest_id(http_request)

    if request.stream:
        async def generate() -> AsyncGenerator[str, None]:
            token = bind_request_id(request_id)
            try:
                async for update in research_orchestrator.resume_task(
                    request.task_id,
                    user_id=user_id,
                    guest_id=guest_id,
                ):
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            except Exception as exc:
                logger.exception(
                    "恢复研究任务失败 task_id=%r user_id=%s",
                    request.task_id,
                    user_id,
                    extra={"request_id": request_id, "task_id": request.task_id},
                )
                error_update = _stream_error_payload(
                    "恢复研究过程中发生错误，请稍后重试",
                    exc,
                    request_id=request_id,
                    task_id=request.task_id,
                )
                yield f"data: {json.dumps(error_update, ensure_ascii=False)}\n\n"
            finally:
                reset_request_id(token)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        token = bind_request_id(request_id)
        results = []
        final_payload: dict[str, object] | None = None
        try:
            async for update in research_orchestrator.resume_task(
                request.task_id,
                user_id=user_id,
                guest_id=guest_id,
            ):
                results.append(update)
                data = update.get("data")
                if update.get("type") in {"report_complete", "error"} and isinstance(
                    data,
                    dict,
                ):
                    final_payload = data
        finally:
            reset_request_id(token)

        return ResearchResponse(
            query=final_payload.get("query", "") if final_payload else "",
            status="completed",
            data=final_payload or {"updates": results},
        )
    except Exception as e:
        logger.exception(
            "恢复研究任务失败（非流式）task_id=%r user_id=%s",
            request.task_id,
            user_id,
            extra={"request_id": request_id, "task_id": request.task_id},
        )
        raise HTTPException(status_code=500, detail="恢复研究失败，请稍后重试") from e


@router.post("/research/stop")
async def stop_research(
    http_request: Request,
    request: StopResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
):
    """停止正在运行的研究任务。"""
    if not request.task_id.strip():
        raise HTTPException(status_code=400, detail="任务ID不能为空")

    task = research_orchestrator.stop_task(
        request.task_id,
        user_id=current_user.id if current_user else None,
        guest_id=None if current_user else resolve_guest_id(http_request),
    )
    if task is None:
        raise HTTPException(status_code=404, detail="研究任务不存在")

    return {
        "status": "stopped",
        "task_id": request.task_id,
        "task": task,
    }


@router.get("/research/status")
async def get_research_status(
    http_request: Request,
    current_user: User | None = Depends(get_optional_current_user),
):
    """获取研究状态"""
    guest_id = None if current_user else resolve_guest_id(http_request)
    return {
        "status": "ready",
        "steps": research_orchestrator.get_history(
            user_id=current_user.id if current_user else None,
            guest_id=guest_id,
        ),
        "message": "研究代理已准备就绪",
    }


@router.get("/research/history")
async def get_research_history(
    http_request: Request,
    current_user: User | None = Depends(get_optional_current_user),
):
    """获取研究历史"""
    history = research_orchestrator.get_history(
        user_id=current_user.id if current_user else None,
        guest_id=None if current_user else resolve_guest_id(http_request),
    )
    return {
        "history": history,
        "total": len(history),
    }


@router.get("/research/{task_id}")
async def get_research_task(
    http_request: Request,
    task_id: str,
    current_user: User | None = Depends(get_optional_current_user),
):
    """获取单个研究任务详情"""
    task = research_orchestrator.get_task(
        task_id,
        user_id=current_user.id if current_user else None,
        guest_id=None if current_user else resolve_guest_id(http_request),
    )
    if task is None:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    return task


@router.delete("/research/history")
async def clear_research_history(current_user: User = Depends(get_current_user)):
    """清空研究历史"""
    cleared = research_orchestrator.clear(user_id=current_user.id)
    return {"message": "研究历史已清空", "cleared": cleared}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "Deep Research Agent API is running"}
