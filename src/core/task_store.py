"""任务存储 - 管理任务状态和结果的持久化"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .pipeline import PipelineProgress, PipelineResult, PipelineStage


@dataclass
class TaskRecord:
    """任务记录"""
    task_id: str
    status: str
    progress: float
    message: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[PipelineResult] = None


class TaskStore:
    """任务存储管理器

    提供任务状态跟踪和结果存储功能。
    支持任务的创建、更新、查询和清理。
    """

    def __init__(self, max_completed_tasks: int = 100):
        """初始化任务存储

        Args:
            max_completed_tasks: 最大保留已完成任务数量
        """
        self._tasks: Dict[str, TaskRecord] = {}
        self._max_completed = max_completed_tasks
        self._lock = asyncio.Lock()

    async def create_task(self, task_id: str) -> TaskRecord:
        """创建任务记录

        Args:
            task_id: 任务ID

        Returns:
            TaskRecord: 新创建的任务记录
        """
        async with self._lock:
            record = TaskRecord(
                task_id=task_id,
                status=PipelineStage.INITIALIZED.value,
                progress=0.0,
                message="任务已创建",
                created_at=datetime.now(),
            )
            self._tasks[task_id] = record
            logger.debug(f"任务已创建: {task_id}")
            return record

    async def update_progress(
        self,
        task_id: str,
        stage: PipelineStage,
        progress: float,
        message: str,
    ) -> None:
        """更新任务进度

        Args:
            task_id: 任务ID
            stage: 管道阶段
            progress: 进度值 (0.0 - 1.0)
            message: 进度消息
        """
        async with self._lock:
            record = self._tasks.get(task_id)
            if record:
                record.status = stage.value
                record.progress = progress
                record.message = message
                record.updated_at = datetime.now()

    async def complete_task(self, task_id: str, result: PipelineResult) -> None:
        """标记任务完成并存储结果

        Args:
            task_id: 任务ID
            result: 管道处理结果
        """
        async with self._lock:
            record = self._tasks.get(task_id)
            if record:
                record.status = PipelineStage.COMPLETED.value if result.success else PipelineStage.FAILED.value
                record.progress = 1.0
                record.message = "分析完成" if result.success else f"分析失败: {result.error_message}"
                record.completed_at = datetime.now()
                record.updated_at = datetime.now()
                record.result = result
                logger.info(f"任务完成: {task_id}, 成功: {result.success}")

            # 清理旧的已完成任务
            self._cleanup_old_tasks()

    async def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """获取任务记录

        Args:
            task_id: 任务ID

        Returns:
            Optional[TaskRecord]: 任务记录
        """
        return self._tasks.get(task_id)

    async def get_task_result(self, task_id: str) -> Optional[PipelineResult]:
        """获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            Optional[PipelineResult]: 管道处理结果
        """
        record = self._tasks.get(task_id)
        if record and record.result:
            return record.result
        return None

    async def get_active_tasks(self) -> List[TaskRecord]:
        """获取活跃任务列表

        Returns:
            List[TaskRecord]: 活跃任务记录列表
        """
        return [
            record for record in self._tasks.values()
            if record.status not in (PipelineStage.COMPLETED.value, PipelineStage.FAILED.value)
        ]

    async def get_all_tasks(self) -> List[TaskRecord]:
        """获取所有任务列表

        Returns:
            List[TaskRecord]: 所有任务记录列表
        """
        return list(self._tasks.values())

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        async with self._lock:
            record = self._tasks.get(task_id)
            if record and record.status not in (PipelineStage.COMPLETED.value, PipelineStage.FAILED.value):
                record.status = PipelineStage.FAILED.value
                record.message = "任务被用户取消"
                record.completed_at = datetime.now()
                record.updated_at = datetime.now()
                logger.info(f"任务已取消: {task_id}")
                return True
            return False

    def _cleanup_old_tasks(self) -> None:
        """清理旧的已完成任务"""
        completed = [
            (tid, record) for tid, record in self._tasks.items()
            if record.status in (PipelineStage.COMPLETED.value, PipelineStage.FAILED.value)
        ]

        if len(completed) > self._max_completed:
            # 按完成时间排序，删除最早的
            completed.sort(key=lambda x: x[1].completed_at or datetime.min)
            to_remove = len(completed) - self._max_completed
            for tid, _ in completed[:to_remove]:
                del self._tasks[tid]
                logger.debug(f"清理过期任务: {tid}")


# 全局任务存储实例
task_store = TaskStore()
