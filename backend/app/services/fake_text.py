from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

from app.config import Settings
from app.services.llm import LLMResponse
from app.services.text_capabilities import TextProviderCapability


class FakeTextService:
    """Local/dev text provider that never calls external APIs.

    The fake provider is intentionally schema-aware for the built-in agents so
    a complete local generation flow can be exercised without paid API calls.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def _configured_response(self) -> str | None:
        configured = self.settings.fake_text_response
        if configured and configured.strip():
            return configured.strip()
        return None

    @staticmethod
    def _message_text(messages: list[dict[str, Any]] | None) -> str:
        parts: list[str] = []
        for message in messages or []:
            content = message.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text")
                        if isinstance(text, str):
                            parts.append(text)
        return "\n".join(parts)

    @staticmethod
    def _payload_from_text(text: str) -> dict[str, Any]:
        stripped = text.strip()
        candidates = [stripped]

        # In normal agent calls the user prompt is exactly JSON, but some test
        # harnesses/proxies wrap it with extra text. Keep fake mode resilient so
        # local E2E testing does not collapse to empty characters/shots.
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end > start:
            candidates.append(stripped[start : end + 1])

        for candidate in candidates:
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                continue
        return {}

    @staticmethod
    def _project_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
        project = payload.get("project")
        return project if isinstance(project, dict) else {}

    @staticmethod
    def _json_text(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def _outline_response(self, payload: dict[str, Any]) -> str:
        project = self._project_from_payload(payload)
        title = str(project.get("title") or "本地测试故事")
        story = str(project.get("story") or "一个角色在测试环境中完成冒险。")
        style = str(project.get("style") or "清爽漫画风")
        short_story = story[:80]
        data = {
            "agent": "outline",
            "user_message": f"Fake 大纲已生成：{short_story}",
            "story_outline": {
                "logline": f"{title}：主角在低成本本地测试中验证完整生成链路。",
                "genre": ["本地测试", "轻冒险"],
                "themes": ["验证", "协作", "成长"],
                "setting": "一间充满便签和屏幕的创作工作室",
                "tone": "轻快、明确、适合快速预览",
                "acts": [
                    {"act": 1, "title": "起", "summary": "主角提出故事想法，系统开始拆解核心冲突。"},
                    {"act": 2, "title": "承转", "summary": "角色进入测试场景，发现每个生成环节都需要稳定衔接。"},
                    {"act": 3, "title": "合", "summary": "所有 Fake 素材顺利汇合，形成可预览的漫剧片段。"},
                ],
                "emotional_arc": "从好奇到紧张排查，再到确认流程跑通后的安心。",
            },
            "visual_bible": f"{style}；明亮背景，高对比线条，角色表情清晰，构图简洁，适合本地 Fake 占位素材。",
            "project_update": {
                "title": title if title != "Untitled" else "Fake 本地测试短片",
                "summary": f"{short_story}（Fake 文本生成，本地测试不扣费）",
            },
        }
        return self._json_text(data)

    def _plan_base(self, payload: dict[str, Any]) -> dict[str, Any]:
        project = self._project_from_payload(payload)
        title = str(project.get("title") or "Fake 本地测试短片")
        style = str(project.get("style") or "清爽漫画风")
        summary = str(project.get("story") or project.get("summary") or "本地测试生成链路")[:120]
        return {
            "agent": "plan",
            "user_message": "Fake 规划已生成，可用于本地端到端测试，不会调用外部文本 API。",
            "project_update": {
                "title": title,
                "style": style,
                "status": "planning",
                "summary": summary,
            },
            "visual_bible": (
                f"{style}；稳定角色轮廓，干净背景，蓝紫色测试工作室与暖黄色想象世界形成对比；"
                "所有占位素材都应清晰标注 Fake、本地、无外部 API。"
            ),
            "story_breakdown": {
                "logline": summary,
                "genre": ["本地测试"],
                "themes": ["可靠性", "低成本验证"],
                "setting": "创作工作台与想象世界交叠的空间",
                "tone": "轻快、清晰",
            },
            "preserve_ids": {"characters": [], "shots": []},
            "characters": [],
            "shots": [],
        }

    def _character_response(self, payload: dict[str, Any]) -> str:
        data = self._plan_base(payload)
        project = self._project_from_payload(payload)
        hints = project.get("character_hints")
        characters: list[dict[str, Any]] = []
        if isinstance(hints, list) and hints:
            for idx, hint in enumerate(hints, start=1):
                text = str(hint).strip() or f"测试角色{idx}"
                name, _, desc = text.partition("：")
                characters.append(
                    {
                        "id": None,
                        "name": name.strip() or f"测试角色{idx}",
                        "description": desc.strip() or f"来自用户提示“{text}”的主要角色。",
                        "role": "protagonist" if idx == 1 else "supporting",
                        "personality_traits": ["主动", "清晰"],
                        "goals": "帮助验证本地 Fake 生成流程",
                        "costume_notes": "简洁现代服装，便于占位图呈现",
                        "visual_notes": "轮廓明确，表情友好，佩戴小型创作徽章",
                    }
                )
        else:
            characters = [
                {
                    "id": None,
                    "name": "小欧",
                    "description": "负责把故事想法推进成漫剧片段的测试主角。",
                    "role": "protagonist",
                    "personality_traits": ["好奇", "果断"],
                    "goals": "验证生成流程是否闭环",
                    "costume_notes": "蓝白色外套，胸前有播放按钮徽章",
                    "visual_notes": "黑色短发，琥珀色眼睛，中等身高，蓝白外套，胸前有黄色播放按钮徽章，表情明亮。",
                },
                {
                    "id": None,
                    "name": "调试精灵",
                    "description": "提醒主角检查配置、素材和进度状态的辅助角色。",
                    "role": "supporting",
                    "personality_traits": ["细致", "可靠"],
                    "goals": "帮助发现流程中的断点",
                    "costume_notes": "小披风和工具腰包",
                    "visual_notes": "小体型悬浮角色，青绿色发光眼睛，半透明小披风，工具腰包，手持扳手形光标。",
                },
                {
                    "id": None,
                    "name": "时间线猫",
                    "description": "守在视频时间线旁，负责把首帧、视频片段和最终拼接结果串起来的吉祥物。",
                    "role": "supporting",
                    "personality_traits": ["机灵", "爱整理"],
                    "goals": "确保每个分镜都有占位图片、占位视频和拼接结果",
                    "costume_notes": "深灰色小披肩，尾巴末端像播放进度条",
                    "visual_notes": "圆脸橘猫，绿色眼睛，小体型，深灰披肩，尾巴带黄色进度条纹，脖子挂迷你场记板。",
                },
            ]
        data["characters"] = characters
        data["user_message"] = f"已生成 {len(characters)} 个 Fake 角色设定。"
        return self._json_text(data)

    def _shot_response(self, payload: dict[str, Any]) -> str:
        data = self._plan_base(payload)
        project = self._project_from_payload(payload)
        target = project.get("target_shot_count")
        try:
            shot_count = int(target) if target is not None else 6
        except (TypeError, ValueError):
            shot_count = 6
        shot_count = max(4, min(shot_count, 8))
        shot_templates = [
            ("创作工作室", "小欧按下开始生成按钮，屏幕上亮起 Fake 三个字", "期待而专注", "中景缓慢推近", "柔和蓝色屏幕光", "开始本地测试。", "键盘轻响"),
            ("分镜白板前", "调试精灵用发光光标圈出文本、图片、视频三个开关", "认真提醒", "近景横移", "明亮顶光", "Fake 模式已开启。", "提示音"),
            ("角色展示台", "小欧、调试精灵、时间线猫依次站上旋转台", "自信亮相", "三连中景切换", "黄色轮廓光", "角色齐了！", "相机快门声"),
            ("想象世界入口", "占位图片像卡片一样从门内飞出并贴到分镜板", "惊喜", "全景拉开", "彩色轮廓光", "首帧画面出来了。", "轻快转场"),
            ("视频时间线", "时间线猫把多个 Fake 视频片段拖入轨道并自动吸附", "机灵得意", "俯拍推进", "蓝紫色工作灯", "片段开始拼接。", "轨道吸附声"),
            ("预览屏幕前", "三位角色一起观看最终合成视频，屏幕角落显示本地占位", "满意微笑", "特写定格", "温暖背光", "完整流程跑通。", "完成提示音"),
            ("设置面板", "开关状态被逐项确认，外部扣费项全部关闭", "笃定", "静态正面镜头", "清晰白光", "没有外部扣费调用。", "勾选声"),
            ("素材库", "占位图、分镜视频和最终拼接视频被归档成三排卡片", "放松", "侧向跟拍", "柔和环境光", "素材已就绪。", "文件落位声"),
        ]
        shots: list[dict[str, Any]] = []
        for idx in range(shot_count):
            scene, action, expression, camera, lighting, dialogue, sfx = shot_templates[idx]
            shots.append(
                {
                    "id": None,
                    "order": idx + 1,
                    "scene": scene,
                    "action": action,
                    "expression": expression,
                    "camera": camera,
                    "lighting": lighting,
                    "dialogue": dialogue,
                    "sfx": sfx,
                    "duration": 2.0,
                    "description": f"{scene}中，{action}，{expression}。",
                    "image_prompt": (
                        f"分镜 {idx + 1} 占位图：{scene}，{action}，{expression}，{camera}，"
                        f"{lighting}，漫画风，清晰标注 Fake Image，本地测试不调用外部图片 API。"
                    ),
                    "video_prompt": (
                        f"分镜 {idx + 1} 占位视频：{camera}展示{action}，节奏轻快，"
                        "2 秒本地 Fake Video，占位片段用于最终拼接。"
                    ),
                }
            )
        data["shots"] = shots
        data["user_message"] = f"已生成 {len(shots)} 个 Fake 分镜。"
        return self._json_text(data)

    def _full_plan_response(self, payload: dict[str, Any]) -> str:
        data = json.loads(self._character_response(payload))
        shots_data = json.loads(self._shot_response(payload))
        data["shots"] = shots_data["shots"]
        data["user_message"] = (
            f"Fake 完整规划已生成：{len(data['characters'])} 个角色、"
            f"{len(data['shots'])} 个分镜，可继续渲染占位图片和占位视频。"
        )
        return self._json_text(data)

    def _critic_response(self) -> str:
        return self._json_text(
            {
                "score": 10,
                "dimensions": {"consistency": 10, "quality": 10, "composition": 10},
                "issues": [],
                "suggestions": [],
            }
        )

    def _response_text(
        self,
        *,
        messages: list[dict[str, Any]] | None,
        prompt: str | None,
        system: str | None,
    ) -> str:
        prompt_text = "\n".join(part for part in [prompt, self._message_text(messages)] if part)
        payload = self._payload_from_text(prompt_text)
        system_text = system or ""
        combined = f"{system_text}\n{prompt_text}".lower()

        task = payload.get("task")
        if task is None:
            task_match = re.search(r'"task"\s*:\s*"(characters|shots)"', prompt_text)
            task = task_match.group(1) if task_match else None

        if task == "characters":
            return self._character_response(payload)
        if task == "shots":
            return self._shot_response(payload)
        if "planagent" in combined or "plan agent" in combined:
            return self._full_plan_response(payload)
        if "critic" in combined or "审查" in combined or "score" in combined:
            return self._critic_response()
        if "outlineagent" in combined or "story_outline" in combined:
            return self._outline_response(payload)

        configured = self._configured_response()
        if configured is not None:
            return configured
        return "这是 Fake 文本 Provider 的本地测试响应，未调用外部文本生成 API。"

    async def probe(self) -> TextProviderCapability:
        return TextProviderCapability(status="valid", generate=True, stream=True)

    async def generate(
        self,
        *,
        messages: list[dict[str, Any]] | None = None,
        prompt: str | None = None,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        text = self._response_text(messages=messages, prompt=prompt, system=system)
        return LLMResponse(text=text, tool_calls=[], raw={"provider": "fake"})

    async def stream(
        self,
        *,
        messages: list[dict[str, Any]] | None = None,
        prompt: str | None = None,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        response = await self.generate(
            messages=messages,
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        if response.text:
            yield {"type": "text", "text": response.text}
        yield {"type": "final", "response": response}
