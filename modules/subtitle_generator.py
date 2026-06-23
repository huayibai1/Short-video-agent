from __future__ import annotations

from pathlib import Path


def _timestamp(seconds: float) -> str:
    millis = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    hrs = total // 3600
    mins = (total % 3600) // 60
    secs = total % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _ass_timestamp(seconds: float) -> str:
    total_cs = int(round(seconds * 100))
    cs = total_cs % 100
    total = total_cs // 100
    hrs = total // 3600
    mins = (total % 3600) // 60
    secs = total % 60
    return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace("{", "").replace("}", "").replace("\n", "\\N")


def write_srt(plan: dict, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    for scene in plan["scenes"]:
        blocks.append(
            "\n".join(
                [
                    str(scene["index"]),
                    f"{_timestamp(scene['start'])} --> {_timestamp(scene['end'])}",
                    scene["subtitle"],
                ]
            )
        )
    output_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return output_path


def write_ass(plan: dict, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "Collisions: Normal",
        "PlayResX: 720",
        "PlayResY: 1280",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Microsoft YaHei,42,&H00FFFFFF,&H000000FF,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,3,1,2,54,54,92,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for scene in plan["scenes"]:
        lines.append(
            "Dialogue: 0,{start},{end},Default,,0,0,0,,{text}".format(
                start=_ass_timestamp(scene["start"]),
                end=_ass_timestamp(scene["end"]),
                text=_ass_escape(scene.get("subtitle") or scene.get("narration") or ""),
            )
        )
    # UTF-8 with BOM helps Windows ffmpeg/libass detect Chinese subtitles reliably.
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return output_path
