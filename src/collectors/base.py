"""数据采集器基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field


class AppInfo(BaseModel):
    """应用信息数据模型"""

    app_id: str = Field(..., description="应用ID")
    name: str = Field(default="", description="应用名称")
    description: Optional[str] = Field(default=None, description="应用描述")
    version: Optional[str] = Field(default=None, description="版本信息")

    # 技术栈信息
    language: Optional[str] = Field(default=None, description="编程语言")
    framework: Optional[str] = Field(default=None, description="框架")
    runtime: Optional[str] = Field(default=None, description="运行时")

    # 部署信息
    deployment_type: Optional[str] = Field(default=None, description="部署类型")
    environment: Optional[str] = Field(default=None, description="部署环境")
    cluster: Optional[str] = Field(default=None, description="集群信息")

    # 依赖关系
    dependencies: List[str] = Field(default_factory=list, description="依赖的应用ID列表")
    databases: List[str] = Field(default_factory=list, description="使用的数据库")
    services: List[str] = Field(default_factory=list, description="调用的服务")

    # 配置信息
    config: Dict[str, Any] = Field(default_factory=dict, description="配置信息")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    collected_at: Optional[str] = Field(default=None, description="采集时间")


class CollectorResult(BaseModel):
    """采集结果"""

    success: bool = Field(default=True, description="是否成功")
    app_info: Optional[AppInfo] = Field(default=None, description="应用信息")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="结果元数据")


class DataCollectorProtocol(Protocol):
    """数据采集器协议"""

    async def collect_app_info(self, app_id: str) -> CollectorResult:
        """采集单个应用信息"""
        ...

    async def collect_batch_info(self, app_ids: List[str]) -> List[CollectorResult]:
        """批量采集应用信息"""
        ...


class BaseDataCollector(ABC):
    """数据采集器基类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    async def collect_app_info(self, app_id: str) -> CollectorResult:
        """采集单个应用信息

        Args:
            app_id: 应用ID

        Returns:
            CollectorResult: 采集结果
        """
        pass

    @abstractmethod
    async def collect_batch_info(self, app_ids: List[str]) -> List[CollectorResult]:
        """批量采集应用信息

        Args:
            app_ids: 应用ID列表

        Returns:
            List[CollectorResult]: 采集结果列表
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 是否健康
        """
        pass

    async def pre_collect(self) -> None:
        """采集前的准备工作"""
        pass

    async def post_collect(self) -> None:
        """采集后的清理工作"""
        pass

    def _create_error_result(self, app_id: str, error_message: str) -> CollectorResult:
        """创建错误结果"""
        return CollectorResult(
            success=False,
            app_info=None,
            error_message=error_message,
            metadata={
                "app_id": app_id,
                "collector": self.name,
                "error_type": "collection_error"
            }
        )

    def _create_success_result(self, app_info: AppInfo) -> CollectorResult:
        """创建成功结果"""
        return CollectorResult(
            success=True,
            app_info=app_info,
            error_message=None,
            metadata={
                "app_id": app_info.app_id,
                "collector": self.name,
                "collected_fields": list(app_info.model_dump().keys())
            }
        )



