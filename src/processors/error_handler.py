"""错误处理和稳定性保障"""

import asyncio
import functools
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed
)

from ..config.settings import settings

T = TypeVar('T')


class ArchAnalyzerError(Exception):
    """架构分析器基础异常"""

    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class DataCollectionError(ArchAnalyzerError):
    """数据采集错误"""
    pass


class AnalysisError(ArchAnalyzerError):
    """分析错误"""
    pass


class ReportGenerationError(ArchAnalyzerError):
    """报告生成错误"""
    pass


class ConfigurationError(ArchAnalyzerError):
    """配置错误"""
    pass


class CircuitBreakerOpenError(ArchAnalyzerError):
    """熔断器开启错误"""
    pass


class ErrorHandler:
    """错误处理管理器"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Dict[str, float] = {}
        self.circuit_breakers: Dict[str, bool] = {}

    def handle_error(self, error: Exception, context: str = "unknown") -> ArchAnalyzerError:
        """统一错误处理

        Args:
            error: 原始异常
            context: 错误上下文

        Returns:
            ArchAnalyzerError: 标准化错误
        """
        # 记录错误
        self._record_error(error, context)

        # 转换为标准化错误
        if isinstance(error, ArchAnalyzerError):
            return error
        elif isinstance(error, ConnectionError) or isinstance(error, TimeoutError):
            return DataCollectionError(
                f"连接错误: {str(error)}",
                "CONNECTION_ERROR",
                {"context": context, "original_error": str(error)}
            )
        elif isinstance(error, ValueError):
            return AnalysisError(
                f"数据验证错误: {str(error)}",
                "VALIDATION_ERROR",
                {"context": context, "original_error": str(error)}
            )
        else:
            return ArchAnalyzerError(
                f"未知错误: {str(error)}",
                "UNKNOWN_ERROR",
                {"context": context, "original_error": str(error), "error_type": type(error).__name__}
            )

    def _record_error(self, error: Exception, context: str):
        """记录错误统计"""
        error_type = type(error).__name__
        key = f"{context}:{error_type}"

        # 更新错误计数
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.last_error_time[key] = time.time()

        # 检查是否需要开启熔断器
        if self.error_counts[key] >= 5:  # 连续5次错误
            self.circuit_breakers[key] = True

    def is_circuit_breaker_open(self, context: str, error_type: str = "Exception") -> bool:
        """检查熔断器是否开启"""
        key = f"{context}:{error_type}"
        return self.circuit_breakers.get(key, False)

    def reset_circuit_breaker(self, context: str, error_type: str = "Exception"):
        """重置熔断器"""
        key = f"{context}:{error_type}"
        self.circuit_breakers[key] = False
        self.error_counts[key] = 0

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            "error_counts": self.error_counts.copy(),
            "circuit_breakers": self.circuit_breakers.copy(),
            "last_errors": self.last_error_time.copy()
        }


# 全局错误处理器实例
error_handler = ErrorHandler()


def with_error_handling(
    context: str = "unknown",
    rethrow: bool = True,
    default_value: Any = None
):
    """错误处理装饰器

    Args:
        context: 错误上下文
        rethrow: 是否重新抛出异常
        default_value: 默认返回值（当不重新抛出时）
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                standardized_error = error_handler.handle_error(e, context)
                if rethrow:
                    raise standardized_error from e
                else:
                    return default_value

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                standardized_error = error_handler.handle_error(e, context)
                if rethrow:
                    raise standardized_error from e
                else:
                    return default_value

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_retry(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """重试装饰器

    Args:
        max_attempts: 最大重试次数
        wait_seconds: 初始等待时间
        backoff_multiplier: 退避倍数
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry(
                retry=retry_if_exception_type(exceptions),
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=wait_seconds, max=60),
                reraise=True
            )(func)(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return retry(
                retry=retry_if_exception_type(exceptions),
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=wait_seconds, max=60),
                reraise=True
            )(func)(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_circuit_breaker(context: str = "unknown"):
    """熔断器装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if error_handler.is_circuit_breaker_open(context):
                raise CircuitBreakerOpenError(
                    f"熔断器已开启: {context}",
                    "CIRCUIT_BREAKER_OPEN",
                    {"context": context}
                )

            try:
                result = await func(*args, **kwargs)
                # 成功时重置熔断器
                error_handler.reset_circuit_breaker(context)
                return result
            except Exception as e:
                # 记录错误，但不在这里处理，由with_error_handling处理
                raise e

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if error_handler.is_circuit_breaker_open(context):
                raise CircuitBreakerOpenError(
                    f"熔断器已开启: {context}",
                    "CIRCUIT_BREAKER_OPEN",
                    {"context": context}
                )

            try:
                result = func(*args, **kwargs)
                # 成功时重置熔断器
                error_handler.reset_circuit_breaker(context)
                return result
            except Exception as e:
                # 记录错误，但不在这里处理，由with_error_handling处理
                raise e

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def error_context(context: str = "unknown"):
    """错误上下文管理器"""
    try:
        yield
    except Exception as e:
        standardized_error = error_handler.handle_error(e, context)
        raise standardized_error from e


class ResourceLimiter:
    """资源限制器"""

    def __init__(self, max_concurrent: int = 10, max_queue_size: int = 100):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0

    @asynccontextmanager
    async def limit(self):
        """资源限制上下文管理器"""
        if self.active_count >= self.max_concurrent:
            raise ArchAnalyzerError(
                f"超出最大并发限制: {self.max_concurrent}",
                "RESOURCE_LIMIT_EXCEEDED",
                {"active_count": self.active_count, "max_concurrent": self.max_concurrent}
            )

        async with self.semaphore:
            self.active_count += 1
            try:
                yield
            finally:
                self.active_count -= 1

    def get_stats(self) -> Dict[str, Any]:
        """获取资源使用统计"""
        return {
            "active_count": self.active_count,
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - self.active_count
        }


# 全局资源限制器
resource_limiter = ResourceLimiter(max_concurrent=settings.processing.max_concurrent_apps)



