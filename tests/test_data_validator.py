"""数据验证器测试"""

import pytest

from src.collectors.base import AppInfo
from src.processors.data_validator import DataValidator, ValidationSeverity


class TestDataValidator:
    """DataValidator 测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_validate_valid_apps(self, validator):
        """测试有效应用数据验证"""
        apps = [
            AppInfo(app_id="app1", name="服务A", language="Java", version="1.0.0"),
            AppInfo(app_id="app2", name="服务B", language="Go", version="2.1.0"),
        ]
        result = validator.validate(apps)
        assert result.valid is True
        assert result.apps_passed == 2
        assert result.apps_failed == 0
        assert len(result.errors) == 0

    def test_validate_empty_app_id(self, validator):
        """测试空app_id"""
        apps = [AppInfo(app_id="", name="无ID应用")]
        result = validator.validate(apps)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].rule == "required_app_id"

    def test_validate_self_dependency(self, validator):
        """测试自引用依赖"""
        apps = [AppInfo(app_id="app1", name="自依赖", dependencies=["app1", "app2"])]
        result = validator.validate(apps)
        assert result.valid is False
        errors = [e for e in result.errors if e.rule == "no_self_dependency"]
        assert len(errors) == 1

    def test_validate_missing_name_warning(self, validator):
        """测试缺少名称产生警告"""
        apps = [AppInfo(app_id="app1", language="Java")]
        result = validator.validate(apps)
        assert result.valid is True  # 仍然有效（仅是警告）
        warnings = [w for w in result.warnings if w.rule == "recommended_name"]
        assert len(warnings) == 1

    def test_validate_missing_language_warning(self, validator):
        """测试缺少语言产生警告"""
        apps = [AppInfo(app_id="app1", name="测试")]
        result = validator.validate(apps)
        warnings = [w for w in result.warnings if w.rule == "recommended_language"]
        assert len(warnings) == 1

    def test_validate_duplicate_dependency_warning(self, validator):
        """测试重复依赖产生警告"""
        apps = [AppInfo(app_id="app1", name="测试", dependencies=["dep1", "dep1"])]
        result = validator.validate(apps)
        warnings = [w for w in result.warnings if w.rule == "no_duplicate_dependency"]
        assert len(warnings) == 1

    def test_validate_circular_dependency(self, validator):
        """测试循环依赖检测"""
        apps = [
            AppInfo(app_id="a", name="A", dependencies=["b"]),
            AppInfo(app_id="b", name="B", dependencies=["c"]),
            AppInfo(app_id="c", name="C", dependencies=["a"]),
        ]
        result = validator.validate(apps)
        cycle_warnings = [w for w in result.warnings if w.rule == "no_circular_dependency"]
        assert len(cycle_warnings) > 0

    def test_validate_no_circular_for_external_deps(self, validator):
        """测试外部依赖不触发循环检测"""
        apps = [
            AppInfo(app_id="a", name="A", dependencies=["external"]),
        ]
        result = validator.validate(apps)
        cycle_warnings = [w for w in result.warnings if w.rule == "no_circular_dependency"]
        assert len(cycle_warnings) == 0

    def test_validate_version_format(self, validator):
        """测试版本号格式"""
        apps = [AppInfo(app_id="app1", name="测试", version="not-a-version")]
        result = validator.validate(apps)
        info_issues = [i for i in result.issues if i.rule == "version_format"]
        assert len(info_issues) == 1

    def test_validate_valid_version_formats(self, validator):
        """测试有效版本号格式"""
        valid_versions = ["1.0.0", "2.1", "3", "v1.2.3", "1.0.0-beta.1"]
        for ver in valid_versions:
            apps = [AppInfo(app_id="app1", name="测试", version=ver)]
            result = validator.validate(apps)
            version_issues = [i for i in result.issues if i.rule == "version_format"]
            assert len(version_issues) == 0, f"版本 {ver} 不应产生问题"

    def test_filter_valid(self, validator):
        """测试过滤有效应用"""
        apps = [
            AppInfo(app_id="good", name="好的"),
            AppInfo(app_id="bad", name="坏的", dependencies=["bad"]),  # 自依赖
            AppInfo(app_id="also-good", name="也好的"),
        ]
        result = validator.validate(apps)
        filtered = validator.filter_valid(apps, result)
        assert len(filtered) == 2
        assert all(a.app_id != "bad" for a in filtered)

    def test_summary(self, validator):
        """测试验证摘要"""
        apps = [
            AppInfo(app_id="a", name="A", language="Java"),
            AppInfo(app_id="", name="无ID"),
        ]
        result = validator.validate(apps)
        summary = result.summary()
        assert "valid" in summary
        assert "apps_validated" in summary
        assert summary["apps_validated"] == 2
        assert summary["errors"] >= 1
