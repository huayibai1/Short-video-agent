from __future__ import annotations

import math
import json
from dataclasses import dataclass, asdict
from typing import Any

from .llm_client import LLMError, chat_completion, extract_json_object


@dataclass
class Scene:
    index: int
    start: float
    end: float
    duration: float
    visual: str
    narration: str
    subtitle: str
    asset_keyword: str
    image_prompt: str
    video_prompt: str


def _style_words(style: str) -> dict[str, str]:
    style = (style or "").strip()
    if "科技" in style or "未来" in style:
        return {
            "tone": "冷静、清晰、有未来感",
            "pace": "快速推进",
            "visual": "城市光线、数据界面、校园科技场景",
        }
    if "温暖" in style or "治愈" in style:
        return {
            "tone": "温暖、亲切、有陪伴感",
            "pace": "平稳叙事",
            "visual": "校园晨光、学习桌面、人物生活瞬间",
        }
    if "幽默" in style or "轻松" in style:
        return {
            "tone": "轻松、有梗、节奏明快",
            "pace": "快节奏转场",
            "visual": "夸张表情、弹幕感文字、生活化镜头",
        }
    return {
        "tone": "清晰、专业、适合短视频传播",
        "pace": "由问题到答案逐步推进",
        "visual": "主题相关场景、信息图、人物行动镜头",
    }


def _split_duration(total_seconds: int, scene_count: int) -> list[float]:
    raw = total_seconds / scene_count
    durations = [round(raw, 2) for _ in range(scene_count)]
    diff = round(total_seconds - sum(durations), 2)
    durations[-1] = round(durations[-1] + diff, 2)
    return durations


def generate_plan(
    topic: str,
    title: str = "",
    custom_prompt: str = "",
    audience: str = "大学生",
    style: str = "科技感",
    duration_seconds: int = 60,
    scene_count: int | None = None,
) -> dict[str, Any]:
    topic = (topic or "未命名主题").strip()
    title = (title or "").strip()
    custom_prompt = (custom_prompt or "").strip()
    audience = (audience or "大学生").strip()
    style = (style or "科技感").strip()
    duration_seconds = max(30, min(int(duration_seconds or 60), 120))
    scene_count = scene_count or 15
    scene_count = max(3, min(int(scene_count), 15))
    words = _style_words(style)
    durations = _split_duration(duration_seconds, scene_count)

    final_title = title or f"{topic}：{duration_seconds}秒短视频"
    summary = (
        f"面向{audience}，用{words['tone']}的表达，在{duration_seconds}秒内解释"
        f"“{topic}”的核心信息。"
    )
    if custom_prompt:
        summary += f" 用户创作要求：{custom_prompt}"

    beats = [
        ("开场钩子", f"{topic}，正在走进日常。", "强钩子标题画面"),
        ("提出问题", f"它对{audience}到底改变了什么？", "问题文字和人物停顿"),
        ("信息获取", "资料先整理，重点更快出现。", "资料、搜索、知识卡片"),
        ("学习方式", "难点被拆开，提示一步一步来。", "课堂、笔记、分层提示"),
        ("创作效率", "文案、图片、视频，都能先出初稿。", "创作软件和时间轴"),
        ("时间管理", "计划、复盘、提醒，更及时。", "日程、清单、提醒"),
        ("能力边界", "AI 提升效率，但不能代替判断。", "警示对比画面"),
        ("正确方法", "先要框架，再核事实，最后改表达。", "人机协作流程"),
        ("风险提醒", "隐私、版权、准确性，都要检查。", "安全锁、风险提示"),
        ("学习案例", "做展示时，先提纲，再脚本，再演练。", "演示文稿和脚本"),
        ("价值总结", f"核心不是替代人，而是放大{audience}的思考。", "人物思考和上升曲线"),
        ("行动一", "从一个真实任务开始使用。", "任务卡片"),
        ("行动二", "把输出当草稿，继续追问。", "草稿批注"),
        ("行动三", "至少修改一次，再提交。", "判断清单"),
        ("收束", "问题问清楚，结果才用得扎实。", "收束字幕"),
        ("结尾号召", "今天就选一个小任务试试。", "结尾行动按钮"),
        ("备用补充", "会提问的人，更能掌控工具。", "未来校园"),
        ("备用收尾", "真正的改变，从下一次实践开始。", "片尾标题"),
        ("备用强调", "别只追热点，要形成方法。", "方法论关键词"),
        ("备用片尾", "收藏思路，下次直接用。", "收藏提示"),
    ]

    selected = beats[:scene_count]
    scenes: list[Scene] = []
    cursor = 0.0
    for idx, (label, narration, visual_hint) in enumerate(selected, start=1):
        duration = durations[idx - 1]
        start = cursor
        end = cursor + duration
        cursor = end
        subtitle = narration
        visual = f"{label}：{visual_hint}。画面风格：{words['visual']}，节奏：{words['pace']}。"
        keyword = f"{topic} {label} {visual_hint}"
        image_prompt = (
            f"竖屏9:16，真实短视频摄影风格，{words['visual']}，{visual_hint}，"
            f"主题是{topic}，画面干净，无文字，无水印，适合作为视频生成参考图。"
        )
        video_prompt = (
            f"基于参考图生成3-5秒竖屏短视频，{visual_hint}，镜头运动自然，"
            f"风格{style}，无字幕，无水印，无乱码文字。"
        )
        scenes.append(
            Scene(
                index=idx,
                start=round(start, 2),
                end=round(end, 2),
                duration=round(duration, 2),
                visual=visual,
                narration=narration,
                subtitle=subtitle,
                asset_keyword=keyword,
                image_prompt=image_prompt,
                video_prompt=video_prompt,
            )
        )

    voiceover = "\n".join(scene.narration for scene in scenes)
    return {
        "title": final_title,
        "topic": topic,
        "custom_prompt": custom_prompt,
        "audience": audience,
        "style": style,
        "duration_seconds": duration_seconds,
        "scene_count": scene_count,
        "summary": summary,
        "voiceover": voiceover,
        "scenes": [asdict(scene) for scene in scenes],
        "generation_mode": "template",
        "rag_sources": [],
    }


def _normalize_llm_plan(plan: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    scenes = plan.get("scenes") or []
    scene_count = fallback["scene_count"]
    durations = _split_duration(fallback["duration_seconds"], scene_count)
    normalized_scenes = []
    cursor = 0.0
    fallback_scenes = fallback["scenes"]
    for idx in range(scene_count):
        raw = scenes[idx] if idx < len(scenes) and isinstance(scenes[idx], dict) else {}
        backup = fallback_scenes[idx]
        duration = durations[idx]
        start = cursor
        end = cursor + duration
        cursor = end
        narration = str(raw.get("narration") or raw.get("subtitle") or backup["narration"]).strip()
        subtitle = str(raw.get("subtitle") or narration).strip()
        visual = str(raw.get("visual") or backup["visual"]).strip()
        asset_keyword = str(raw.get("asset_keyword") or backup["asset_keyword"]).strip()
        image_prompt = str(raw.get("image_prompt") or backup.get("image_prompt", "")).strip()
        video_prompt = str(raw.get("video_prompt") or backup.get("video_prompt", "")).strip()
        normalized_scenes.append(
            {
                "index": idx + 1,
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "visual": visual,
                "narration": narration,
                "subtitle": subtitle,
                "asset_keyword": asset_keyword,
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
            }
        )
    voiceover = "\n".join(scene["narration"] for scene in normalized_scenes)
    return {
        "title": str(plan.get("title") or fallback["title"]).strip(),
        "topic": fallback["topic"],
        "custom_prompt": fallback.get("custom_prompt", ""),
        "audience": fallback["audience"],
        "style": fallback["style"],
        "duration_seconds": fallback["duration_seconds"],
        "scene_count": scene_count,
        "summary": str(plan.get("summary") or fallback["summary"]).strip(),
        "voiceover": voiceover,
        "scenes": normalized_scenes,
        "generation_mode": "llm",
        "rag_sources": fallback.get("rag_sources", []),
    }


def generate_plan_with_llm(
    topic: str,
    title: str = "",
    custom_prompt: str = "",
    audience: str = "大学生",
    style: str = "科技感",
    duration_seconds: int = 60,
    scene_count: int | None = None,
    rag_context: str = "",
    rag_sources: list[dict[str, Any]] | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    fallback = generate_plan(topic, title, custom_prompt, audience, style, duration_seconds, scene_count)
    fallback["rag_sources"] = rag_sources or []
    system = (
        "你是一个短视频策划 Agent。请输出严格 JSON，不要 Markdown。"
        "JSON 字段必须包含 title, summary, voiceover, scenes。"
        "scenes 是数组，每个元素必须包含 visual, narration, subtitle, asset_keyword, image_prompt, video_prompt。"
        "旁白要短，字幕适合手机竖屏阅读。"
    )
    user = f"""
请生成一个中文短视频方案。

主题：{fallback['topic']}
用户指定标题：{fallback['title']}
用户自定义生成提示词：
{fallback.get('custom_prompt') or '无'}
受众：{fallback['audience']}
风格：{fallback['style']}
时长：{fallback['duration_seconds']} 秒
分镜数量：{fallback['scene_count']} 个

RAG 检索到的参考资料：
{rag_context or '无'}

要求：
1. 分镜数量必须是 {fallback['scene_count']} 个。
2. 每个分镜都要有 visual、narration、subtitle、asset_keyword、image_prompt、video_prompt。
3. image_prompt 用于生图模型生成 I2V 参考图，必须详细描述画面主体、场景、光线、构图，要求无文字无水印。
4. video_prompt 用于视频模型基于参考图生成动态片段，必须描述镜头运动、动作、氛围，要求无字幕无水印。
5. 总旁白控制在适合 {fallback['duration_seconds']} 秒配音的长度。
6. 必须优先遵循“用户自定义生成提示词”，不要替换成默认测试主题。
7. 内容要结合 RAG 参考资料，但不要编造来源。
"""
    try:
        text = chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.75,
            timeout=timeout,
        )
        raw_plan = extract_json_object(text)
        return _normalize_llm_plan(raw_plan, fallback)
    except (LLMError, json.JSONDecodeError, ValueError) as exc:
        fallback["generation_mode"] = "template_fallback"
        fallback["llm_error"] = str(exc)
        return fallback


def plan_to_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# {plan['title']}",
        "",
        f"- 主题：{plan['topic']}",
        f"- 受众：{plan['audience']}",
        f"- 风格：{plan['style']}",
        f"- 时长：{plan['duration_seconds']} 秒",
        f"- 分镜：{plan['scene_count']} 个",
        "",
        "## 视频概述",
        plan["summary"],
        "",
        "## 配音文案",
        plan["voiceover"],
        "",
        "## 分镜表",
        "| # | 时间 | 画面 | 配音/字幕 | 素材关键词 |",
        "|---|---|---|---|---|",
    ]
    for scene in plan["scenes"]:
        lines.append(
            "| {index} | {start:.2f}-{end:.2f}s | {visual} | {subtitle} | {asset_keyword} |".format(
                **scene
            )
        )
    return "\n".join(lines) + "\n"
