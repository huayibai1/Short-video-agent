from __future__ import annotations

import subprocess
import wave
from pathlib import Path


def _write_silent_wav(output_path: Path, seconds: int = 60, sample_rate: int = 16000) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"\x00\x00" * sample_rate * max(1, int(seconds))
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)
    return output_path


def synthesize_voice(text: str, output_path: str | Path, fallback_seconds: int = 60) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text_path = output_path.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")

    ps_script = f"""
Add-Type -AssemblyName System.Speech
$text = Get-Content -LiteralPath '{text_path}' -Raw -Encoding UTF8
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $synth.GetInstalledVoices() | Where-Object {{
    $_.VoiceInfo.Culture.Name -like 'zh-*' -or $_.VoiceInfo.Name -match 'Huihui|Yaoyao|Kangkang|Chinese'
}} | Select-Object -First 1
if ($voice) {{ $synth.SelectVoice($voice.VoiceInfo.Name) }}
$synth.Rate = 1
$synth.Volume = 100
$synth.SetOutputToWaveFile('{output_path}')
$synth.Speak($text)
$synth.Dispose()
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1000:
            return output_path
    except Exception:
        pass
    return _write_silent_wav(output_path, fallback_seconds)

