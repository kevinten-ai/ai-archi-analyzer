"""管道处理测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.pipeline import PipelineOrchestrator, PipelineStage
from src.collectors.base import AppInfo


class TestPipelineOrchestrator:
    """管道编排器测试"""

    @pytest.fixture
    def orchestrator(self):
        """测试夹具：创建管道编排器"""
        return PipelineOrchestrator()

    @pytest.mark.asyncio
    async def test_analyze_architecture_success(self, orchestrator):
        """测试成功执行架构分析"""
        # 模拟应用ID列表
        app_ids = ["app1", "app2", "app3"]

        # 模拟应用数据
        mock_apps = [
            AppInfo(app_id="app1", name="应用1"),
            AppInfo(app_id="app2", name="应用2"),
            AppInfo(app_id="app3", name="应用3")
        ]

        # Mock 各个组件
        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect, \
             patch.object(orchestrator.analyzer, 'analyze_architecture') as mock_analyze, \
             patch.object(orchestrator.report_generator, 'save_report') as mock_save:

            # 设置Mock返回值
            mock_collect.return_value = [
                MagicMock(success=True, app_info=app, error_message=None)
                for app in mock_apps
            ]
            mock_analyze.return_value = MagicMock(
                architecture_type="微服务架构",
                quality_score=8.5,
                summary="测试架构摘要"
            )
            mock_save.return_value = "/path/to/report.md"

            # 执行测试
            result = await orchestrator.analyze_architecture(app_ids)

            # 验证结果
            assert result.success is True
            assert result.task_id is not None
            assert result.architecture_analysis is not None
            assert result.report_path == "/path/to/report.md"
            assert len(result.apps_data) == 3

    @pytest.mark.asyncio
    async def test_analyze_architecture_with_collection_failure(self, orchestrator):
        """测试数据采集失败的情况"""
        app_ids = ["app1", "app2"]

        # Mock 数据采集失败
        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect:
            mock_collect.return_value = [
                MagicMock(success=False, app_info=None, error_message="采集失败"),
                MagicMock(success=True, app_info=AppInfo(app_id="app2", name="应用2"), error_message=None)
            ]

            # 执行测试
            result = await orchestrator.analyze_architecture(app_ids)

            # 验证结果：应该只包含成功的应用
            assert result.success is True
            assert len(result.apps_data) == 1
            assert result.apps_data[0].app_id == "app2"

    @pytest.mark.asyncio
    async def test_analyze_architecture_empty_apps(self, orchestrator):
        """测试空应用列表"""
        app_ids = []

        result = await orchestrator.analyze_architecture(app_ids)

        assert result.success is False
        assert "没有成功采集到任何应用数据" in result.error_message

    @pytest.mark.asyncio
    async def test_get_task_progress(self, orchestrator):
        """测试获取任务进度"""
        # 先创建一个任务
        app_ids = ["app1"]
        task = asyncio.create_task(orchestrator.analyze_architecture(app_ids))

        # 等待一小段时间确保任务开始
        await asyncio.sleep(0.1)

        # 这里需要改进：实际应该从任务中获取task_id
        # 暂时跳过这个测试，因为当前实现中task_id是内部生成的

    @pytest.mark.asyncio
    async def test_cancel_task(self, orchestrator):
        """测试取消任务"""
        # 创建一个长时间运行的任务
        app_ids = ["app1", "app2", "app3"] * 10  # 很多应用，模拟长时间任务

        # 这里需要实际的任务ID，暂时跳过
        success = await orchestrator.cancel_task("nonexistent-task")
        assert success is False


class TestPipelineProgress:
    """管道进度测试"""

    def test_pipeline_stage_enum(self):
        """测试管道阶段枚举"""
        assert PipelineStage.INITIALIZED.value == "initialized"
        assert PipelineStage.COLLECTING.value == "collecting"
        assert PipelineStage.ANALYZING.value == "analyzing"
        assert PipelineStage.GENERATING_REPORT.value == "generating_report"
        assert PipelineStage.COMPLETED.value == "completed"
        assert PipelineStage.FAILED.value == "failed"



