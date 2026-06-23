from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _ffmpeg_exe() -> str | None:
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _ffmpeg_path(path: str | Path) -> str:
    return str(Path(path).resolve()).replace("\\", "/").replace(":", "\\:")


def _run_ffmpeg(cmd: list[str], timeout: int = 240) -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return result.returncode == 0


def build_silent_video(
    plan: dict,
    scene_images: list[Path],
    output_path: str | Path,
    fps: int = 24,
    size: tuple[int, int] = (720, 1280),
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV VideoWriter could not open mp4 output.")

    for scene, image_path in zip(plan["scenes"], scene_images):
        image = Image.open(image_path).convert("RGB").resize(size)
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        frame_count = max(1, int(round(scene["duration"] * fps)))
        for i in range(frame_count):
            # Subtle motion avoids a fully static slideshow.
            alpha = 1.0 + (i / max(1, frame_count - 1)) * 0.035
            crop_w = int(width / alpha)
            crop_h = int(height / alpha)
            x0 = (width - crop_w) // 2
            y0 = (height - crop_h) // 2
            cropped = frame[y0 : y0 + crop_h, x0 : x0 + crop_w]
            animated = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)
            writer.write(animated)
    writer.release()
    return output_path


def build_video_from_mixed_assets(
    plan: dict,
    scene_images: list[Path],
    scene_videos: dict[int, Path],
    output_path: str | Path,
    fps: int = 24,
    size: tuple[int, int] = (720, 1280),
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_exe()
    if not scene_videos or not ffmpeg:
        return build_silent_video(plan, scene_images, output_path, fps=fps, size=size)

    temp_dir = output_path.parent / "_segments"
    temp_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    image_by_index = {idx + 1: path for idx, path in enumerate(scene_images)}
    for scene in plan["scenes"]:
        idx = int(scene["index"])
        segment_path = temp_dir / f"segment_{idx:02d}.mp4"
        duration = str(scene["duration"])
        if idx in scene_videos:
            cmd = [
                ffmpeg,
                "-y",
                "-i",
                str(scene_videos[idx]),
                "-t",
                duration,
                "-vf",
                f"scale={size[0]}:{size[1]}:force_original_aspect_ratio=increase,crop={size[0]}:{size[1]},setsar=1",
                "-an",
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(segment_path),
            ]
        else:
            cmd = [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(image_by_index[idx]),
                "-t",
                duration,
                "-vf",
                f"scale={size[0]}:{size[1]},setsar=1",
                "-an",
                "-r",
                str(fps),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                str(segment_path),
            ]
        if not _run_ffmpeg(cmd):
            return build_silent_video(plan, scene_images, output_path, fps=fps, size=size)
        segments.append(segment_path)

    concat_file = temp_dir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{str(path).replace(chr(92), '/')}'" for path in segments),
        encoding="utf-8",
    )
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        str(output_path),
    ]
    if not _run_ffmpeg(cmd):
        return build_silent_video(plan, scene_images, output_path, fps=fps, size=size)
    return output_path


def burn_subtitles(
    video_path: str | Path,
    subtitle_path: str | Path,
    output_path: str | Path,
    size: tuple[int, int] = (720, 1280),
) -> tuple[Path, bool]:
    video_path = Path(video_path)
    subtitle_path = Path(subtitle_path)
    output_path = Path(output_path)
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg or not subtitle_path.exists():
        shutil.copyfile(video_path, output_path)
        return output_path, False
    subtitle_filter = (
        f"subtitles='{_ffmpeg_path(subtitle_path)}':force_style="
        "'FontName=Microsoft YaHei,FontSize=20,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
        "Alignment=2,MarginV=88'"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        subtitle_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output_path),
    ]
    if not _run_ffmpeg(cmd):
        shutil.copyfile(video_path, output_path)
        return output_path, False
    return output_path, True


def mux_audio(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    subtitle_path: str | Path | None = None,
) -> tuple[Path, bool]:
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg or not audio_path.exists():
        shutil.copyfile(video_path, output_path)
        return output_path, False

    input_video = video_path
    temp_subtitled = output_path.with_name(output_path.stem + "_subtitled.mp4")
    if subtitle_path:
        input_video, _ = burn_subtitles(video_path, subtitle_path, temp_subtitled)

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_video),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
    if not _run_ffmpeg(cmd):
        shutil.copyfile(video_path, output_path)
        return output_path, False
    return output_path, True
