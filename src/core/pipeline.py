"""管道处理编排器 - 实现数据流处理管道"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from ..collectors.base import AppInfo, CollectorResult
from ..collectors.mcp_collector import MCPCollector
from .analyzer import ArchitectureAnalysis, LLMAnalyzer
from .report_generator import ReportGenerator, ReportFormat
from ..config.settings import settings


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
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    progress_history: List[PipelineProgress] = field(default_factory=list)


class PipelineError(Exception):
    """管道处理错误"""
    pass


class PipelineOrchestrator:
    """架构分析管道编排器"""

    def __init__(self):
        self.collector = MCPCollector()
        self.analyzer = LLMAnalyzer()
        self.report_generator = ReportGenerator()
        self.active_tasks: Dict[str, PipelineProgress] = {}

    async def analyze_architecture(
        self,
        app_ids: List[str],
        report_format: str = ReportFormat.MARKDOWN,
        enable_progress_tracking: bool = True
    ) -> PipelineResult:
        """执行架构分析管道

        Args:
            app_ids: 应用ID列表
            report_format: 报告格式
            enable_progress_tracking: 是否启用进度跟踪

        Returns:
            PipelineResult: 管道处理结果
        """
        task_id = str(uuid.uuid4())
        start_time = datetime.now()

        # 初始化进度
        progress = PipelineProgress(
            task_id=task_id,
            stage=PipelineStage.INITIALIZED,
            progress=0.0,
            message="初始化架构分析任务",
            start_time=start_time
        )

        if enable_progress_tracking:
            self.active_tasks[task_id] = progress

        try:
            # 阶段1: 数据采集
            await self._update_progress(task_id, PipelineStage.COLLECTING, 0.1,
                                       "开始采集应用数据")

            apps_data = await self._collect_apps_data(app_ids, task_id, enable_progress_tracking)

            # 阶段2: 数据处理
            await self._update_progress(task_id, PipelineStage.PROCESSING, 0.4,
                                       "处理和验证应用数据")

            processed_data = await self._process_apps_data(apps_data, task_id)

            # 阶段3: 架构分析
            await self._update_progress(task_id, PipelineStage.ANALYZING, 0.7,
                                       "执行架构智能分析")

            analysis = await self.analyzer.analyze_architecture(processed_data)

            # 阶段4: 报告生成
            await self._update_progress(task_id, PipelineStage.GENERATING_REPORT, 0.9,
                                       "生成分析报告")

            report_path = self.report_generator.save_report(
                analysis, processed_data,
                filename=f"archi_analysis_{task_id}",
                format_type=report_format
            )

            # 完成
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            await self._update_progress(task_id, PipelineStage.COMPLETED, 1.0,
                                       "架构分析完成", end_time=end_time)

            # 构建结果
            result = PipelineResult(
                task_id=task_id,
                success=True,
                architecture_analysis=analysis,
                report_path=str(report_path),
                apps_data=processed_data,
                processing_time=processing_time,
                progress_history=self._get_progress_history(task_id)
            )

            return result

        except Exception as e:
            # 处理失败
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            await self._update_progress(task_id, PipelineStage.FAILED, 1.0,
                                       f"分析失败: {str(e)}", end_time=end_time,
                                       error_message=str(e))

            result = PipelineResult(
                task_id=task_id,
                success=False,
                error_message=str(e),
                processing_time=processing_time,
                progress_history=self._get_progress_history(task_id)
            )

            return result

        finally:
            # 清理任务
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    async def get_task_progress(self, task_id: str) -> Optional[PipelineProgress]:
        """获取任务进度

        Args:
            task_id: 任务ID

        Returns:
            Optional[PipelineProgress]: 进度信息
        """
        return self.active_tasks.get(task_id)

    async def get_task_result(self, task_id: str) -> Optional[PipelineResult]:
        """获取任务结果（如果任务已完成）

        Args:
            task_id: 任务ID

        Returns:
            Optional[PipelineResult]: 任务结果
        """
        # 这里可以实现结果缓存机制
        # 暂时返回None，表示需要等待任务完成
        return None

    async def _collect_apps_data(
        self,
        app_ids: List[str],
        task_id: str,
        enable_progress: bool
    ) -> List[AppInfo]:
        """采集应用数据"""
        apps_data = []

        async with self.collector:
            # 批量采集
            batch_size = settings.processing.batch_size
            total_batches = (len(app_ids) + batch_size - 1) // batch_size

            for i in range(0, len(app_ids), batch_size):
                batch = app_ids[i:i + batch_size]
                batch_num = i // batch_size + 1

                if enable_progress:
                    progress = 0.1 + (0.2 * (batch_num - 1) / total_batches)
                    await self._update_progress(
                        task_id, PipelineStage.COLLECTING, progress,
                        f"采集第{batch_num}/{total_batches}批应用数据"
                    )

                # 采集当前批次
                batch_results = await self.collector.collect_batch_info(batch)

                # 处理结果
                for result in batch_results:
                    if result.success and result.app_info:
                        apps_data.append(result.app_info)
                    else:
                        # 记录采集失败的应用，但不中断整个流程
                        print(f"采集应用失败: {result.error_message}")

        return apps_data

    async def _process_apps_data(
        self,
        apps_data: List[AppInfo],
        task_id: str
    ) -> List[AppInfo]:
        """处理应用数据"""
        if not apps_data:
            raise PipelineError("没有成功采集到任何应用数据")

        # 数据验证和清洗
        processed_data = []
        for app in apps_data:
            try:
                # 验证必要字段
                if not app.app_id:
                    continue

                # 数据清洗
                cleaned_app = self._clean_app_data(app)
                processed_data.append(cleaned_app)

            except Exception as e:
                print(f"处理应用 {app.app_id} 数据失败: {str(e)}")
                continue

        if not processed_data:
            raise PipelineError("数据处理后没有有效应用数据")

        return processed_data

    def _clean_app_data(self, app: AppInfo) -> AppInfo:
        """清洗应用数据"""
        # 清理空值
        cleaned_data = app.model_dump()

        # 清理字符串字段的空白字符
        for field in ['name', 'description', 'language', 'framework']:
            if cleaned_data.get(field):
                cleaned_data[field] = cleaned_data[field].strip()

        # 确保列表字段不为空
        for field in ['dependencies', 'databases', 'services']:
            if not cleaned_data.get(field):
                cleaned_data[field] = []

        # 清理字典字段
        for field in ['config', 'metadata']:
            if not cleaned_data.get(field):
                cleaned_data[field] = {}

        return AppInfo(**cleaned_data)

    async def _update_progress(
        self,
        task_id: str,
        stage: PipelineStage,
        progress: float,
        message: str,
        end_time: Optional[datetime] = None,
        error_message: Optional[str] = None
    ):
        """更新任务进度"""
        if task_id in self.active_tasks:
            progress_info = self.active_tasks[task_id]
            progress_info.stage = stage
            progress_info.progress = progress
            progress_info.message = message
            if end_time:
                progress_info.end_time = end_time
            if error_message:
                progress_info.error_message = error_message

            # 可以在这里添加进度持久化逻辑
            # await self._persist_progress(progress_info)

    def _get_progress_history(self, task_id: str) -> List[PipelineProgress]:
        """获取进度历史（简化实现）"""
        # 这里可以从持久化存储中获取完整历史
        # 暂时返回空列表
        return []

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否成功取消
        """
        if task_id in self.active_tasks:
            progress = self.active_tasks[task_id]
            progress.stage = PipelineStage.FAILED
            progress.error_message = "任务被用户取消"
            progress.end_time = datetime.now()
            del self.active_tasks[task_id]
            return True
        return False

    async def get_active_tasks(self) -> List[PipelineProgress]:
        """获取活跃任务列表

        Returns:
            List[PipelineProgress]: 活跃任务列表
        """
        return list(self.active_tasks.values())



