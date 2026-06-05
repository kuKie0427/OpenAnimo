from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class PlanOutputValidator:
    """验证 Agent 产出物是否符合约束。返回问题列表，空列表 = 通过。"""

    def validate_characters(self, data: dict, hints: list[str] | None = None) -> list[str]:
        """验证 characters 产出：hints 匹配 + 必填字段"""
        issues: list[str] = []
        hints = hints or []

        # 1. character_hints 全部匹配
        if hints:
            generated_names = {c.get("name", "") for c in data.get("characters", [])}
            for hint in hints:
                if not any(hint in name for name in generated_names):
                    issues.append(f"character_hint '{hint}' not matched")

        # 2. 必填字段
        for i, char in enumerate(data.get("characters", [])):
            for field in ["name", "description"]:
                if not char.get(field):
                    issues.append(f"characters[{i}] missing required field: {field}")

        return issues

    def validate_shots(self, data: dict, target_count: int | None = None) -> list[str]:
        """验证 shots 产出：shot count 匹配"""
        issues: list[str] = []
        if target_count is not None:
            actual = len(data.get("shots", []))
            if actual != target_count:
                issues.append(f"shot count mismatch: expected {target_count}, got {actual}")
        return issues
