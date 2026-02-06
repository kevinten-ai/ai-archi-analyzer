"""API数据模型"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ArchitectureAnalysisRequest(BaseModel):
    """架构分析请求"""

    app_ids: List[str] = Field(..., min_length=1, description="应用ID列表")
    report_format: str = Field(default="markdown", description="报告格式")
    enable_progress_tracking: bool = Field(default=True, description="启用进度跟踪")

    @field_validator("report_format")
    @classmethod
    def validate_report_format(cls, v: str) -> str:
        valid_formats = ["markdown", "json", "html"]
        if v not in valid_formats:
            raise ValueError(f"不支持的报告格式: {v}，支持: {valid_formats}")
        return v

    @field_validator("app_ids")
    @classmethod
    def validate_app_ids(cls, v: List[str]) -> List[str]:
        if len(v) > 100:  # 限制最大应用数量
            raise ValueError("应用数量不能超过100个")
        return v


class TaskStatus(BaseModel):
    """任务状态"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="进度百分比")
    message: str = Field(default="", description="状态消息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


class ArchitectureAnalysisResponse(BaseModel):
    """架构分析响应"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(default="", description="响应消息")


class TaskResultResponse(BaseModel):
    """任务结果响应"""

    task_id: str = Field(..., description="任务ID")
    success: bool = Field(..., description="是否成功")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    processing_time: Optional[float] = Field(default=None, description="处理时间(秒)")
    report_url: Optional[str] = Field(default=None, description="报告下载URL")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    # 架构分析结果摘要
    architecture_summary: Optional[dict] = Field(default=None, description="架构分析摘要")
    total_apps: Optional[int] = Field(default=None, description="应用总数")
    quality_score: Optional[float] = Field(default=None, description="质量评分")


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(default=None, description="错误详情")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    components: dict = Field(default_factory=dict, description="组件状态")



