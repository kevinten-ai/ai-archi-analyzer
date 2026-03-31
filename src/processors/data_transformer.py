"""数据转换器 - 数据清洗、格式转换和数据聚合"""

from typing import Any, Dict, List, Optional, Set

from loguru import logger

from ..collectors.base import AppInfo


class DataTransformError(Exception):
    """数据转换错误"""
    pass


class DataTransformer:
    """数据转换器

    负责对采集到的应用数据进行清洗、标准化和聚合处理，
    确保数据质量满足后续分析引擎的要求。
    """

    # 已知编程语言标准化映射
    LANGUAGE_ALIASES: Dict[str, str] = {
        "java": "Java",
        "JAVA": "Java",
        "python": "Python",
        "py": "Python",
        "golang": "Go",
        "go": "Go",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "typescript": "TypeScript",
        "ts": "TypeScript",
        "c#": "C#",
        "csharp": "C#",
        "c++": "C++",
        "cpp": "C++",
        "ruby": "Ruby",
        "rb": "Ruby",
        "rust": "Rust",
        "kotlin": "Kotlin",
        "scala": "Scala",
        "swift": "Swift",
        "php": "PHP",
    }

    # 已知框架标准化映射
    FRAMEWORK_ALIASES: Dict[str, str] = {
        "spring boot": "Spring Boot",
        "spring-boot": "Spring Boot",
        "springboot": "Spring Boot",
        "spring": "Spring",
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "express": "Express",
        "expressjs": "Express",
        "react": "React",
        "vue": "Vue",
        "vuejs": "Vue",
        "angular": "Angular",
        "gin": "Gin",
        "echo": "Echo",
        "rails": "Ruby on Rails",
        "ruby on rails": "Ruby on Rails",
        "laravel": "Laravel",
        "nestjs": "NestJS",
        "nextjs": "Next.js",
        "next.js": "Next.js",
    }

    def transform(self, apps_data: List[AppInfo]) -> List[AppInfo]:
        """执行完整的数据转换流程

        Args:
            apps_data: 原始应用数据列表

        Returns:
            List[AppInfo]: 转换后的应用数据列表
        """
        if not apps_data:
            return []

        logger.info(f"开始数据转换，共 {len(apps_data)} 个应用")

        # 步骤1: 清洗每个应用的数据
        cleaned = [self._clean_app(app) for app in apps_data]

        # 步骤2: 标准化字段值
        normalized = [self._normalize_app(app) for app in cleaned]

        # 步骤3: 去重（基于app_id）
        deduplicated = self._deduplicate(normalized)

        # 步骤4: 补充交叉引用信息
        enriched = self._enrich_cross_references(deduplicated)

        logger.info(f"数据转换完成，输出 {len(enriched)} 个应用")
        return enriched

    def aggregate(self, apps_data: List[AppInfo]) -> Dict[str, Any]:
        """聚合应用数据，生成统计摘要

        Args:
            apps_data: 应用数据列表

        Returns:
            Dict[str, Any]: 聚合统计信息
        """
        if not apps_data:
            return {"total_apps": 0}

        languages: Dict[str, int] = {}
        frameworks: Dict[str, int] = {}
        deployment_types: Dict[str, int] = {}
        environments: Dict[str, int] = {}
        all_databases: Set[str] = set()
        all_services: Set[str] = set()
        dependency_count = 0

        for app in apps_data:
            if app.language:
                languages[app.language] = languages.get(app.language, 0) + 1
            if app.framework:
                frameworks[app.framework] = frameworks.get(app.framework, 0) + 1
            if app.deployment_type:
                deployment_types[app.deployment_type] = deployment_types.get(app.deployment_type, 0) + 1
            if app.environment:
                environments[app.environment] = environments.get(app.environment, 0) + 1
            all_databases.update(app.databases)
            all_services.update(app.services)
            dependency_count += len(app.dependencies)

        return {
            "total_apps": len(apps_data),
            "languages": languages,
            "frameworks": frameworks,
            "deployment_types": deployment_types,
            "environments": environments,
            "unique_databases": sorted(all_databases),
            "unique_services": sorted(all_services),
            "total_dependencies": dependency_count,
            "avg_dependencies": round(dependency_count / len(apps_data), 2) if apps_data else 0,
        }

    def _clean_app(self, app: AppInfo) -> AppInfo:
        """清洗单个应用数据"""
        data = app.model_dump()

        # 清理字符串字段的空白字符
        str_fields = [
            "app_id", "name", "description", "version",
            "language", "framework", "runtime",
            "deployment_type", "environment", "cluster",
        ]
        for field in str_fields:
            value = data.get(field)
            if isinstance(value, str):
                data[field] = value.strip()
                # 空字符串转为None（除app_id和name外）
                if not data[field] and field not in ("app_id", "name"):
                    data[field] = None

        # 清理列表字段：去空值、去重、去空白
        list_fields = ["dependencies", "databases", "services"]
        for field in list_fields:
            items = data.get(field) or []
            cleaned = []
            seen = set()
            for item in items:
                if isinstance(item, str):
                    item = item.strip()
                if item and item not in seen:
                    cleaned.append(item)
                    seen.add(item)
            data[field] = cleaned

        # 清理字典字段
        for field in ["config", "metadata"]:
            if not data.get(field):
                data[field] = {}

        return AppInfo(**data)

    def _normalize_app(self, app: AppInfo) -> AppInfo:
        """标准化应用数据字段值"""
        data = app.model_dump()

        # 标准化编程语言名称
        if data.get("language"):
            lang_lower = data["language"].lower().strip()
            data["language"] = self.LANGUAGE_ALIASES.get(lang_lower, data["language"])

        # 标准化框架名称
        if data.get("framework"):
            fw_lower = data["framework"].lower().strip()
            data["framework"] = self.FRAMEWORK_ALIASES.get(fw_lower, data["framework"])

        # 标准化部署类型
        if data.get("deployment_type"):
            dt = data["deployment_type"].lower().strip()
            deploy_map = {
                "k8s": "kubernetes",
                "kubernetes": "kubernetes",
                "docker": "docker",
                "vm": "virtual_machine",
                "virtual_machine": "virtual_machine",
                "bare_metal": "bare_metal",
                "baremetal": "bare_metal",
                "ecs": "ecs",
                "serverless": "serverless",
                "lambda": "serverless",
            }
            data["deployment_type"] = deploy_map.get(dt, dt)

        # 标准化环境名称
        if data.get("environment"):
            env = data["environment"].lower().strip()
            env_map = {
                "prod": "production",
                "production": "production",
                "stg": "staging",
                "staging": "staging",
                "dev": "development",
                "development": "development",
                "test": "testing",
                "testing": "testing",
                "uat": "uat",
                "pre": "pre-production",
                "pre-production": "pre-production",
            }
            data["environment"] = env_map.get(env, env)

        return AppInfo(**data)

    def _deduplicate(self, apps_data: List[AppInfo]) -> List[AppInfo]:
        """基于app_id去重，保留最后出现的记录"""
        seen: Dict[str, AppInfo] = {}
        for app in apps_data:
            if app.app_id in seen:
                logger.warning(f"发现重复应用ID: {app.app_id}，使用最新记录")
            seen[app.app_id] = app
        return list(seen.values())

    def _enrich_cross_references(self, apps_data: List[AppInfo]) -> List[AppInfo]:
        """补充应用间的交叉引用信息

        如果应用A依赖应用B，确保B的services中包含被A引用的信息。
        """
        app_map = {app.app_id: app for app in apps_data}
        known_ids = set(app_map.keys())

        enriched = []
        for app in apps_data:
            data = app.model_dump()

            # 标记依赖中哪些是已知应用、哪些是外部依赖
            internal_deps = [d for d in app.dependencies if d in known_ids]
            external_deps = [d for d in app.dependencies if d not in known_ids]

            if external_deps:
                metadata = dict(data.get("metadata") or {})
                metadata["external_dependencies"] = external_deps
                metadata["internal_dependencies"] = internal_deps
                data["metadata"] = metadata

            enriched.append(AppInfo(**data))

        return enriched
