"""检查点管理器 - 管道阶段数据持久化与恢复"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..collectors.base import AppInfo
from ..config.settings import settings


class CheckpointError(Exception):
    """检查点操作错误"""
    pass


class CheckpointManager:
    """检查点管理器

    支持管道各阶段处理结果的持久化和恢复，
    实现断点续传功能。
    """

    def __init__(self, base_dir: Optional[str] = None):
        """初始化检查点管理器

        Args:
            base_dir: 检查点存储基础目录
        """
        self.base_dir = Path(base_dir or settings.processing.cache_dir) / "checkpoints"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        task_id: str,
        stage: str,
        data: Dict[str, Any],
    ) -> Path:
        """保存检查点

        Args:
            task_id: 任务ID
            stage: 管道阶段名称
            data: 要保存的数据

        Returns:
            Path: 检查点文件路径
        """
        task_dir = self.base_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            "task_id": task_id,
            "stage": stage,
            "saved_at": datetime.now().isoformat(),
            "data": data,
        }

        file_path = task_dir / f"{stage}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False, default=str)
            logger.debug(f"检查点已保存: {task_id}/{stage}")
            return file_path
        except Exception as e:
            raise CheckpointError(f"保存检查点失败: {e}") from e

    def load_checkpoint(
        self,
        task_id: str,
        stage: str,
    ) -> Optional[Dict[str, Any]]:
        """加载检查点

        Args:
            task_id: 任务ID
            stage: 管道阶段名称

        Returns:
            Optional[Dict[str, Any]]: 检查点数据，不存在则返回None
        """
        file_path = self.base_dir / task_id / f"{stage}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
            logger.debug(f"检查点已加载: {task_id}/{stage}")
            return checkpoint.get("data")
        except Exception as e:
            logger.warning(f"加载检查点失败: {task_id}/{stage}, {e}")
            return None

    def has_checkpoint(self, task_id: str, stage: str) -> bool:
        """检查检查点是否存在

        Args:
            task_id: 任务ID
            stage: 管道阶段名称

        Returns:
            bool: 是否存在
        """
        file_path = self.base_dir / task_id / f"{stage}.json"
        return file_path.exists()

    def list_checkpoints(self, task_id: str) -> List[str]:
        """列出任务的所有检查点

        Args:
            task_id: 任务ID

        Returns:
            List[str]: 检查点阶段名称列表
        """
        task_dir = self.base_dir / task_id
        if not task_dir.exists():
            return []

        return [
            f.stem
            for f in sorted(task_dir.glob("*.json"))
        ]

    def cleanup_task(self, task_id: str) -> None:
        """清理任务的所有检查点

        Args:
            task_id: 任务ID
        """
        task_dir = self.base_dir / task_id
        if task_dir.exists():
            import shutil
            shutil.rmtree(task_dir)
            logger.debug(f"检查点已清理: {task_id}")

    def cleanup_old(self, max_age_hours: int = 24) -> int:
        """清理过期检查点

        Args:
            max_age_hours: 最大保留小时数

        Returns:
            int: 清理的任务数量
        """
        import shutil
        cleaned = 0
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)

        if not self.base_dir.exists():
            return 0

        for task_dir in self.base_dir.iterdir():
            if not task_dir.is_dir():
                continue

            # 检查目录下最新文件的修改时间
            latest_mtime = 0.0
            for f in task_dir.glob("*.json"):
                latest_mtime = max(latest_mtime, f.stat().st_mtime)

            if latest_mtime > 0 and latest_mtime < cutoff:
                shutil.rmtree(task_dir)
                cleaned += 1

        if cleaned > 0:
            logger.info(f"清理了 {cleaned} 个过期检查点")
        return cleaned

    def save_apps_checkpoint(
        self,
        task_id: str,
        stage: str,
        apps_data: List[AppInfo],
    ) -> Path:
        """保存应用数据检查点（便捷方法）

        Args:
            task_id: 任务ID
            stage: 管道阶段名称
            apps_data: 应用数据列表

        Returns:
            Path: 检查点文件路径
        """
        data = {
            "apps": [app.model_dump() for app in apps_data],
            "count": len(apps_data),
        }
        return self.save_checkpoint(task_id, stage, data)

    def load_apps_checkpoint(
        self,
        task_id: str,
        stage: str,
    ) -> Optional[List[AppInfo]]:
        """加载应用数据检查点（便捷方法）

        Args:
            task_id: 任务ID
            stage: 管道阶段名称

        Returns:
            Optional[List[AppInfo]]: 应用数据列表
        """
        data = self.load_checkpoint(task_id, stage)
        if data is None:
            return None

        try:
            return [AppInfo(**app) for app in data.get("apps", [])]
        except Exception as e:
            logger.warning(f"解析应用数据检查点失败: {e}")
            return None
