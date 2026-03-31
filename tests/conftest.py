"""共享测试配置和夹具"""

import os

import pytest

# 设置测试环境变量（在import settings之前）
os.environ.setdefault("ARCHI_ENVIRONMENT", "testing")
os.environ.setdefault("ARCHI_DEBUG", "true")
os.environ.setdefault("ARCHI_MCP__ENABLED", "true")
os.environ.setdefault("ARCHI_MCP__ENDPOINT", "http://localhost:8080/api")
os.environ.setdefault("ARCHI_LLM__API_KEY", "test-key")

from src.collectors.base import AppInfo


@pytest.fixture
def sample_app():
    """单个应用数据夹具"""
    return AppInfo(
        app_id="test-app",
        name="测试应用",
        description="用于测试的应用",
        version="1.0.0",
        language="Java",
        framework="Spring Boot",
        runtime="JDK 17",
        deployment_type="kubernetes",
        environment="production",
        dependencies=["dep-1", "dep-2"],
        databases=["mysql", "redis"],
        services=["service-a"],
    )


@pytest.fixture
def sample_apps():
    """多个应用数据夹具"""
    return [
        AppInfo(
            app_id="user-service",
            name="用户服务",
            language="Java",
            framework="Spring Boot",
            dependencies=["order-service"],
            databases=["mysql"],
        ),
        AppInfo(
            app_id="order-service",
            name="订单服务",
            language="Go",
            framework="Gin",
            dependencies=["payment-service"],
            databases=["mysql", "redis"],
        ),
        AppInfo(
            app_id="payment-service",
            name="支付服务",
            language="Python",
            framework="FastAPI",
            databases=["postgresql"],
        ),
    ]
