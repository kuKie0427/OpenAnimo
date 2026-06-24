"""Narrative beat analyzer for shot distribution.

Pure computation — maps a 3-act story outline to a per-shot beat schedule.
No LLM calls, no I/O, no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BeatAssignment:
    """Per-shot beat metadata injected into PlanAgent prompt."""
    shot_index: int          # 1-based position in shot sequence
    act: int                 # 1/2/3
    act_label: str           # "起" / "承转" / "合"
    beat_name: str           # e.g. "开场建立" / "冲突升级" / "高潮对决" / "结局收束"
    intensity: int           # 1-5 emotional intensity
    suggested_camera: str    # e.g. "中景·摇镜" / "特写·推近" / "全景·固定"
    suggested_duration: float  # recommended duration in seconds


BEAT_TEMPLATES: dict[int, list[dict]] = {
    1: [  # Act 1: 起 — Establishment
        {"beat_name": "开场建立", "intensity": 2, "camera": "全景·固定或慢摇", "dur": 4.0},
        {"beat_name": "世界展示", "intensity": 3, "camera": "中景·跟拍", "dur": 3.5},
        {"beat_name": "激励事件", "intensity": 4, "camera": "近景·推近", "dur": 3.0},
    ],
    2: [  # Act 2: 承转 — Conflict & Reversal
        {"beat_name": "冲突升级", "intensity": 4, "camera": "中景·快速切换", "dur": 2.5},
        {"beat_name": "中间转折", "intensity": 5, "camera": "特写·推近", "dur": 2.0},
        {"beat_name": "暗夜时刻", "intensity": 5, "camera": "特写·俯拍", "dur": 3.0},
        {"beat_name": "转机萌芽", "intensity": 3, "camera": "中景·摇镜", "dur": 3.5},
    ],
    3: [  # Act 3: 合 — Climax & Resolution
        {"beat_name": "高潮对决", "intensity": 5, "camera": "特写·快速推拉", "dur": 2.0},
        {"beat_name": "结局收束", "intensity": 2, "camera": "全景·固定缓推", "dur": 4.5},
        {"beat_name": "余韵落幕", "intensity": 1, "camera": "远景·慢拉", "dur": 5.0},
    ],
}

ACT_RATIOS = {1: 0.20, 2: 0.50, 3: 0.30}


def analyze_beats(
    target_shot_count: int,
    acts: list[dict] | None = None,
) -> list[BeatAssignment]:
    """Analyze narrative beats and return per-shot assignments."""
    if target_shot_count < 1:
        return []

    assignments: list[BeatAssignment] = []

    # Distribute shots across acts
    if target_shot_count <= 3:
        act_shots = (
            [(1, 1)]
            if target_shot_count == 1
            else [(1, 1), (2, 1)]
            if target_shot_count == 2
            else [(1, 1), (2, 1), (3, 1)]
        )
    else:
        act1_count = round(target_shot_count * ACT_RATIOS[1])
        act2_count = round(target_shot_count * ACT_RATIOS[2])
        act3_count = target_shot_count - act1_count - act2_count
        if act3_count < 1:
            act3_count = 1
            act2_count = max(1, target_shot_count - act1_count - act3_count)
        act_shots = [(1, act1_count), (2, act2_count), (3, act3_count)]

    shot_index = 1
    for act_num, shot_count in act_shots:
        templates = BEAT_TEMPLATES[act_num]
        for i in range(shot_count):
            beat = templates[i % len(templates)]
            dur = beat["dur"]
            if shot_count > len(templates):
                dur *= 0.9

            assignments.append(BeatAssignment(
                shot_index=shot_index,
                act=act_num,
                act_label={1: "起", 2: "承转", 3: "合"}[act_num],
                beat_name=beat["beat_name"],
                intensity=beat["intensity"],
                suggested_camera=beat["camera"],
                suggested_duration=round(dur, 1),
            ))
            shot_index += 1

    return assignments


def format_beat_schedule(assignments: list[BeatAssignment]) -> str:
    """Format beat assignments as human-readable text for LLM prompt injection."""
    if not assignments:
        return ""

    lines = ["【节拍调度表 — 请严格按此密度和时长分配分镜】", ""]
    current_act = None
    for b in assignments:
        if b.act != current_act:
            current_act = b.act
            lines.append(f"┌─ 第{b.act}幕「{b.act_label}」")
        lines.append(
            f"│ #{b.shot_index:2d} {b.beat_name} "
            f"| 强度:{b.intensity}/5 "
            f"| 时长≈{b.suggested_duration}s "
            f"| 运镜:{b.suggested_camera}"
        )
    lines.append("")
    lines.append("指令：高潮段(强度5)多分镜/短时长/戏剧性运镜，过渡段(强度1-2)少分镜/长时长/全景建立镜头。")
    return "\n".join(lines)
