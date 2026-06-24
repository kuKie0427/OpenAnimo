"""TTS 语音映射 — 角色特征 → Edge TTS 语音名称

Edge TTS 提供多种中文语音，按性别和年龄分类。
本模块维护映射表，并从角色描述中推断语音类型。
"""

from __future__ import annotations

from app.models.project import Character

# 角色特征 → Edge TTS 语音名称
DEFAULT_VOICE_MAP: dict[str, str] = {
    "male_young": "zh-CN-YunxiNeural",       # 男青年
    "male_mature": "zh-CN-YunjianNeural",     # 男成熟/大叔
    "female_young": "zh-CN-XiaoxiaoNeural",   # 女青年
    "female_mature": "zh-CN-XiaoyiNeural",    # 女成熟
    "child": "zh-CN-XiaohanNeural",           # 儿童
    "narrator": "zh-CN-YunyangNeural",        # 旁白/新闻播报
}

# 反向映射：语音名称 → 语音类型（用于调试/展示）
VOICE_TO_TYPE: dict[str, str] = {v: k for k, v in DEFAULT_VOICE_MAP.items()}

# 关键词 → 语音类型
_KEYWORD_MAP: dict[str, str] = {
    # 女性青年
    "少女": "female_young",
    "女孩": "female_young",
    "姑娘": "female_young",
    "小姐": "female_young",
    "妹妹": "female_young",
    "女学生": "female_young",
    # 女性成熟
    "夫人": "female_mature",
    "阿姨": "female_mature",
    "母亲": "female_mature",
    "妈妈": "female_mature",
    "女王": "female_mature",
    "女总裁": "female_mature",
    "姐姐": "female_mature",
    # 男性青年
    "少年": "male_young",
    "男孩": "male_young",
    "青年": "male_young",
    "小哥哥": "male_young",
    "男学生": "male_young",
    "弟弟": "male_young",
    # 男性成熟
    "大叔": "male_mature",
    "父亲": "male_mature",
    "爸爸": "male_mature",
    "将军": "male_mature",
    "总裁": "male_mature",
    "老人": "male_mature",
    "爷爷": "male_mature",
    # 儿童
    "小孩": "child",
    "儿童": "child",
    "幼儿": "child",
    "萝莉": "child",
    "正太": "child",
    # 旁白
    "旁白": "narrator",
    "解说": "narrator",
    "播报": "narrator",
    "叙述": "narrator",
}

# 姓名关键词推断（常见姓氏+性别推断）
_NAME_HINTS_MALE: set[str] = {
    "先生", "君", "哥", "叔", "公", "爷", "伯",
}
_NAME_HINTS_FEMALE: set[str] = {
    "小姐", "姐", "妹", "姨", "婆", "夫人", "娘",
}


def infer_voice_type(character: Character) -> str:
    """从角色描述和名称推断语音类型

    优先级：
    1. 描述中的关键词匹配
    2. 名称中的性别提示
    3. 默认：female_young（最常见的动漫角色类型）

    Args:
        character: 角色模型实例

    Returns:
        语音类型键名（如 "male_young"、"female_mature" 等）
    """
    desc = (character.description or "").lower()
    name = character.name or ""

    # 1. 描述关键词匹配
    for keyword, voice_type in _KEYWORD_MAP.items():
        if keyword in desc:
            return voice_type

    # 2. 名称性别提示
    for hint in _NAME_HINTS_MALE:
        if hint in name:
            return "male_young"
    for hint in _NAME_HINTS_FEMALE:
        if hint in name:
            return "female_young"

    # 3. 默认
    return "female_young"


def get_voice_for_character(character: Character) -> str:
    """获取角色的 Edge TTS 语音名称

    Args:
        character: 角色模型实例

    Returns:
        Edge TTS 语音名称（如 "zh-CN-YunxiNeural"）
    """
    voice_type = infer_voice_type(character)
    return DEFAULT_VOICE_MAP.get(voice_type, DEFAULT_VOICE_MAP["female_young"])
