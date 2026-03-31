"""任务存储测试"""

import pytest

from src.core.pipeline import PipelineResult, PipelineStage
from src.core.task_store import TaskStore


class TestTaskStore:
    """TaskStore 测试"""

    @pytest.fixture
    def store(self):
        return TaskStore(max_completed_tasks=5)

    @pytest.mark.asyncio
    async def test_create_and_get_task(self, store):
        """测试创建和获取任务"""
        record = await store.create_task("task-1")
        assert record.task_id == "task-1"
        assert record.status == PipelineStage.INITIALIZED.value

        fetched = await store.get_task("task-1")
        assert fetched is not None
        assert fetched.task_id == "task-1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, store):
        """测试获取不存在的任务"""
        result = await store.get_task("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_progress(self, store):
        """测试更新任务进度"""
        await store.create_task("task-1")
        await store.update_progress("task-1", PipelineStage.COLLECTING, 0.3, "采集中")

        record = await store.get_task("task-1")
        assert record.status == PipelineStage.COLLECTING.value
        assert record.progress == 0.3
        assert record.message == "采集中"

    @pytest.mark.asyncio
    async def test_complete_task(self, store):
        """测试完成任务"""
        await store.create_task("task-1")

        result = PipelineResult(task_id="task-1", success=True, processing_time=10.5)
        await store.complete_task("task-1", result)

        record = await store.get_task("task-1")
        assert record.status == PipelineStage.COMPLETED.value
        assert record.result is not None
        assert record.result.success is True
        assert record.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_failed_task(self, store):
        """测试完成失败的任务"""
        await store.create_task("task-1")

        result = PipelineResult(task_id="task-1", success=False, error_message="出错了")
        await store.complete_task("task-1", result)

        record = await store.get_task("task-1")
        assert record.status == PipelineStage.FAILED.value

    @pytest.mark.asyncio
    async def test_get_task_result(self, store):
        """测试获取任务结果"""
        await store.create_task("task-1")
        result = PipelineResult(task_id="task-1", success=True)
        await store.complete_task("task-1", result)

        fetched_result = await store.get_task_result("task-1")
        assert fetched_result is not None
        assert fetched_result.success is True

    @pytest.mark.asyncio
    async def test_get_task_result_not_completed(self, store):
        """测试获取未完成任务的结果"""
        await store.create_task("task-1")
        result = await store.get_task_result("task-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_task(self, store):
        """测试取消任务"""
        await store.create_task("task-1")
        success = await store.cancel_task("task-1")
        assert success is True

        record = await store.get_task("task-1")
        assert record.status == PipelineStage.FAILED.value
        assert "取消" in record.message

    @pytest.mark.asyncio
    async def test_cancel_completed_task(self, store):
        """测试取消已完成的任务"""
        await store.create_task("task-1")
        result = PipelineResult(task_id="task-1", success=True)
        await store.complete_task("task-1", result)

        success = await store.cancel_task("task-1")
        assert success is False  # 已完成的任务不能取消

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, store):
        """测试取消不存在的任务"""
        success = await store.cancel_task("nonexistent")
        assert success is False

    @pytest.mark.asyncio
    async def test_get_active_tasks(self, store):
        """测试获取活跃任务"""
        await store.create_task("task-1")
        await store.create_task("task-2")

        # 完成task-1
        result = PipelineResult(task_id="task-1", success=True)
        await store.complete_task("task-1", result)

        active = await store.get_active_tasks()
        assert len(active) == 1
        assert active[0].task_id == "task-2"

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, store):
        """测试获取所有任务"""
        await store.create_task("task-1")
        await store.create_task("task-2")

        all_tasks = await store.get_all_tasks()
        assert len(all_tasks) == 2

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(self, store):
        """测试过期任务清理"""
        # 创建超过max_completed_tasks(5)个已完成任务
        for i in range(7):
            tid = f"task-{i}"
            await store.create_task(tid)
            result = PipelineResult(task_id=tid, success=True)
            await store.complete_task(tid, result)

        all_tasks = await store.get_all_tasks()
        # 应该只保留最新的5个
        assert len(all_tasks) <= 5
