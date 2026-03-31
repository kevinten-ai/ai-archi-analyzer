"""API路由定义"""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from loguru import logger

from .models import (
    ArchitectureAnalysisRequest,
    ArchitectureAnalysisResponse,
    TaskResultResponse,
    TaskStatus,
    HealthCheckResponse,
    ErrorResponse,
)
from ..config.settings import settings
from ..core.pipeline import PipelineOrchestrator, PipelineStage
from ..core.task_store import task_store


router = APIRouter()

# 延迟初始化的编排器实例
_pipeline_orchestrator: Optional[PipelineOrchestrator] = None


def _get_orchestrator() -> PipelineOrchestrator:
    """获取管道编排器（延迟初始化，避免导入时触发配置校验）"""
    global _pipeline_orchestrator
    if _pipeline_orchestrator is None:
        async def on_progress(task_id: str, stage: PipelineStage, progress: float, message: str) -> None:
            await task_store.update_progress(task_id, stage, progress, message)

        _pipeline_orchestrator = PipelineOrchestrator(progress_callback=on_progress)
    return _pipeline_orchestrator


async def _run_analysis_task(
    task_id: str,
    app_ids: list,
    report_format: str,
) -> None:
    """后台执行分析任务，完成后将结果写入TaskStore"""
    try:
        orchestrator = _get_orchestrator()
        result = await orchestrator.analyze_architecture(
            app_ids=app_ids,
            report_format=report_format,
            task_id=task_id,
        )
        await task_store.complete_task(task_id, result)
    except Exception as e:
        logger.error(f"分析任务异常: {task_id}, {e}")
        from ..core.pipeline import PipelineResult
        fail_result = PipelineResult(task_id=task_id, success=False, error_message=str(e))
        await task_store.complete_task(task_id, fail_result)


@router.post(
    "/analyze",
    response_model=ArchitectureAnalysisResponse,
    summary="开始架构分析",
    description="提交应用ID列表，开始架构分析任务",
)
async def start_architecture_analysis(request: ArchitectureAnalysisRequest):
    """开始架构分析任务"""
    # 生成task_id并注册到TaskStore
    orchestrator = _get_orchestrator()
    task_id = orchestrator.generate_task_id()
    await task_store.create_task(task_id)

    # 在后台启动分析任务
    asyncio.create_task(
        _run_analysis_task(task_id, request.app_ids, request.report_format)
    )

    return ArchitectureAnalysisResponse(
        task_id=task_id,
        status="accepted",
        message="架构分析任务已接受，正在处理中",
    )


@router.get(
    "/tasks/{task_id}/status",
    response_model=TaskStatus,
    summary="获取任务状态",
    description="查询架构分析任务的执行状态和进度",
)
async def get_task_status(task_id: str):
    """获取任务状态"""
    record = await task_store.get_task(task_id)

    if record is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatus(
        task_id=record.task_id,
        status=record.status,
        progress=record.progress,
        message=record.message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/tasks/{task_id}/result",
    response_model=TaskResultResponse,
    summary="获取任务结果",
    description="获取已完成架构分析任务的详细结果",
)
async def get_task_result(task_id: str):
    """获取任务结果"""
    record = await task_store.get_task(task_id)

    if record is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = record.result
    if result is None:
        raise HTTPException(status_code=404, detail="任务尚未完成")

    response = TaskResultResponse(
        task_id=result.task_id,
        success=result.success,
        processing_time=result.processing_time,
        error_message=result.error_message,
    )

    if result.success and result.architecture_analysis:
        analysis = result.architecture_analysis
        response.completed_at = record.completed_at
        response.report_url = f"/api/reports/{task_id}"
        response.architecture_summary = {
            "type": analysis.architecture_type,
            "summary": (
                analysis.summary[:200] + "..."
                if len(analysis.summary) > 200
                else analysis.summary
            ),
        }
        response.total_apps = len(result.apps_data) if result.apps_data else 0
        response.quality_score = analysis.quality_score

    return response


@router.get(
    "/reports/{task_id}",
    summary="下载分析报告",
    description="下载指定任务的架构分析报告",
)
async def download_report(
    task_id: str,
    format: str = Query("markdown", description="报告格式"),
):
    """下载分析报告"""
    result = await task_store.get_task_result(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail="任务不存在或尚未完成")

    if not result.report_path:
        raise HTTPException(status_code=404, detail="报告文件不存在")

    report_path = Path(result.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告文件已被删除")

    # 确定MIME类型
    media_types = {
        "markdown": "text/markdown",
        "json": "application/json",
        "html": "text/html",
    }
    media_type = media_types.get(format, "application/octet-stream")

    return FileResponse(
        path=str(report_path),
        media_type=media_type,
        filename=report_path.name,
    )


@router.get(
    "/tasks",
    summary="获取任务列表",
    description="获取所有任务列表",
)
async def get_tasks(active_only: bool = Query(False, description="仅显示活跃任务")):
    """获取任务列表"""
    if active_only:
        tasks = await task_store.get_active_tasks()
    else:
        tasks = await task_store.get_all_tasks()

    return {
        "total": len(tasks),
        "tasks": [
            {
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
            for task in tasks
        ],
    }


@router.delete(
    "/tasks/{task_id}",
    summary="取消任务",
    description="取消正在执行的架构分析任务",
)
async def cancel_task(task_id: str):
    """取消任务"""
    success = await task_store.cancel_task(task_id)

    if not success:
        raise HTTPException(status_code=404, detail="任务不存在或无法取消")

    return {"message": "任务已取消"}


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="健康检查",
    description="检查服务和组件的健康状态",
)
async def health_check():
    """健康检查"""
    components_status = {}

    # 检查MCP连接
    try:
        from ..collectors.mcp_collector import MCPCollector
        collector = MCPCollector()
        is_healthy = await collector.health_check()
        components_status["mcp_collector"] = "healthy" if is_healthy else "unhealthy"
    except Exception:
        components_status["mcp_collector"] = "error"

    # 检查LLM连接
    try:
        from ..core.analyzer import LLMAnalyzer
        LLMAnalyzer()
        components_status["llm_analyzer"] = "healthy"
    except Exception:
        components_status["llm_analyzer"] = "error"

    all_healthy = all(status == "healthy" for status in components_status.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        components=components_status,
    )


@router.get(
    "/config",
    summary="获取配置信息",
    description="获取当前系统配置（调试用途）",
)
async def get_config():
    """获取配置信息（仅开发环境）"""
    if not settings.debug:
        raise HTTPException(status_code=403, detail="配置信息仅在调试模式下可用")

    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "llm_provider": settings.llm.provider,
        "mcp_enabled": settings.mcp.enabled,
        "processing_max_concurrent": settings.processing.max_concurrent_apps,
        "api_host": settings.api.host,
        "api_port": settings.api.port,
    }
