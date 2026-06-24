"""任务管理器 - 跟踪和取消后台任务"""
from __future__ import annotations

import asyncio
from typing import Dict


class TaskManager:
    """管理后台任务，支持取消"""

    def __init__(self) -> None:
        # project_id -> task
        self._tasks: Dict[int, asyncio.Task] = {}

    def register(self, project_id: int, task: asyncio.Task) -> None:
        """注册一个任务"""
        # 如果有旧任务，先取消
        old_task = self._tasks.get(project_id)
        if old_task and not old_task.done():
            old_task.cancel()
        self._tasks[project_id] = task

    def cancel(self, project_id: int) -> bool:
        """取消指定项目的任务，返回是否成功取消"""
        task = self._tasks.get(project_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def remove(self, project_id: int) -> None:
        """移除任务记录"""
        self._tasks.pop(project_id, None)

    def is_running(self, project_id: int) -> bool:
        """检查项目是否有运行中的任务"""
        task = self._tasks.get(project_id)
        return task is not None and not task.done()


# 全局单例
task_manager = TaskManager()
