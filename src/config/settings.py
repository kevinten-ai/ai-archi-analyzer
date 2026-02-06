"""配置管理器 - 分层配置系统"""

import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM配置"""

    provider: str = Field(default="openai", description="LLM提供商")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: Optional[str] = Field(default=None, description="API基础URL")
    model: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=4000, gt=0, description="最大token数")
    timeout: int = Field(default=60, gt=0, description="请求超时时间(秒)")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        valid_providers = ["openai", "anthropic", "azure", "local"]
        if v not in valid_providers:
            raise ValueError(f"不支持的LLM提供商: {v}，支持: {valid_providers}")
        return v


class MCPConfig(BaseSettings):
    """MCP客户端配置"""

    enabled: bool = Field(default=False, description="是否启用MCP客户端")
    endpoint: Optional[str] = Field(default=None, description="MCP服务端点")
    timeout: int = Field(default=30, gt=0, description="MCP请求超时时间(秒)")
    retry_attempts: int = Field(default=3, ge=0, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, description="重试延迟(秒)")


class ProcessingConfig(BaseSettings):
    """处理配置"""

    max_concurrent_apps: int = Field(default=10, gt=0, description="最大并发应用数")
    batch_size: int = Field(default=5, gt=0, description="批处理大小")
    enable_progress_tracking: bool = Field(default=True, description="启用进度跟踪")
    output_dir: str = Field(default="./output", description="输出目录")
    cache_dir: str = Field(default="./cache", description="缓存目录")


class APIConfig(BaseSettings):
    """API服务配置"""

    host: str = Field(default="0.0.0.0", description="服务主机")
    port: int = Field(default=8000, gt=0, lt=65536, description="服务端口")
    workers: int = Field(default=1, gt=0, description="工作进程数")
    reload: bool = Field(default=False, description="开发模式自动重载")
    cors_origins: List[str] = Field(default=["*"], description="CORS允许的源")


class LoggingConfig(BaseSettings):
    """日志配置"""

    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        description="日志格式"
    )
    file_path: Optional[str] = Field(default=None, description="日志文件路径")
    max_file_size: str = Field(default="10 MB", description="最大文件大小")
    retention: str = Field(default="7 days", description="日志保留时间")


class Settings(BaseSettings):
    """全局配置"""

    # 环境配置
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")

    # 子配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        """Pydantic配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"

        # 环境变量前缀
        env_prefix = "ARCHI_"

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "testing", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"无效的环境: {v}，支持: {valid_envs}")
        return v

    def setup_logging(self) -> None:
        """配置日志系统"""
        import logging
        from pathlib import Path

        # 创建日志目录
        if self.logging.file_path:
            log_path = Path(self.logging.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        # 配置标准库日志
        logging.basicConfig(
            level=getattr(logging, self.logging.level.upper()),
            format=self.logging.format,
            filename=self.logging.file_path,
            filemode="a" if self.logging.file_path else None,
        )

    def ensure_directories(self) -> None:
        """确保必要的目录存在"""
        from pathlib import Path

        Path(self.processing.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.processing.cache_dir).mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()

# 开发环境下的便捷访问
if settings.debug:
    print(f"配置加载完成 - 环境: {settings.environment}")
    print(f"调试模式: {settings.debug}")
    print(f"LLM提供商: {settings.llm.provider}")
    if settings.mcp.enabled:
        print(f"MCP端点: {settings.mcp.endpoint}")



