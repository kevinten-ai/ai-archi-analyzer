"""管道处理测试"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.pipeline import PipelineOrchestrator, PipelineStage, PipelineError
from src.collectors.base import AppInfo


class TestPipelineOrchestrator:
    """管道编排器测试"""

    @pytest.fixture
    def orchestrator(self):
        """测试夹具：创建管道编排器"""
        return PipelineOrchestrator()

    @pytest.fixture
    def mock_apps(self):
        """测试夹具：模拟应用数据"""
        return [
            AppInfo(app_id="app1", name="应用1", language="Java", framework="Spring Boot"),
            AppInfo(app_id="app2", name="应用2", language="Go", framework="Gin"),
            AppInfo(app_id="app3", name="应用3", language="Python", framework="FastAPI"),
        ]

    @pytest.mark.asyncio
    async def test_analyze_architecture_success(self, orchestrator, mock_apps):
        """测试成功执行架构分析"""
        app_ids = ["app1", "app2", "app3"]

        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect, \
             patch.object(orchestrator.analyzer, 'analyze_architecture') as mock_analyze, \
             patch.object(orchestrator.report_generator, 'save_report') as mock_save:

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

            result = await orchestrator.analyze_architecture(app_ids)

            assert result.success is True
            assert result.task_id is not None
            assert result.architecture_analysis is not None
            assert result.report_path == "/path/to/report.md"
            assert len(result.apps_data) == 3
            assert result.aggregate_stats is not None
            assert result.validation_summary is not None

    @pytest.mark.asyncio
    async def test_analyze_architecture_with_collection_failure(self, orchestrator):
        """测试数据采集部分失败的情况"""
        app_ids = ["app1", "app2"]

        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect, \
             patch.object(orchestrator.analyzer, 'analyze_architecture') as mock_analyze, \
             patch.object(orchestrator.report_generator, 'save_report') as mock_save:

            mock_collect.return_value = [
                MagicMock(success=False, app_info=None, error_message="采集失败"),
                MagicMock(
                    success=True,
                    app_info=AppInfo(app_id="app2", name="应用2", language="Java"),
                    error_message=None
                ),
            ]
            mock_analyze.return_value = MagicMock(
                architecture_type="单体架构",
                quality_score=6.0,
                summary="测试"
            )
            mock_save.return_value = "/path/to/report.md"

            result = await orchestrator.analyze_architecture(app_ids)

            assert result.success is True
            assert len(result.apps_data) == 1
            assert result.apps_data[0].app_id == "app2"

    @pytest.mark.asyncio
    async def test_analyze_architecture_empty_apps(self, orchestrator):
        """测试空应用列表"""
        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect:
            mock_collect.return_value = []

            result = await orchestrator.analyze_architecture([])

            assert result.success is False
            assert "没有成功采集到任何应用数据" in result.error_message

    @pytest.mark.asyncio
    async def test_analyze_with_custom_task_id(self, orchestrator, mock_apps):
        """测试使用自定义任务ID"""
        custom_id = "custom-task-123"

        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect, \
             patch.object(orchestrator.analyzer, 'analyze_architecture') as mock_analyze, \
             patch.object(orchestrator.report_generator, 'save_report') as mock_save:

            mock_collect.return_value = [
                MagicMock(success=True, app_info=mock_apps[0], error_message=None)
            ]
            mock_analyze.return_value = MagicMock(
                architecture_type="微服务架构",
                quality_score=7.0,
                summary="测试"
            )
            mock_save.return_value = "/path/to/report.md"

            result = await orchestrator.analyze_architecture(
                ["app1"], task_id=custom_id
            )

            assert result.task_id == custom_id

    @pytest.mark.asyncio
    async def test_progress_callback(self, mock_apps):
        """测试进度回调"""
        progress_updates = []

        async def on_progress(task_id, stage, progress, message):
            progress_updates.append((stage, progress, message))

        orchestrator = PipelineOrchestrator(progress_callback=on_progress)

        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect, \
             patch.object(orchestrator.analyzer, 'analyze_architecture') as mock_analyze, \
             patch.object(orchestrator.report_generator, 'save_report') as mock_save:

            mock_collect.return_value = [
                MagicMock(success=True, app_info=mock_apps[0], error_message=None)
            ]
            mock_analyze.return_value = MagicMock(
                architecture_type="微服务架构",
                quality_score=7.0,
                summary="测试"
            )
            mock_save.return_value = "/path/to/report.md"

            await orchestrator.analyze_architecture(["app1"])

        # 验证进度回调被调用了多次
        assert len(progress_updates) > 0
        stages = [p[0] for p in progress_updates]
        assert PipelineStage.INITIALIZED in stages
        assert PipelineStage.COLLECTING in stages
        assert PipelineStage.PROCESSING in stages
        assert PipelineStage.ANALYZING in stages
        assert PipelineStage.COMPLETED in stages

    def test_generate_task_id(self, orchestrator):
        """测试任务ID生成"""
        id1 = orchestrator.generate_task_id()
        id2 = orchestrator.generate_task_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID格式


class TestPipelineProgress:
    """管道进度测试"""

    def test_pipeline_stage_enum(self):
        """测试管道阶段枚举"""
        assert PipelineStage.INITIALIZED.value == "initialized"
        assert PipelineStage.COLLECTING.value == "collecting"
        assert PipelineStage.PROCESSING.value == "processing"
        assert PipelineStage.ANALYZING.value == "analyzing"
        assert PipelineStage.GENERATING_REPORT.value == "generating_report"
        assert PipelineStage.COMPLETED.value == "completed"
        assert PipelineStage.FAILED.value == "failed"
