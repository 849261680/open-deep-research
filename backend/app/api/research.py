import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents.langchain_research_agent import langchain_research_agent
from ..core.deps import get_current_user
from ..core.deps import get_optional_current_user
from ..core.orchestrator import research_orchestrator
from ..models.user import User

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    stream: bool | None = True


class ResearchResponse(BaseModel):
    query: str
    status: str
    data: dict


class ResumeResearchRequest(BaseModel):
    task_id: str
    stream: bool | None = True


class StopResearchRequest(BaseModel):
    task_id: str


@router.options("/research")
async def research_options():
    """处理CORS预检请求"""
    return {"message": "OK"}


@router.post("/research", response_model=None)
async def start_research(
    request: ResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse | ResearchResponse:
    """开始研究任务"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="研究问题不能为空")

    if request.stream:
        # 流式响应
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for update in langchain_research_agent.conduct_research(
                    request.query, user_id=current_user.id if current_user else None
                ):
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_update = {
                    "type": "error",
                    "message": f"研究过程中发生错误: {str(e)}",
                    "data": None,
                }
                yield f"data: {json.dumps(error_update, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    # 非流式响应
    try:
        results = []
        final_payload: dict[str, object] | None = None
        async for update in langchain_research_agent.conduct_research(
            request.query, user_id=current_user.id if current_user else None
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
        raise HTTPException(status_code=500, detail=f"研究失败: {str(e)}") from e


@router.post("/research/resume", response_model=None)
async def resume_research(
    request: ResumeResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse | ResearchResponse:
    """恢复已有研究任务"""
    if not request.task_id.strip():
        raise HTTPException(status_code=400, detail="任务ID不能为空")

    if request.stream:
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for update in research_orchestrator.resume_task(
                    request.task_id, user_id=current_user.id if current_user else None
                ):
                    yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_update = {
                    "type": "error",
                    "message": f"恢复研究过程中发生错误: {str(e)}",
                    "data": None,
                }
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
            request.task_id, user_id=current_user.id if current_user else None
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
        raise HTTPException(status_code=500, detail=f"恢复研究失败: {str(e)}") from e


@router.post("/research/stop")
async def stop_research(
    request: StopResearchRequest,
    current_user: User | None = Depends(get_optional_current_user),
):
    """停止正在运行的研究任务。"""
    if not request.task_id.strip():
        raise HTTPException(status_code=400, detail="任务ID不能为空")

    task = research_orchestrator.stop_task(
        request.task_id,
        user_id=current_user.id if current_user else None,
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
    current_user: User | None = Depends(get_optional_current_user),
):
    """获取研究状态"""
    return {
        "status": "ready",
        "steps": langchain_research_agent.get_research_history(
            user_id=current_user.id if current_user else None
        ),
        "message": "研究代理已准备就绪",
    }


@router.get("/research/history")
async def get_research_history(
    current_user: User | None = Depends(get_optional_current_user),
):
    """获取研究历史"""
    history = langchain_research_agent.get_research_history(
        user_id=current_user.id if current_user else None
    )
    return {
        "history": history,
        "total": len(history),
    }


@router.get("/research/{task_id}")
async def get_research_task(
    task_id: str,
    current_user: User | None = Depends(get_optional_current_user),
):
    """获取单个研究任务详情"""
    task = research_orchestrator.get_task(
        task_id,
        user_id=current_user.id if current_user else None,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    return task


@router.delete("/research/history")
async def clear_research_history(_current_user: User = Depends(get_current_user)):
    """清空研究历史和记忆"""
    langchain_research_agent.clear_memory()
    return {"message": "研究历史和记忆已清空"}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "Deep Research Agent API is running"}
