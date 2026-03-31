"""数据转换器测试"""

import pytest

from src.collectors.base import AppInfo
from src.processors.data_transformer import DataTransformer


class TestDataTransformer:
    """DataTransformer 测试"""

    @pytest.fixture
    def transformer(self):
        return DataTransformer()

    @pytest.fixture
    def sample_apps(self):
        return [
            AppInfo(
                app_id="app1",
                name="  用户服务  ",
                language="java",
                framework="spring boot",
                deployment_type="k8s",
                environment="prod",
                dependencies=["app2", "app2", "app3"],  # 有重复
                databases=["mysql", ""],  # 有空值
                services=["service-a"],
            ),
            AppInfo(
                app_id="app2",
                name="订单服务",
                language="JAVA",
                framework="Spring Boot",
                deployment_type="kubernetes",
                environment="production",
                dependencies=["app3"],
                databases=["redis"],
                services=[],
            ),
            AppInfo(
                app_id="app3",
                name="支付服务",
                language="golang",
                framework="gin",
                environment="dev",
                dependencies=["external-svc"],
            ),
        ]

    def test_transform_normalizes_languages(self, transformer, sample_apps):
        """测试编程语言标准化"""
        result = transformer.transform(sample_apps)
        languages = {app.language for app in result}
        # "java", "JAVA" -> "Java"; "golang" -> "Go"
        assert languages == {"Java", "Go"}

    def test_transform_normalizes_frameworks(self, transformer, sample_apps):
        """测试框架名称标准化"""
        result = transformer.transform(sample_apps)
        frameworks = {app.framework for app in result if app.framework}
        # "spring boot" -> "Spring Boot"; "gin" -> "Gin"
        assert "Spring Boot" in frameworks
        assert "Gin" in frameworks

    def test_transform_normalizes_environments(self, transformer, sample_apps):
        """测试环境名称标准化"""
        result = transformer.transform(sample_apps)
        envs = {app.environment for app in result if app.environment}
        # "prod", "production" -> "production"; "dev" -> "development"
        assert envs == {"production", "development"}

    def test_transform_normalizes_deployment_types(self, transformer, sample_apps):
        """测试部署类型标准化"""
        result = transformer.transform(sample_apps)
        deploy_types = {app.deployment_type for app in result if app.deployment_type}
        # "k8s", "kubernetes" -> "kubernetes"
        assert deploy_types == {"kubernetes"}

    def test_transform_cleans_whitespace(self, transformer, sample_apps):
        """测试空白字符清理"""
        result = transformer.transform(sample_apps)
        app1 = next(a for a in result if a.app_id == "app1")
        assert app1.name == "用户服务"  # 前后空格已清除

    def test_transform_deduplicates_dependencies(self, transformer, sample_apps):
        """测试依赖去重"""
        result = transformer.transform(sample_apps)
        app1 = next(a for a in result if a.app_id == "app1")
        # 原始 ["app2", "app2", "app3"] -> 去重后 ["app2", "app3"]
        assert app1.dependencies == ["app2", "app3"]

    def test_transform_removes_empty_list_items(self, transformer, sample_apps):
        """测试列表中空值移除"""
        result = transformer.transform(sample_apps)
        app1 = next(a for a in result if a.app_id == "app1")
        assert "" not in app1.databases

    def test_transform_deduplicates_apps(self, transformer):
        """测试应用去重（基于app_id）"""
        apps = [
            AppInfo(app_id="dup", name="版本1"),
            AppInfo(app_id="dup", name="版本2"),
            AppInfo(app_id="unique", name="唯一"),
        ]
        result = transformer.transform(apps)
        assert len(result) == 2
        # 保留最后出现的
        dup = next(a for a in result if a.app_id == "dup")
        assert dup.name == "版本2"

    def test_transform_enriches_cross_references(self, transformer, sample_apps):
        """测试交叉引用补充"""
        result = transformer.transform(sample_apps)
        app3 = next(a for a in result if a.app_id == "app3")
        # app3依赖"external-svc"，不在已知应用ID中
        assert "external-svc" in app3.metadata.get("external_dependencies", [])

    def test_transform_empty_list(self, transformer):
        """测试空列表"""
        assert transformer.transform([]) == []

    def test_aggregate(self, transformer, sample_apps):
        """测试数据聚合"""
        transformed = transformer.transform(sample_apps)
        stats = transformer.aggregate(transformed)

        assert stats["total_apps"] == 3
        assert "Java" in stats["languages"]
        assert stats["languages"]["Java"] == 2
        assert "Go" in stats["languages"]
        assert len(stats["unique_databases"]) > 0
        assert stats["avg_dependencies"] > 0

    def test_aggregate_empty(self, transformer):
        """测试空列表聚合"""
        stats = transformer.aggregate([])
        assert stats["total_apps"] == 0
