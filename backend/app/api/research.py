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
from ..core.deps import resolve_guest_id
from ..core.orchestrator import research_orchestrator
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    stream: bool | None = True

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


def _stream_error_payload(message: str, exc: Exception) -> dict[str, object]:
    data: dict[str, object] | None = None
    if os.getenv("RESEARCH_STREAM_INCLUDE_ERROR_DETAIL", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        data = {"detail": str(exc)}
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
    user_id = current_user.id if current_user else None
    guest_id = None if current_user else resolve_guest_id(http_request)

    if request.stream:
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for update in research_orchestrator.run(
                    request.query,
                    user_id=user_id,
                    guest_id=guest_id,
                ):
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            except Exception as exc:
                logger.exception("研究任务执行失败 query=%r user_id=%s", request.query, user_id)
                error_update = _stream_error_payload(
                    "研究过程中发生错误，请稍后重试",
                    exc,
                )
                yield f"data: {json.dumps(error_update, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    try:
        results = []
        final_payload: dict[str, object] | None = None
        async for update in research_orchestrator.run(
            request.query,
            user_id=user_id,
            guest_id=guest_id,
        ):
            results.append(update)
            if update.get("type") == "report_complete" and isinstance(
                update.get("data"), dict
            ):
                final_payload = dict(update["data"])

        return ResearchResponse(
            query=request.query,
            status="completed",
            data=final_payload or {"updates": results},
        )
    except Exception as e:
        logger.exception("研究任务执行失败（非流式）query=%r user_id=%s", request.query, user_id)
        raise HTTPException(status_code=500, detail="研究失败，请稍后重试") from e


@router.post("/research/resume", response_model=None)
async def resume_research(
    http_request: Request,
    request: ResumeResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse | ResearchResponse:
    """恢复已有研究任务"""
    if not request.task_id.strip():
        raise HTTPException(status_code=400, detail="任务ID不能为空")

    user_id = current_user.id if current_user else None
    guest_id = None if current_user else resolve_guest_id(http_request)

    if request.stream:
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for update in research_orchestrator.resume_task(
                    request.task_id,
                    user_id=user_id,
                    guest_id=guest_id,
                ):
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            except Exception as exc:
                logger.exception("恢复研究任务失败 task_id=%r user_id=%s", request.task_id, user_id)
                error_update = _stream_error_payload(
                    "恢复研究过程中发生错误，请稍后重试",
                    exc,
                )
                yield f"data: {json.dumps(error_update, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    try:
        results = []
        final_payload: dict[str, object] | None = None
        async for update in research_orchestrator.resume_task(
            request.task_id,
            user_id=user_id,
            guest_id=guest_id,
        ):
            results.append(update)
            if update.get("type") in {"report_complete", "error"} and isinstance(
                update.get("data"), dict
            ):
                final_payload = dict(update["data"])

        return ResearchResponse(
            query=final_payload.get("query", "") if final_payload else "",
            status="completed",
            data=final_payload or {"updates": results},
        )
    except Exception as e:
        logger.exception("恢复研究任务失败（非流式）task_id=%r user_id=%s", request.task_id, user_id)
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
