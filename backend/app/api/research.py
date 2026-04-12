import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..agents.langchain_research_agent import langchain_research_agent
from ..core.orchestrator import research_orchestrator

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


@router.options("/research")
async def research_options():
    """处理CORS预检请求"""
    return {"message": "OK"}


@router.post("/research", response_model=None)
async def start_research(
    request: ResearchRequest,
) -> StreamingResponse | ResearchResponse:
    """开始研究任务"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="研究问题不能为空")

    if request.stream:
        # 流式响应
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for update in langchain_research_agent.conduct_research(
                    request.query
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
        async for update in langchain_research_agent.conduct_research(request.query):
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
) -> StreamingResponse | ResearchResponse:
    """恢复已有研究任务"""
    if not request.task_id.strip():
        raise HTTPException(status_code=400, detail="任务ID不能为空")

    if request.stream:
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for update in research_orchestrator.resume_task(request.task_id):
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
        async for update in research_orchestrator.resume_task(request.task_id):
            results.append(update)
            if update.get("type") in {"report_complete", "error"} and isinstance(
                update.get("data"), dict
            ):
                final_payload = dict(update["data"])

        return ResearchResponse(
            query=request.task_id,
            status="completed",
            data=final_payload or {"updates": results},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复研究失败: {str(e)}") from e


@router.get("/research/status")
async def get_research_status():
    """获取研究状态"""
    return {
        "status": "ready",
        "steps": langchain_research_agent.get_research_history(),
        "message": "研究代理已准备就绪",
    }


@router.get("/research/history")
async def get_research_history():
    """获取研究历史"""
    return {
        "history": langchain_research_agent.get_research_history(),
        "total": len(langchain_research_agent.get_research_history()),
    }


@router.get("/research/{task_id}")
async def get_research_task(task_id: str):
    """获取单个研究任务详情"""
    task = research_orchestrator.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    return task


@router.delete("/research/history")
async def clear_research_history():
    """清空研究历史和记忆"""
    langchain_research_agent.clear_memory()
    return {"message": "研究历史和记忆已清空"}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "Deep Research Agent API is running"}
