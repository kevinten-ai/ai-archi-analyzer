"""报告生成器 - 生成架构分析报告"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from .analyzer import ArchitectureAnalysis
from ..collectors.base import AppInfo
from ..config.settings import settings


class ReportFormat:
    """报告格式枚举"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class ReportGenerator:
    """架构分析报告生成器"""

    def __init__(self, template_dir: Optional[str] = None):
        self.template_dir = Path(template_dir or Path(__file__).parent / "templates")
        self.output_dir = Path(settings.processing.output_dir)

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # 如果模板目录不存在，创建默认模板
        if not self.template_dir.exists():
            self._create_default_templates()

    def generate_architecture_report(
        self,
        analysis: ArchitectureAnalysis,
        apps_data: List[AppInfo],
        format_type: str = ReportFormat.MARKDOWN
    ) -> str:
        """生成架构分析报告

        Args:
            analysis: 架构分析结果
            apps_data: 应用数据列表
            format_type: 报告格式

        Returns:
            str: 生成的报告内容
        """
        if format_type == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(analysis, apps_data)
        elif format_type == ReportFormat.JSON:
            return self._generate_json_report(analysis, apps_data)
        elif format_type == ReportFormat.HTML:
            return self._generate_html_report(analysis, apps_data)
        else:
            raise ValueError(f"不支持的报告格式: {format_type}")

    def save_report(
        self,
        analysis: ArchitectureAnalysis,
        apps_data: List[AppInfo],
        filename: Optional[str] = None,
        format_type: str = ReportFormat.MARKDOWN
    ) -> Path:
        """保存报告到文件

        Args:
            analysis: 架构分析结果
            apps_data: 应用数据列表
            filename: 文件名（不含扩展名）
            format_type: 报告格式

        Returns:
            Path: 保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"architecture_analysis_{timestamp}"

        # 生成报告内容
        content = self.generate_architecture_report(analysis, apps_data, format_type)

        # 确定文件扩展名
        extension = {
            ReportFormat.MARKDOWN: ".md",
            ReportFormat.JSON: ".json",
            ReportFormat.HTML: ".html"
        }.get(format_type, ".txt")

        # 保存文件
        file_path = self.output_dir / f"{filename}{extension}"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def _generate_markdown_report(
        self,
        analysis: ArchitectureAnalysis,
        apps_data: List[AppInfo]
    ) -> str:
        """生成Markdown格式报告"""
        template_name = "architecture_report.md.j2"

        # 准备模板数据
        template_data = {
            "analysis": analysis.model_dump(),
            "apps_data": [app.model_dump() for app in apps_data],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_apps": len(apps_data),
            "app_summary": self._create_app_summary(apps_data),
            "dependency_matrix": self._create_dependency_matrix(apps_data)
        }

        # 渲染模板
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**template_data)
        except Exception:
            # 如果模板不存在，使用内置模板
            return self._generate_builtin_markdown(analysis, apps_data)

    def _generate_json_report(
        self,
        analysis: ArchitectureAnalysis,
        apps_data: List[AppInfo]
    ) -> str:
        """生成JSON格式报告"""
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_apps": len(apps_data),
                "generator_version": "1.0.0"
            },
            "architecture_analysis": analysis.model_dump(),
            "applications": [app.model_dump() for app in apps_data],
            "summary": {
                "app_summary": self._create_app_summary(apps_data),
                "dependency_matrix": self._create_dependency_matrix(apps_data)
            }
        }

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def _generate_html_report(
        self,
        analysis: ArchitectureAnalysis,
        apps_data: List[AppInfo]
    ) -> str:
        """生成HTML格式报告"""
        # 转换为Markdown后简单包装HTML
        markdown_content = self._generate_markdown_report(analysis, apps_data)

        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统架构分析报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        code {{
            background-color: #f1f3f4;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        .score {{
            font-size: 1.2em;
            font-weight: bold;
            color: #e74c3c;
        }}
        .score-high {{ color: #27ae60; }}
        .score-medium {{ color: #f39c12; }}
        .score-low {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        {self._markdown_to_html(markdown_content)}
    </div>
</body>
</html>
        """

        return html_template

    def _generate_builtin_markdown(
        self,
        analysis: ArchitectureAnalysis,
        apps_data: List[AppInfo]
    ) -> str:
        """生成内置Markdown报告（当模板不存在时使用）"""
        lines = []

        # 标题
        lines.append("# 系统架构分析报告")
        lines.append("")

        # 生成时间
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # 基本信息
        lines.append("## 📊 基本信息")
        lines.append(f"- **应用数量**: {len(apps_data)}")
        lines.append(f"- **架构类型**: {analysis.architecture_type}")
        lines.append(f"- **质量评分**: {analysis.quality_score}/10")
        lines.append("")

        # 架构总述
        lines.append("## 📋 架构总述")
        lines.append(analysis.summary)
        lines.append("")

        # 技术栈分析
        lines.append("## 🛠️ 技术栈分析")
        if analysis.languages:
            lines.append(f"**编程语言**: {', '.join(analysis.languages)}")
        if analysis.frameworks:
            lines.append(f"**框架**: {', '.join(analysis.frameworks)}")
        lines.append("")

        # 架构优势
        if analysis.strengths:
            lines.append("## ✅ 架构优势")
            for strength in analysis.strengths:
                lines.append(f"- {strength}")
            lines.append("")

        # 架构问题
        if analysis.weaknesses:
            lines.append("## ⚠️ 架构问题")
            for weakness in analysis.weaknesses:
                lines.append(f"- {weakness}")
            lines.append("")

        # 改进建议
        if analysis.recommendations:
            lines.append("## 💡 改进建议")
            for recommendation in analysis.recommendations:
                lines.append(f"- {recommendation}")
            lines.append("")

        # 风险评估
        if analysis.risks:
            lines.append("## 🚨 风险评估")
            for risk in analysis.risks:
                risk_type = risk.get("risk_type", "未知风险")
                severity = risk.get("severity", "medium")
                description = risk.get("description", "")
                lines.append(f"- **{risk_type}** ({severity}): {description}")
            lines.append("")

        # 应用详情
        lines.append("## 📱 应用详情")
        for app in apps_data:
            lines.append(f"### {app.name or app.app_id}")
            lines.append(f"- **应用ID**: {app.app_id}")
            if app.description:
                lines.append(f"- **描述**: {app.description}")
            if app.language:
                lines.append(f"- **语言**: {app.language}")
            if app.framework:
                lines.append(f"- **框架**: {app.framework}")
            if app.dependencies:
                lines.append(f"- **依赖**: {', '.join(app.dependencies)}")
            lines.append("")

        return "\n".join(lines)

    def _create_app_summary(self, apps_data: List[AppInfo]) -> Dict[str, Any]:
        """创建应用汇总信息"""
        summary = {
            "total_apps": len(apps_data),
            "languages": {},
            "frameworks": {},
            "deployment_types": {},
            "environments": {}
        }

        for app in apps_data:
            # 统计编程语言
            if app.language:
                summary["languages"][app.language] = summary["languages"].get(app.language, 0) + 1

            # 统计框架
            if app.framework:
                summary["frameworks"][app.framework] = summary["frameworks"].get(app.framework, 0) + 1

            # 统计部署类型
            if app.deployment_type:
                summary["deployment_types"][app.deployment_type] = summary["deployment_types"].get(app.deployment_type, 0) + 1

            # 统计环境
            if app.environment:
                summary["environments"][app.environment] = summary["environments"].get(app.environment, 0) + 1

        return summary

    def _create_dependency_matrix(self, apps_data: List[AppInfo]) -> Dict[str, List[str]]:
        """创建依赖关系矩阵"""
        matrix = {}
        app_map = {app.app_id: app for app in apps_data}

        for app in apps_data:
            dependencies = []
            if app.dependencies:
                for dep_id in app.dependencies:
                    if dep_id in app_map:
                        dep_app = app_map[dep_id]
                        dependencies.append(dep_app.name or dep_id)
            matrix[app.name or app.app_id] = dependencies

        return matrix

    def _markdown_to_html(self, markdown_content: str) -> str:
        """简单Markdown转HTML（基础实现）"""
        # 这里可以集成markdown库进行转换
        # 暂时返回简单的预格式化文本
        return f"<pre>{markdown_content}</pre>"

    def _create_default_templates(self):
        """创建默认模板文件"""
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Markdown模板
        md_template = '''# 系统架构分析报告

**生成时间**: {{ generated_at }}
**应用数量**: {{ total_apps }}

## 📊 基本信息

- **架构类型**: {{ analysis.architecture_type }}
- **质量评分**: {{ analysis.quality_score }}/10

## 📋 架构总述

{{ analysis.summary }}

## 🛠️ 技术栈分析

**编程语言**: {{ analysis.languages | join(', ') }}
**框架**: {{ analysis.frameworks | join(', ') }}

## ✅ 架构优势

{% for strength in analysis.strengths %}
- {{ strength }}
{% endfor %}

## ⚠️ 架构问题

{% for weakness in analysis.weaknesses %}
- {{ weakness }}
{% endfor %}

## 💡 改进建议

{% for recommendation in analysis.recommendations %}
- {{ recommendation }}
{% endfor %}

## 📱 应用详情

{% for app in apps_data %}
### {{ app.name or app.app_id }}

- **应用ID**: {{ app.app_id }}
- **描述**: {{ app.description or '无' }}
- **语言**: {{ app.language or '未知' }}
- **框架**: {{ app.framework or '未知' }}
- **依赖**: {{ app.dependencies | join(', ') or '无' }}
{% endfor %}
'''

        with open(self.template_dir / "architecture_report.md.j2", "w", encoding="utf-8") as f:
            f.write(md_template)



