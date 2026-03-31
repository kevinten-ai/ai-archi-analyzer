"""管道处理编排器 - 实现数据流处理管道"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from ..collectors.base import AppInfo, CollectorResult
from ..collectors.mcp_collector import MCPCollector
from ..config.settings import settings
from ..processors.data_transformer import DataTransformer
from ..processors.data_validator import DataValidator
from .analyzer import ArchitectureAnalysis, LLMAnalyzer
from .checkpoint import CheckpointManager
from .report_generator import ReportFormat, ReportGenerator


class PipelineStage(Enum):
    """管道阶段枚举"""
    INITIALIZED = "initialized"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineProgress:
    """管道处理进度"""
    task_id: str
    stage: PipelineStage
    progress: float  # 0.0 - 1.0
    message: str
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """管道处理结果"""
    task_id: str
    success: bool
    architecture_analysis: Optional[ArchitectureAnalysis] = None
    report_path: Optional[str] = None
    apps_data: List[AppInfo] = field(default_factory=list)
    aggregate_stats: Optional[Dict[str, Any]] = None
    validation_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    progress_history: List[PipelineProgress] = field(default_factory=list)


class PipelineError(Exception):
    """管道处理错误"""
    pass


# 进度回调类型
ProgressCallback = Callable[[str, PipelineStage, float, str], Any]


class PipelineOrchestrator:
    """架构分析管道编排器

    实现四阶段管道：采集 → 转换/验证 → 分析 → 报告生成
    支持外部进度回调（与TaskStore集成）。
    """

    def __init__(self, progress_callback: Optional[ProgressCallback] = None):
        self.collector = MCPCollector()
        self.analyzer = LLMAnalyzer()
        self.report_generator = ReportGenerator()
        self.transformer = DataTransformer()
        self.validator = DataValidator()
        self.checkpoint = CheckpointManager()
        self._progress_callback = progress_callback

    def generate_task_id(self) -> str:
        """生成任务ID（暴露给调用方以便提前注册）"""
        return str(uuid.uuid4())

    async def analyze_architecture(
        self,
        app_ids: List[str],
        report_format: str = ReportFormat.MARKDOWN,
        task_id: Optional[str] = None,
    ) -> PipelineResult:
        """执行架构分析管道

        Args:
            app_ids: 应用ID列表
            report_format: 报告格式
            task_id: 外部指定的任务ID（可选）

        Returns:
            PipelineResult: 管道处理结果
        """
        task_id = task_id or self.generate_task_id()
        start_time = datetime.now()

        await self._notify_progress(task_id, PipelineStage.INITIALIZED, 0.0,
                                    "初始化架构分析任务")

        try:
            # 阶段1: 数据采集
            await self._notify_progress(task_id, PipelineStage.COLLECTING, 0.1,
                                        "开始采集应用数据")

            apps_data = await self._collect_apps_data(app_ids, task_id)

            # 检查点: 采集完成
            self.checkpoint.save_apps_checkpoint(task_id, "collecting", apps_data)

            # 阶段2: 数据转换和验证
            await self._notify_progress(task_id, PipelineStage.PROCESSING, 0.35,
                                        "转换和验证应用数据")

            processed_data, aggregate_stats, validation_summary = (
                await self._process_apps_data(apps_data, task_id)
            )

            # 检查点: 处理完成
            self.checkpoint.save_apps_checkpoint(task_id, "processing", processed_data)
            self.checkpoint.save_checkpoint(task_id, "processing_stats", {
                "aggregate": aggregate_stats,
                "validation": validation_summary,
            })

            # 阶段3: 架构分析
            await self._notify_progress(task_id, PipelineStage.ANALYZING, 0.6,
                                        "执行架构智能分析")

            analysis = await self.analyzer.analyze_architecture(processed_data)

            # 阶段4: 报告生成
            await self._notify_progress(task_id, PipelineStage.GENERATING_REPORT, 0.9,
                                        "生成分析报告")

            report_path = self.report_generator.save_report(
                analysis, processed_data,
                filename=f"archi_analysis_{task_id}",
                format_type=report_format
            )

            # 完成
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            await self._notify_progress(task_id, PipelineStage.COMPLETED, 1.0,
                                        "架构分析完成")

            return PipelineResult(
                task_id=task_id,
                success=True,
                architecture_analysis=analysis,
                report_path=str(report_path),
                apps_data=processed_data,
                aggregate_stats=aggregate_stats,
                validation_summary=validation_summary,
                processing_time=processing_time,
            )

        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            await self._notify_progress(task_id, PipelineStage.FAILED, 1.0,
                                        f"分析失败: {str(e)}")

            return PipelineResult(
                task_id=task_id,
                success=False,
                error_message=str(e),
                processing_time=processing_time,
            )

    async def _collect_apps_data(
        self,
        app_ids: List[str],
        task_id: str,
    ) -> List[AppInfo]:
        """阶段1: 采集应用数据"""
        apps_data = []

        async with self.collector:
            batch_size = settings.processing.batch_size
            total_batches = max(1, (len(app_ids) + batch_size - 1) // batch_size)

            for i in range(0, len(app_ids), batch_size):
                batch = app_ids[i:i + batch_size]
                batch_num = i // batch_size + 1

                progress = 0.1 + (0.2 * batch_num / total_batches)
                await self._notify_progress(
                    task_id, PipelineStage.COLLECTING, progress,
                    f"采集第{batch_num}/{total_batches}批应用数据"
                )

                batch_results = await self.collector.collect_batch_info(batch)

                for result in batch_results:
                    if result.success and result.app_info:
                        apps_data.append(result.app_info)
                    else:
                        logger.warning(f"采集应用失败: {result.error_message}")

        return apps_data

    async def _process_apps_data(
        self,
        apps_data: List[AppInfo],
        task_id: str,
    ) -> tuple:
        """阶段2: 数据转换和验证

        Returns:
            tuple: (processed_data, aggregate_stats, validation_summary)
        """
        if not apps_data:
            raise PipelineError("没有成功采集到任何应用数据")

        # 步骤2a: 数据转换（清洗、标准化、去重、交叉引用）
        await self._notify_progress(task_id, PipelineStage.PROCESSING, 0.40,
                                    "执行数据转换和清洗")
        transformed_data = self.transformer.transform(apps_data)

        # 步骤2b: 数据聚合统计
        aggregate_stats = self.transformer.aggregate(transformed_data)

        # 步骤2c: 数据验证
        await self._notify_progress(task_id, PipelineStage.PROCESSING, 0.50,
                                    "执行数据验证")
        validation_result = self.validator.validate(transformed_data)
        validation_summary = validation_result.summary()

        # 过滤出有效数据（排除有ERROR的应用）
        valid_data = self.validator.filter_valid(transformed_data, validation_result)

        if not valid_data:
            raise PipelineError("数据验证后没有有效应用数据")

        if validation_result.warnings:
            logger.warning(f"数据验证发现 {len(validation_result.warnings)} 个警告")

        return valid_data, aggregate_stats, validation_summary

    async def _notify_progress(
        self,
        task_id: str,
        stage: PipelineStage,
        progress: float,
        message: str,
    ) -> None:
        """通知进度更新"""
        if self._progress_callback:
            try:
                result = self._progress_callback(task_id, stage, progress, message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"进度回调失败: {e}")



