# 使用示例

本文档提供AI Architecture Analyzer的完整使用示例。

## 🚀 快速开始示例

### 1. 基础架构分析

```python
import asyncio
from src.core.pipeline import PipelineOrchestrator

async def basic_analysis():
    """基础架构分析示例"""
    # 创建管道编排器
    orchestrator = PipelineOrchestrator()

    # 定义要分析的应用ID列表
    app_ids = [
        "user-service",
        "order-service",
        "payment-service",
        "inventory-service"
    ]

    # 执行架构分析
    result = await orchestrator.analyze_architecture(
        app_ids=app_ids,
        report_format="markdown",
        enable_progress_tracking=True
    )

    if result.success:
        print(f"分析完成！报告已保存至: {result.report_path}")
        print(f"处理时间: {result.processing_time:.2f}秒")
        print(f"架构类型: {result.architecture_analysis.architecture_type}")
        print(f"质量评分: {result.architecture_analysis.quality_score}/10")
    else:
        print(f"分析失败: {result.error_message}")

# 运行示例
asyncio.run(basic_analysis())
```

### 2. 使用API接口

```python
import requests
import time

def api_analysis_example():
    """API调用示例"""
    base_url = "http://localhost:8000"

    # 1. 提交分析任务
    response = requests.post(
        f"{base_url}/api/analyze",
        json={
            "app_ids": ["web-app", "api-gateway", "database", "cache"],
            "report_format": "markdown",
            "enable_progress_tracking": True
        }
    )

    if response.status_code != 200:
        print("提交任务失败")
        return

    task_id = response.json()["task_id"]
    print(f"任务已提交，ID: {task_id}")

    # 2. 轮询任务状态
    while True:
        status_response = requests.get(f"{base_url}/api/tasks/{task_id}/status")

        if status_response.status_code != 200:
            print("获取状态失败")
            break

        status_data = status_response.json()
        progress = status_data["progress"] * 100

        print(f"进度: {progress:.1f}% - {status_data['message']}")

        if status_data["status"] in ["completed", "failed"]:
            break

        time.sleep(2)  # 等待2秒后再次检查

    # 3. 获取分析结果
    result_response = requests.get(f"{base_url}/api/tasks/{task_id}/result")

    if result_response.status_code == 200:
        result = result_response.json()
        if result["success"]:
            print("分析成功！")
            print(f"应用数量: {result['total_apps']}")
            print(f"质量评分: {result['quality_score']}")
        else:
            print(f"分析失败: {result['error_message']}")

# 运行示例
api_analysis_example()
```

## 📊 高级用法示例

### 1. 批量分析大规模系统

```python
import asyncio
from src.core.pipeline import PipelineOrchestrator

async def large_scale_analysis():
    """大规模系统分析示例"""
    orchestrator = PipelineOrchestrator()

    # 模拟大规模系统（100个应用）
    app_ids = [f"service-{i:03d}" for i in range(1, 101)]

    print(f"开始分析 {len(app_ids)} 个应用...")

    # 执行分析
    result = await orchestrator.analyze_architecture(
        app_ids=app_ids,
        report_format="json",  # 使用JSON格式便于程序处理
        enable_progress_tracking=True
    )

    if result.success:
        print("大规模分析完成！")
        print(f"总应用数: {len(result.apps_data)}")
        print(f"架构质量评分: {result.architecture_analysis.quality_score}")

        # 分析技术栈分布
        tech_stats = analyze_tech_stack(result.apps_data)
        print("技术栈统计:")
        for tech, count in tech_stats.items():
            print(f"  {tech}: {count} 个应用")

def analyze_tech_stack(apps_data):
    """分析技术栈分布"""
    tech_stats = {}
    for app in apps_data:
        tech = app.language or "Unknown"
        tech_stats[tech] = tech_stats.get(tech, 0) + 1
    return tech_stats

asyncio.run(large_scale_analysis())
```

### 2. 自定义分析配置

```python
import asyncio
from src.core.pipeline import PipelineOrchestrator
from src.config.settings import settings

async def custom_analysis():
    """自定义配置分析示例"""

    # 修改配置（示例）
    settings.processing.max_concurrent_apps = 5  # 降低并发度
    settings.processing.batch_size = 3  # 减小批处理大小
    settings.llm.temperature = 0.3  # 降低创造性，提高确定性

    orchestrator = PipelineOrchestrator()

    app_ids = ["critical-service-1", "critical-service-2"]

    result = await orchestrator.analyze_architecture(
        app_ids=app_ids,
        report_format="markdown"
    )

    print(f"自定义配置分析完成: {result.success}")

asyncio.run(custom_analysis())
```

### 3. 错误处理和重试

```python
import asyncio
from src.core.pipeline import PipelineOrchestrator
from src.processors.error_handler import with_error_handling, ArchAnalyzerError

async def error_handling_example():
    """错误处理示例"""
    orchestrator = PipelineOrchestrator()

    @with_error_handling(context="analysis_example", rethrow=False, default_value=None)
    async def safe_analysis(app_ids):
        """带错误处理的分析函数"""
        return await orchestrator.analyze_architecture(app_ids)

    # 测试不同场景
    test_cases = [
        ["valid-app-1", "valid-app-2"],  # 正常情况
        [],  # 空列表
        ["nonexistent-app"] * 100,  # 大量不存在的应用
    ]

    for i, app_ids in enumerate(test_cases, 1):
        print(f"\n=== 测试用例 {i} ===")
        print(f"应用ID: {app_ids[:3]}{'...' if len(app_ids) > 3 else ''}")

        result = await safe_analysis(app_ids)

        if result and result.success:
            print(f"✅ 成功: {len(result.apps_data)} 个应用已分析")
        else:
            print(f"❌ 失败: {result.error_message if result else '未知错误'}")

asyncio.run(error_handling_example())
```

## 🧪 测试示例

### 1. 单元测试

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.core.pipeline import PipelineOrchestrator

class TestArchitectureAnalysis:
    """架构分析测试"""

    @pytest.fixture
    async def orchestrator(self):
        """测试夹具"""
        return PipelineOrchestrator()

    @pytest.mark.asyncio
    async def test_successful_analysis(self, orchestrator):
        """测试成功分析场景"""
        app_ids = ["test-app-1", "test-app-2"]

        # Mock 外部依赖
        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect:
            mock_collect.return_value = [
                AsyncMock(success=True, app_info=AsyncMock(app_id=app_id))
                for app_id in app_ids
            ]

            result = await orchestrator.analyze_architecture(app_ids)

            assert result.success is True
            assert len(result.apps_data) == 2

    @pytest.mark.asyncio
    async def test_partial_failure_analysis(self, orchestrator):
        """测试部分失败场景"""
        app_ids = ["good-app", "bad-app"]

        with patch.object(orchestrator.collector, 'collect_batch_info') as mock_collect:
            mock_collect.return_value = [
                AsyncMock(success=True, app_info=AsyncMock(app_id="good-app")),
                AsyncMock(success=False, app_info=None, error_message="采集失败")
            ]

            result = await orchestrator.analyze_architecture(app_ids)

            # 应该成功，但只包含成功的应用
            assert result.success is True
            assert len(result.apps_data) == 1
            assert result.apps_data[0].app_id == "good-app"
```

### 2. 性能测试

```python
import asyncio
import time
from src.core.pipeline import PipelineOrchestrator

async def performance_test():
    """性能测试示例"""
    orchestrator = PipelineOrchestrator()

    # 测试不同规模的系统
    test_sizes = [10, 50, 100]

    for size in test_sizes:
        app_ids = [f"perf-app-{i}" for i in range(size)]

        start_time = time.time()
        result = await orchestrator.analyze_architecture(app_ids)
        end_time = time.time()

        duration = end_time - start_time

        print(f"规模 {size}: {duration:.2f}秒, 平均 {duration/size:.3f}秒/应用")

asyncio.run(performance_test())
```

## 🔧 配置示例

### 环境变量配置

```bash
# .env 文件
# LLM 配置
ARCHI_LLM__PROVIDER=openai
ARCHI_LLM__API_KEY=sk-your-openai-api-key
ARCHI_LLM__MODEL=gpt-4
ARCHI_LLM__TEMPERATURE=0.1
ARCHI_LLM__MAX_TOKENS=4000

# MCP 配置
ARCHI_MCP__ENABLED=true
ARCHI_MCP__ENDPOINT=http://mcp-server.company.com:8080
ARCHI_MCP__TIMEOUT=30

# 处理配置
ARCHI_PROCESSING__MAX_CONCURRENT_APPS=20
ARCHI_PROCESSING__BATCH_SIZE=10
ARCHI_PROCESSING__OUTPUT_DIR=./analysis_reports

# API配置
ARCHI_API__HOST=0.0.0.0
ARCHI_API__PORT=8000
ARCHI_API__WORKERS=4

# 日志配置
ARCHI_LOGGING__LEVEL=INFO
ARCHI_LOGGING__FILE_PATH=./logs/archi_analyzer.log

# 调试模式
ARCHI_DEBUG=false
```

### 程序化配置

```python
from src.config.settings import settings

def configure_for_production():
    """生产环境配置"""
    # LLM配置
    settings.llm.provider = "openai"
    settings.llm.model = "gpt-4"
    settings.llm.temperature = 0.1

    # 处理配置
    settings.processing.max_concurrent_apps = 50
    settings.processing.batch_size = 20

    # API配置
    settings.api.host = "0.0.0.0"
    settings.api.port = 80
    settings.api.workers = 8

    # 禁用调试
    settings.debug = False

def configure_for_development():
    """开发环境配置"""
    settings.debug = True
    settings.api.reload = True
    settings.processing.max_concurrent_apps = 5
    settings.llm.model = "gpt-3.5-turbo"  # 使用更快的模型
```

## 📈 监控和日志示例

### 日志记录

```python
import structlog
from src.config.settings import settings

def setup_structured_logging():
    """设置结构化日志"""
    if settings.logging.level == "DEBUG":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

# 使用结构化日志
logger = structlog.get_logger()

async def monitored_analysis():
    """带监控的分析函数"""
    with logger.new(task_id="example-task") as task_logger:
        task_logger.info("开始架构分析")

        try:
            # 执行分析...
            task_logger.info("分析完成", duration=123.45, app_count=10)
        except Exception as e:
            task_logger.error("分析失败", error=str(e))
            raise
```

这些示例展示了AI Architecture Analyzer的主要功能和使用方式。你可以根据实际需求调整配置和代码。



