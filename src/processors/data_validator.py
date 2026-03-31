"""数据验证器 - 结构验证和业务规则校验"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from ..collectors.base import AppInfo


class ValidationSeverity(Enum):
    """验证问题严重级别"""
    ERROR = "error"        # 必须修复，数据不可用
    WARNING = "warning"    # 建议修复，可能影响分析质量
    INFO = "info"          # 提示信息


@dataclass
class ValidationIssue:
    """验证问题"""
    app_id: str
    field: str
    severity: ValidationSeverity
    message: str
    rule: str  # 触发的规则名称


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    apps_validated: int = 0
    apps_passed: int = 0
    apps_failed: int = 0

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def summary(self) -> Dict[str, Any]:
        """生成验证摘要"""
        return {
            "valid": self.valid,
            "apps_validated": self.apps_validated,
            "apps_passed": self.apps_passed,
            "apps_failed": self.apps_failed,
            "total_issues": len(self.issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
        }


class DataValidator:
    """数据验证器

    对采集并转换后的应用数据进行结构验证和业务规则校验，
    确保数据完整性和一致性。
    """

    def validate(self, apps_data: List[AppInfo]) -> ValidationResult:
        """验证应用数据列表

        Args:
            apps_data: 应用数据列表

        Returns:
            ValidationResult: 验证结果
        """
        issues: List[ValidationIssue] = []
        failed_ids: Set[str] = set()

        logger.info(f"开始数据验证，共 {len(apps_data)} 个应用")

        for app in apps_data:
            app_issues = self._validate_app(app)
            issues.extend(app_issues)

            # 如果有ERROR级别问题，标记为失败
            if any(i.severity == ValidationSeverity.ERROR for i in app_issues):
                failed_ids.add(app.app_id)

        # 跨应用验证
        cross_issues = self._validate_cross_app(apps_data)
        issues.extend(cross_issues)

        passed = len(apps_data) - len(failed_ids)
        result = ValidationResult(
            valid=len(failed_ids) == 0,
            issues=issues,
            apps_validated=len(apps_data),
            apps_passed=passed,
            apps_failed=len(failed_ids),
        )

        logger.info(
            f"数据验证完成: {result.apps_passed}/{result.apps_validated} 通过, "
            f"{len(result.errors)} 错误, {len(result.warnings)} 警告"
        )
        return result

    def filter_valid(
        self,
        apps_data: List[AppInfo],
        result: ValidationResult,
    ) -> List[AppInfo]:
        """过滤出通过验证的应用数据

        Args:
            apps_data: 原始应用数据列表
            result: 验证结果

        Returns:
            List[AppInfo]: 通过验证的应用数据
        """
        failed_ids = {
            issue.app_id
            for issue in result.errors
        }
        return [app for app in apps_data if app.app_id not in failed_ids]

    def _validate_app(self, app: AppInfo) -> List[ValidationIssue]:
        """验证单个应用数据"""
        issues: List[ValidationIssue] = []

        # 规则1: app_id不能为空
        if not app.app_id or not app.app_id.strip():
            issues.append(ValidationIssue(
                app_id=app.app_id or "<empty>",
                field="app_id",
                severity=ValidationSeverity.ERROR,
                message="应用ID不能为空",
                rule="required_app_id",
            ))
            return issues  # app_id为空，后续验证无意义

        # 规则2: name建议不为空
        if not app.name:
            issues.append(ValidationIssue(
                app_id=app.app_id,
                field="name",
                severity=ValidationSeverity.WARNING,
                message="应用名称为空，建议补充",
                rule="recommended_name",
            ))

        # 规则3: 语言和框架建议提供
        if not app.language:
            issues.append(ValidationIssue(
                app_id=app.app_id,
                field="language",
                severity=ValidationSeverity.WARNING,
                message="编程语言未指定，可能影响分析质量",
                rule="recommended_language",
            ))

        # 规则4: 自引用依赖检查
        if app.app_id in app.dependencies:
            issues.append(ValidationIssue(
                app_id=app.app_id,
                field="dependencies",
                severity=ValidationSeverity.ERROR,
                message=f"应用不能依赖自身: {app.app_id}",
                rule="no_self_dependency",
            ))

        # 规则5: 重复依赖检查
        dep_set = set()
        for dep in app.dependencies:
            if dep in dep_set:
                issues.append(ValidationIssue(
                    app_id=app.app_id,
                    field="dependencies",
                    severity=ValidationSeverity.WARNING,
                    message=f"重复依赖: {dep}",
                    rule="no_duplicate_dependency",
                ))
            dep_set.add(dep)

        # 规则6: 版本格式检查（如果提供）
        if app.version and not self._is_valid_version(app.version):
            issues.append(ValidationIssue(
                app_id=app.app_id,
                field="version",
                severity=ValidationSeverity.INFO,
                message=f"版本号格式不规范: {app.version}",
                rule="version_format",
            ))

        return issues

    def _validate_cross_app(self, apps_data: List[AppInfo]) -> List[ValidationIssue]:
        """跨应用验证"""
        issues: List[ValidationIssue] = []
        app_ids = {app.app_id for app in apps_data}

        # 规则: 循环依赖检测
        cycle_issues = self._detect_circular_dependencies(apps_data, app_ids)
        issues.extend(cycle_issues)

        return issues

    def _detect_circular_dependencies(
        self,
        apps_data: List[AppInfo],
        known_ids: Set[str],
    ) -> List[ValidationIssue]:
        """检测循环依赖

        使用DFS检测应用依赖图中的环。
        """
        issues: List[ValidationIssue] = []

        # 构建邻接表（只包含已知应用间的依赖）
        graph: Dict[str, List[str]] = {}
        for app in apps_data:
            graph[app.app_id] = [d for d in app.dependencies if d in known_ids]

        # DFS检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {aid: WHITE for aid in graph}
        path: List[str] = []
        cycles_found: Set[frozenset] = set()

        def dfs(node: str) -> None:
            color[node] = GRAY
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    cycle_key = frozenset(cycle)
                    if cycle_key not in cycles_found:
                        cycles_found.add(cycle_key)
                        cycle_str = " -> ".join(cycle + [neighbor])
                        for app_id in cycle:
                            issues.append(ValidationIssue(
                                app_id=app_id,
                                field="dependencies",
                                severity=ValidationSeverity.WARNING,
                                message=f"检测到循环依赖: {cycle_str}",
                                rule="no_circular_dependency",
                            ))
                elif color[neighbor] == WHITE:
                    dfs(neighbor)

            path.pop()
            color[node] = BLACK

        for node in graph:
            if color[node] == WHITE:
                dfs(node)

        return issues

    def _is_valid_version(self, version: str) -> bool:
        """检查版本号是否符合常见格式"""
        import re
        # 支持 semver、简单版本号等
        patterns = [
            r"^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$",  # semver
            r"^\d+\.\d+$",                                # major.minor
            r"^\d+$",                                      # major only
            r"^v\d+",                                      # v-prefixed
        ]
        return any(re.match(p, version) for p in patterns)
