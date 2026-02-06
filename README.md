# AI Architecture Analyzer

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于LLM的系统架构分析平台，支持通过MCP客户端获取应用数据，进行智能架构分析和报告生成。

## 📋 项目概述

本项目是一个专为大规模分布式系统设计的**架构梳理自动化平台**，核心目标是实现自动规模化的架构梳理能力。通过智能分析器集群，实现对复杂企业级系统的自动化架构发现、依赖关系梳理和结构化文档生成，显著提升架构梳理的效率和质量。

### 🎯 核心特性

- **智能架构发现**：基于代码分析和配置扫描，自动识别应用间的依赖关系
- **服务拓扑构建**：自动生成服务调用拓扑图，清晰展示系统架构层次
- **LLM驱动分析**：使用大语言模型进行深度架构分析和优化建议
- **多格式报告**：支持Markdown、JSON、HTML等多种格式的报告输出
- **可扩展设计**：插件化架构，支持自定义数据源和分析器
- **高性能处理**：异步处理和并发控制，支持大规模系统分析

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    📊 报告展示层                              │
│  ├─ Markdown报告   ├─ JSON数据   ├─ 统计图表   ├─ 优化建议    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    🔍 分析处理层                              │
│  ├─ 结构分析器     ├─ 智能分析器 ├─ 配置分析器 ├─ 风险评估器  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    🔄 数据转换层                              │
│  ├─ 数据清洗       ├─ 格式转换    ├─ 数据聚合    ├─ 验证检查  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    📥 数据采集层                              │
│  ├─ MCP接口       ├─ 配置获取     ├─ 文件处理    ├─ 数据备份   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip (推荐使用虚拟环境)

### 安装依赖

```bash
# 克隆项目
cd ai_platform/ai-archi-analyzer

# 安装依赖
pip install -r requirements.txt

# 或者使用uv
pip install -e .
```

### 配置环境

创建 `.env` 文件：

```bash
# LLM配置
ARCHI_LLM__PROVIDER=openai
ARCHI_LLM__API_KEY=your_openai_api_key
ARCHI_LLM__MODEL=gpt-4

# MCP配置
ARCHI_MCP__ENABLED=true
ARCHI_MCP__ENDPOINT=http://your-mcp-server:8080

# API服务配置
ARCHI_API__HOST=0.0.0.0
ARCHI_API__PORT=8000

# 调试模式
ARCHI_DEBUG=true
```

### 启动服务

```bash
# 启动API服务
python -m src.main

# 或者直接运行
python src/main.py
```

服务将在 `http://localhost:8000` 启动，API文档可在 `http://localhost:8000/docs` 查看。

## 📖 API使用指南

详细的API使用示例请参考：[使用示例](docs/examples.md)

### 1. 开始架构分析

```bash
curl -X POST "http://localhost:8000/api/analyze" \
     -H "Content-Type: application/json" \
     -d '{
       "app_ids": ["app1", "app2", "app3"],
       "report_format": "markdown",
       "enable_progress_tracking": true
     }'
```

响应：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "架构分析任务已接受，正在处理中"
}
```

### 2. 查询任务状态

```bash
curl "http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000/status"
```

响应：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "analyzing",
  "progress": 0.7,
  "message": "执行架构智能分析",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": null
}
```

### 3. 获取分析结果

```bash
curl "http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000/result"
```

响应：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "completed_at": "2024-01-15T10:35:23",
  "processing_time": 323.45,
  "report_url": "/api/reports/550e8400-e29b-41d4-a716-446655440000",
  "architecture_summary": {
    "type": "微服务架构",
    "summary": "该系统采用微服务架构，共包含15个服务..."
  },
  "total_apps": 15,
  "quality_score": 8.5
}
```

### 4. 下载分析报告

```bash
curl "http://localhost:8000/api/reports/550e8400-e29b-41d4-a716-446655440000?format=markdown"
```

### 5. 健康检查

```bash
curl "http://localhost:8000/api/health"
```

响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:40:00",
  "components": {
    "mcp_collector": "healthy",
    "llm_analyzer": "healthy"
  }
}
```

## 🛠️ 开发指南

### 项目结构

```
src/
├── api/                    # API层
│   ├── __init__.py
│   ├── routes.py          # API路由
│   └── models.py          # 数据模型
├── core/                  # 核心业务逻辑
│   ├── __init__.py
│   ├── pipeline.py        # 管道编排器
│   ├── analyzer.py        # LLM分析引擎
│   └── report_generator.py # 报告生成器
├── collectors/            # 数据采集层
│   ├── __init__.py
│   ├── base.py            # 采集器基类
│   └── mcp_collector.py   # MCP采集器
├── processors/            # 数据处理层
│   ├── __init__.py
│   ├── data_transformer.py # 数据转换器
│   ├── data_validator.py   # 数据验证器
│   └── error_handler.py    # 错误处理
├── config/                # 配置管理
│   ├── __init__.py
│   └── settings.py        # 配置管理器
└── main.py               # 程序入口
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_pipeline.py

# 带覆盖率测试
pytest --cov=src --cov-report=html
```

### 代码格式化

```bash
# 格式化代码
black src/

# 排序导入
isort src/

# 类型检查
mypy src/
```

## 🔧 配置说明

### LLM配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ARCHI_LLM__PROVIDER` | LLM提供商 | `openai` |
| `ARCHI_LLM__API_KEY` | API密钥 | 必需 |
| `ARCHI_LLM__MODEL` | 模型名称 | `gpt-4` |
| `ARCHI_LLM__TEMPERATURE` | 温度参数 | `0.1` |
| `ARCHI_LLM__MAX_TOKENS` | 最大token数 | `4000` |

### MCP配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ARCHI_MCP__ENABLED` | 是否启用MCP | `false` |
| `ARCHI_MCP__ENDPOINT` | MCP服务端点 | 必需 |
| `ARCHI_MCP__TIMEOUT` | 请求超时时间 | `30` |

### 处理配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `ARCHI_PROCESSING__MAX_CONCURRENT_APPS` | 最大并发应用数 | `10` |
| `ARCHI_PROCESSING__BATCH_SIZE` | 批处理大小 | `5` |
| `ARCHI_PROCESSING__OUTPUT_DIR` | 输出目录 | `./output` |

## 🔌 扩展开发

### 添加新的数据采集器

1. 继承 `BaseDataCollector` 类
2. 实现 `collect_app_info` 和 `collect_batch_info` 方法
3. 在 `PipelineOrchestrator` 中集成新的采集器

### 添加新的分析器

1. 继承 `LLMAnalyzer` 类或创建新的分析器
2. 实现分析逻辑
3. 在管道中集成新的分析器

### 添加新的报告格式

1. 在 `ReportFormat` 枚举中添加新格式
2. 在 `ReportGenerator` 中实现对应的生成方法

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的API框架
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库
- [OpenAI](https://openai.com/) - 大语言模型服务
- [参考文档](../企业级架构梳理自动化平台总结.md) - 架构设计理念

## 📞 联系方式

- 项目维护者：Architecture Team
- 邮箱：archi@company.com

---

**注意**: 本项目仍在开发中，API可能会发生变化。请关注版本更新。