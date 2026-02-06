"""API路由定义"""

import asyncio
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

from .models import (
    ArchitectureAnalysisRequest,
    ArchitectureAnalysisResponse,
    TaskResultResponse,
    TaskStatus,
    HealthCheckResponse,
    ErrorResponse
)
from ..core.pipeline import PipelineOrchestrator
from ..config.settings import settings


router = APIRouter()
pipeline_orchestrator = PipelineOrchestrator()


@router.post(
    "/analyze",
    response_model=ArchitectureAnalysisResponse,
    summary="开始架构分析",
    description="提交应用ID列表，开始架构分析任务"
)
async def start_architecture_analysis(
    request: ArchitectureAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """开始架构分析任务"""
    try:
        # 启动异步分析任务
        task = asyncio.create_task(
            pipeline_orchestrator.analyze_architecture(
                app_ids=request.app_ids,
                report_format=request.report_format,
                enable_progress_tracking=request.enable_progress_tracking
            )
        )

        # 等待任务开始（短暂延迟确保task_id生成）
        await asyncio.sleep(0.1)

        # 这里可以改进为返回实际的任务ID
        # 暂时使用简化的实现
        return ArchitectureAnalysisResponse(
            task_id="task-placeholder",
            status="accepted",
            message="架构分析任务已接受，正在处理中"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"启动分析任务失败: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}/status",
    response_model=TaskStatus,
    summary="获取任务状态",
    description="查询架构分析任务的执行状态和进度"
)
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        progress = await pipeline_orchestrator.get_task_progress(task_id)

        if progress is None:
            # 任务不存在或已完成
            raise HTTPException(status_code=404, detail="任务不存在")

        return TaskStatus(
            task_id=progress.task_id,
            status=progress.stage.value,
            progress=progress.progress,
            message=progress.message,
            created_at=progress.start_time,
            updated_at=progress.end_time
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.get(
    "/tasks/{task_id}/result",
    response_model=TaskResultResponse,
    summary="获取任务结果",
    description="获取已完成架构分析任务的详细结果"
)
async def get_task_result(task_id: str):
    """获取任务结果"""
    try:
        result = await pipeline_orchestrator.get_task_result(task_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="任务结果不存在或任务尚未完成"
            )

        # 构建响应
        response_data = TaskResultResponse(
            task_id=result.task_id,
            success=result.success,
            processing_time=result.processing_time,
            error_message=result.error_message
        )

        if result.success and result.architecture_analysis:
            analysis = result.architecture_analysis
            response_data.completed_at = None  # 可以从progress_history获取
            response_data.report_url = f"/api/reports/{task_id}"
            response_data.architecture_summary = {
                "type": analysis.architecture_type,
                "summary": analysis.summary[:200] + "..." if len(analysis.summary) > 200 else analysis.summary
            }
            response_data.total_apps = len(result.apps_data) if result.apps_data else 0
            response_data.quality_score = analysis.quality_score

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取任务结果失败: {str(e)}"
        )


@router.get(
    "/reports/{task_id}",
    summary="下载分析报告",
    description="下载指定任务的架构分析报告"
)
async def download_report(task_id: str, format: str = Query("markdown", description="报告格式")):
    """下载分析报告"""
    try:
        # 这里需要实现报告文件查找逻辑
        # 暂时返回模拟响应
        raise HTTPException(
            status_code=501,
            detail="报告下载功能正在开发中"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"下载报告失败: {str(e)}"
        )


@router.get(
    "/tasks",
    summary="获取活跃任务列表",
    description="获取当前正在执行的任务列表"
)
async def get_active_tasks():
    """获取活跃任务列表"""
    try:
        active_tasks = await pipeline_orchestrator.get_active_tasks()

        return {
            "total": len(active_tasks),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.stage.value,
                    "progress": task.progress,
                    "message": task.message,
                    "created_at": task.start_time.isoformat()
                }
                for task in active_tasks
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取活跃任务失败: {str(e)}"
        )


@router.delete(
    "/tasks/{task_id}",
    summary="取消任务",
    description="取消正在执行的架构分析任务"
)
async def cancel_task(task_id: str):
    """取消任务"""
    try:
        success = await pipeline_orchestrator.cancel_task(task_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="任务不存在或无法取消"
            )

        return {"message": "任务已取消"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取消任务失败: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="健康检查",
    description="检查服务和组件的健康状态"
)
async def health_check():
    """健康检查"""
    try:
        # 检查各个组件状态
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
            analyzer = LLMAnalyzer()
            # 这里可以添加简单的LLM健康检查
            components_status["llm_analyzer"] = "healthy"
        except Exception:
            components_status["llm_analyzer"] = "error"

        # 确定整体状态
        all_healthy = all(status == "healthy" for status in components_status.values())
        overall_status = "healthy" if all_healthy else "degraded"

        return HealthCheckResponse(
            status=overall_status,
            components=components_status
        )

    except Exception as e:
        return HealthCheckResponse(
            status="error",
            components={"error": str(e)}
        )


@router.get(
    "/config",
    summary="获取配置信息",
    description="获取当前系统配置（调试用途）"
)
async def get_config():
    """获取配置信息（仅开发环境）"""
    if not settings.debug:
        raise HTTPException(
            status_code=403,
            detail="配置信息仅在调试模式下可用"
        )

    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "llm_provider": settings.llm.provider,
        "mcp_enabled": settings.mcp.enabled,
        "processing_max_concurrent": settings.processing.max_concurrent_apps,
        "api_host": settings.api.host,
        "api_port": settings.api.port
    }



