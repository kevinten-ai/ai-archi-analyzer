"""检查点管理器测试"""

import json
import pytest
import tempfile
from pathlib import Path

from src.collectors.base import AppInfo
from src.core.checkpoint import CheckpointManager


class TestCheckpointManager:
    """CheckpointManager 测试"""

    @pytest.fixture
    def checkpoint_dir(self, tmp_path):
        return str(tmp_path / "checkpoints")

    @pytest.fixture
    def manager(self, checkpoint_dir):
        return CheckpointManager(base_dir=checkpoint_dir)

    def test_save_and_load_checkpoint(self, manager):
        """测试保存和加载检查点"""
        data = {"key": "value", "count": 42}
        manager.save_checkpoint("task-1", "collecting", data)

        loaded = manager.load_checkpoint("task-1", "collecting")
        assert loaded is not None
        assert loaded["key"] == "value"
        assert loaded["count"] == 42

    def test_load_nonexistent_checkpoint(self, manager):
        """测试加载不存在的检查点"""
        result = manager.load_checkpoint("nonexistent", "stage")
        assert result is None

    def test_has_checkpoint(self, manager):
        """测试检查点存在检查"""
        manager.save_checkpoint("task-1", "collecting", {"data": True})

        assert manager.has_checkpoint("task-1", "collecting") is True
        assert manager.has_checkpoint("task-1", "analyzing") is False
        assert manager.has_checkpoint("task-2", "collecting") is False

    def test_list_checkpoints(self, manager):
        """测试列出检查点"""
        manager.save_checkpoint("task-1", "collecting", {})
        manager.save_checkpoint("task-1", "processing", {})
        manager.save_checkpoint("task-1", "analyzing", {})

        checkpoints = manager.list_checkpoints("task-1")
        assert len(checkpoints) == 3
        assert "collecting" in checkpoints
        assert "processing" in checkpoints
        assert "analyzing" in checkpoints

    def test_list_checkpoints_empty(self, manager):
        """测试列出空检查点"""
        assert manager.list_checkpoints("nonexistent") == []

    def test_cleanup_task(self, manager):
        """测试清理任务检查点"""
        manager.save_checkpoint("task-1", "collecting", {})
        manager.save_checkpoint("task-1", "processing", {})

        manager.cleanup_task("task-1")

        assert manager.list_checkpoints("task-1") == []
        assert manager.load_checkpoint("task-1", "collecting") is None

    def test_save_and_load_apps_checkpoint(self, manager):
        """测试应用数据检查点"""
        apps = [
            AppInfo(app_id="app1", name="服务A", language="Java"),
            AppInfo(app_id="app2", name="服务B", language="Go"),
        ]
        manager.save_apps_checkpoint("task-1", "collecting", apps)

        loaded = manager.load_apps_checkpoint("task-1", "collecting")
        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0].app_id == "app1"
        assert loaded[1].language == "Go"

    def test_load_apps_checkpoint_nonexistent(self, manager):
        """测试加载不存在的应用数据检查点"""
        result = manager.load_apps_checkpoint("task-1", "stage")
        assert result is None

    def test_checkpoint_file_is_valid_json(self, manager, checkpoint_dir):
        """测试检查点文件是有效JSON"""
        manager.save_checkpoint("task-1", "test", {"key": "值"})

        file_path = Path(checkpoint_dir) / "checkpoints" / "task-1" / "test.json"
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        assert content["task_id"] == "task-1"
        assert content["stage"] == "test"
        assert content["data"]["key"] == "值"
        assert "saved_at" in content

    def test_multiple_tasks(self, manager):
        """测试多任务独立检查点"""
        manager.save_checkpoint("task-1", "collecting", {"task": 1})
        manager.save_checkpoint("task-2", "collecting", {"task": 2})

        data1 = manager.load_checkpoint("task-1", "collecting")
        data2 = manager.load_checkpoint("task-2", "collecting")

        assert data1["task"] == 1
        assert data2["task"] == 2

    def test_overwrite_checkpoint(self, manager):
        """测试覆盖检查点"""
        manager.save_checkpoint("task-1", "stage", {"version": 1})
        manager.save_checkpoint("task-1", "stage", {"version": 2})

        data = manager.load_checkpoint("task-1", "stage")
        assert data["version"] == 2
