"""架构分析引擎 - 基于LLM的智能分析"""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..collectors.base import AppInfo
from ..config.settings import settings


class ArchitectureAnalysis(BaseModel):
    """架构分析结果"""

    # 基本信息
    summary: str = Field(..., description="架构总述")
    architecture_type: str = Field(..., description="架构类型")

    # 技术栈分析
    tech_stack: Dict[str, Any] = Field(default_factory=dict, description="技术栈分析")
    languages: List[str] = Field(default_factory=list, description="使用的编程语言")
    frameworks: List[str] = Field(default_factory=list, description="使用的框架")

    # 依赖关系分析
    dependencies: Dict[str, Any] = Field(default_factory=dict, description="依赖关系分析")
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict, description="依赖图")

    # 架构质量评估
    quality_score: float = Field(default=0.0, ge=0.0, le=10.0, description="架构质量评分")
    strengths: List[str] = Field(default_factory=list, description="架构优势")
    weaknesses: List[str] = Field(default_factory=list, description="架构问题")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")

    # 风险评估
    risks: List[Dict[str, Any]] = Field(default_factory=list, description="架构风险")
    security_concerns: List[str] = Field(default_factory=list, description="安全隐患")

    # 扩展性分析
    scalability: Dict[str, Any] = Field(default_factory=dict, description="扩展性评估")
    performance_bottlenecks: List[str] = Field(default_factory=list, description="性能瓶颈")

    # 部署运维建议
    deployment_recommendations: List[str] = Field(default_factory=list, description="部署建议")
    monitoring_suggestions: List[str] = Field(default_factory=list, description="监控建议")


class LLMAnalyzerError(Exception):
    """LLM分析器错误"""
    pass


class LLMAnalyzer:
    """基于LLM的架构分析引擎"""

    def __init__(self):
        self.config = settings.llm
        self.client = self._create_llm_client()

    def _create_llm_client(self):
        """创建LLM客户端"""
        if self.config.provider == "openai":
            try:
                from openai import AsyncOpenAI
                return AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout
                )
            except ImportError:
                raise LLMAnalyzerError("OpenAI SDK未安装，请安装openai包")

        elif self.config.provider == "anthropic":
            try:
                import anthropic
                return anthropic.AsyncAnthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout
                )
            except ImportError:
                raise LLMAnalyzerError("Anthropic SDK未安装，请安装anthropic包")

        else:
            raise LLMAnalyzerError(f"不支持的LLM提供商: {self.config.provider}")

    async def analyze_architecture(self, apps_data: List[AppInfo]) -> ArchitectureAnalysis:
        """分析系统架构

        Args:
            apps_data: 应用数据列表

        Returns:
            ArchitectureAnalysis: 架构分析结果
        """
        if not apps_data:
            raise LLMAnalyzerError("应用数据不能为空")

        # 构建分析prompt
        prompt = self._build_analysis_prompt(apps_data)

        # 调用LLM进行分析
        response = await self._call_llm(prompt)

        # 解析分析结果
        return self._parse_analysis_result(response, apps_data)

    async def analyze_single_app(self, app_data: AppInfo) -> Dict[str, Any]:
        """分析单个应用

        Args:
            app_data: 应用数据

        Returns:
            Dict[str, Any]: 单应用分析结果
        """
        prompt = self._build_single_app_prompt(app_data)
        response = await self._call_llm(prompt)
        return self._parse_single_app_result(response, app_data)

    def _build_analysis_prompt(self, apps_data: List[AppInfo]) -> str:
        """构建系统架构分析prompt"""
        apps_json = json.dumps([app.model_dump() for app in apps_data], indent=2, ensure_ascii=False)

        prompt = f"""你是一个资深的系统架构师，请对以下系统架构进行全面分析。

应用数据：
{apps_json}

请从以下维度进行分析，并以JSON格式返回结果：

1. **summary**: 系统架构的总述（200字以内）
2. **architecture_type**: 架构类型（如：微服务架构、单体架构、分布式架构等）
3. **tech_stack**: 技术栈分析，包括主要语言、框架、中间件等
4. **languages**: 使用的编程语言列表
5. **frameworks**: 使用的框架列表
6. **dependencies**: 依赖关系分析，描述应用间的调用关系
7. **dependency_graph**: 依赖关系图，格式如：{{"app1": ["app2", "app3"]}}
8. **quality_score**: 架构质量评分（0-10分）
9. **strengths**: 架构优势列表（3-5项）
10. **weaknesses**: 架构问题列表（3-5项）
11. **recommendations**: 改进建议列表（3-5项）
12. **risks**: 风险列表，每项包含risk_type、severity（high/medium/low）、description
13. **security_concerns**: 安全隐患列表
14. **scalability**: 扩展性评估，包括水平扩展、垂直扩展能力
15. **performance_bottlenecks**: 潜在性能瓶颈列表
16. **deployment_recommendations**: 部署建议列表
17. **monitoring_suggestions**: 监控建议列表

请确保返回的是有效的JSON格式，不要包含其他文本。"""

        return prompt

    def _build_single_app_prompt(self, app_data: AppInfo) -> str:
        """构建单应用分析prompt"""
        app_json = json.dumps(app_data.model_dump(), indent=2, ensure_ascii=False)

        prompt = f"""你是一个资深的应用架构师，请对以下应用进行详细分析。

应用数据：
{app_json}

请分析以下方面：
1. 技术栈评估
2. 架构设计合理性
3. 潜在风险和问题
4. 优化建议
5. 部署运维建议

请以结构化的方式返回分析结果。"""

        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM服务"""
        try:
            if self.config.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                return response.choices[0].message.content

            elif self.config.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
                return response.content[0].text

            else:
                raise LLMAnalyzerError(f"不支持的LLM提供商: {self.config.provider}")

        except Exception as e:
            raise LLMAnalyzerError(f"LLM调用失败: {str(e)}") from e

    def _parse_analysis_result(self, response: str, apps_data: List[AppInfo]) -> ArchitectureAnalysis:
        """解析架构分析结果"""
        try:
            # 尝试解析JSON响应
            result_data = json.loads(response.strip())

            # 验证必要字段
            required_fields = [
                "summary", "architecture_type", "quality_score",
                "strengths", "weaknesses", "recommendations"
            ]

            for field in required_fields:
                if field not in result_data:
                    result_data[field] = self._get_default_value(field)

            # 创建ArchitectureAnalysis对象
            analysis = ArchitectureAnalysis(**result_data)

            return analysis

        except json.JSONDecodeError as e:
            # JSON解析失败，返回默认分析结果
            return self._create_default_analysis(apps_data, f"LLM响应解析失败: {str(e)}")
        except Exception as e:
            return self._create_default_analysis(apps_data, f"结果解析异常: {str(e)}")

    def _parse_single_app_result(self, response: str, app_data: AppInfo) -> Dict[str, Any]:
        """解析单应用分析结果"""
        try:
            # 尝试解析为JSON
            result = json.loads(response.strip())
        except json.JSONDecodeError:
            # 如果不是JSON，返回文本结果
            result = {"analysis": response}

        result["app_id"] = app_data.app_id
        return result

    def _get_default_value(self, field: str) -> Any:
        """获取字段默认值"""
        defaults = {
            "summary": "系统架构分析完成，但LLM未返回完整结果",
            "architecture_type": "未知",
            "quality_score": 5.0,
            "strengths": ["需要进一步分析确认"],
            "weaknesses": ["需要进一步分析确认"],
            "recommendations": ["建议进行人工复核"]
        }
        return defaults.get(field, [])

    def _create_default_analysis(self, apps_data: List[AppInfo], error_msg: str) -> ArchitectureAnalysis:
        """创建默认分析结果"""
        return ArchitectureAnalysis(
            summary=f"架构分析失败: {error_msg}",
            architecture_type="未知",
            quality_score=0.0,
            strengths=[],
            weaknesses=[error_msg],
            recommendations=["请检查LLM配置和网络连接"]
        )



