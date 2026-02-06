"""MCP数据采集器实现"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config.settings import settings
from .base import AppInfo, BaseDataCollector, CollectorResult


class MCPClientError(Exception):
    """MCP客户端错误"""
    pass


class MCPCollector(BaseDataCollector):
    """MCP数据采集器

    通过MCP协议从远程服务获取应用信息。
    预留接口设计，支持后续具体实现。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 从配置获取MCP设置
        mcp_config = settings.mcp

        self.endpoint = self.config.get("endpoint") or mcp_config.endpoint
        self.timeout = self.config.get("timeout", mcp_config.timeout)
        self.retry_attempts = self.config.get("retry_attempts", mcp_config.retry_attempts)
        self.retry_delay = self.config.get("retry_delay", mcp_config.retry_delay)

        # HTTP客户端
        self.client: Optional[httpx.AsyncClient] = None

        # 验证配置
        if not self.endpoint:
            raise ValueError("MCP endpoint must be configured")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_client()

    async def _init_client(self):
        """初始化HTTP客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ai-archi-analyzer/1.0"
                }
            )

    async def _close_client(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求（带重试机制）

        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Dict[str, Any]: 响应数据

        Raises:
            MCPClientError: 请求失败时抛出
        """
        if not self.client:
            await self._init_client()

        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()

            # 假设MCP服务返回JSON格式
            return response.json()

        except httpx.HTTPStatusError as e:
            raise MCPClientError(f"MCP服务返回错误状态码: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise MCPClientError(f"MCP服务请求失败: {str(e)}") from e
        except Exception as e:
            raise MCPClientError(f"MCP服务调用异常: {str(e)}") from e

    async def collect_app_info(self, app_id: str) -> CollectorResult:
        """采集单个应用信息

        Args:
            app_id: 应用ID

        Returns:
            CollectorResult: 采集结果
        """
        try:
            # 预留：调用MCP服务的应用信息接口
            # TODO: 根据实际MCP协议实现具体调用逻辑
            url = f"{self.endpoint}/api/v1/apps/{app_id}"

            # 模拟MCP调用（实际实现时替换为真实调用）
            app_data = await self._mock_mcp_call(app_id)

            # 转换为AppInfo对象
            app_info = self._parse_app_data(app_id, app_data)

            return self._create_success_result(app_info)

        except MCPClientError as e:
            return self._create_error_result(app_id, str(e))
        except Exception as e:
            return self._create_error_result(app_id, f"采集失败: {str(e)}")

    async def collect_batch_info(self, app_ids: List[str]) -> List[CollectorResult]:
        """批量采集应用信息

        Args:
            app_ids: 应用ID列表

        Returns:
            List[CollectorResult]: 采集结果列表
        """
        # 并发采集，控制并发数量
        semaphore = asyncio.Semaphore(settings.processing.max_concurrent_apps)

        async def _collect_with_semaphore(app_id: str) -> CollectorResult:
            async with semaphore:
                return await self.collect_app_info(app_id)

        # 创建并发任务
        tasks = [_collect_with_semaphore(app_id) for app_id in app_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 任务执行异常
                app_id = app_ids[i]
                final_results.append(
                    self._create_error_result(app_id, f"并发采集失败: {str(result)}")
                )
            else:
                final_results.append(result)

        return final_results

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 是否健康
        """
        try:
            # 调用MCP健康检查接口
            url = f"{self.endpoint}/health"
            await self._make_request("GET", url)
            return True
        except Exception:
            return False

    async def pre_collect(self) -> None:
        """采集前的准备工作"""
        # 初始化连接
        await self._init_client()

        # 健康检查
        if not await self.health_check():
            raise MCPClientError("MCP服务健康检查失败")

    async def post_collect(self) -> None:
        """采集后的清理工作"""
        await self._close_client()

    async def _mock_mcp_call(self, app_id: str) -> Dict[str, Any]:
        """模拟MCP调用（开发阶段使用）

        Args:
            app_id: 应用ID

        Returns:
            Dict[str, Any]: 模拟的应用数据
        """
        # 模拟网络延迟
        await asyncio.sleep(0.1)

        # 返回模拟数据
        return {
            "app_id": app_id,
            "name": f"应用{app_id}",
            "description": f"这是{app_id}应用的描述信息",
            "version": "1.0.0",
            "language": "Java",
            "framework": "Spring Boot",
            "runtime": "JDK 17",
            "deployment_type": "kubernetes",
            "environment": "production",
            "cluster": "prod-cluster",
            "dependencies": [f"app-{i}" for i in range(1, 4)],
            "databases": ["mysql", "redis"],
            "services": ["service-a", "service-b"],
            "config": {
                "port": 8080,
                "env": "prod"
            },
            "metadata": {
                "team": "backend-team",
                "created_at": "2024-01-01"
            }
        }

    def _parse_app_data(self, app_id: str, data: Dict[str, Any]) -> AppInfo:
        """解析应用数据

        Args:
            app_id: 应用ID
            data: MCP返回的数据

        Returns:
            AppInfo: 解析后的应用信息
        """
        try:
            # 直接映射字段（根据实际MCP数据格式调整）
            app_info = AppInfo(
                app_id=app_id,
                name=data.get("name", ""),
                description=data.get("description"),
                version=data.get("version"),
                language=data.get("language"),
                framework=data.get("framework"),
                runtime=data.get("runtime"),
                deployment_type=data.get("deployment_type"),
                environment=data.get("environment"),
                cluster=data.get("cluster"),
                dependencies=data.get("dependencies", []),
                databases=data.get("databases", []),
                services=data.get("services", []),
                config=data.get("config", {}),
                metadata=data.get("metadata", {}),
            )

            return app_info

        except Exception as e:
            raise ValueError(f"解析应用数据失败: {str(e)}") from e



