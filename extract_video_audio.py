#!/usr/bin/env python3
"""Extract the first audio track from a video to a high-quality MP3 offline."""
from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path


_process: subprocess.Popen[str] | None = None


def stop_child(signum: int, _frame: object) -> None:
    if _process is not None and _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _process.kill()
    raise SystemExit(128 + signum)


def main() -> int:
    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    if len(sys.argv) != 3:
        print("Usage: extract_video_audio.py INPUT_VIDEO OUTPUT.mp3", file=sys.stderr)
        return 2

    source, output = map(Path, sys.argv[1:])
    if not source.is_file():
        print(f"Видео не найдено: {source}", file=sys.stderr)
        return 2
    if output.suffix.lower() != ".mp3":
        print("Файл результата должен иметь расширение .mp3", file=sys.stderr)
        return 2

    try:
        import imageio_ffmpeg
    except ImportError:
        print("В выбранном окружении не найден imageio-ffmpeg.", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Видео: {source.name}", flush=True)
    print("Извлекаю первую аудиодорожку в MP3 без перекодирования видео…", flush=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-hide_banner", "-y",
        "-i", str(source), "-map", "0:a:0", "-vn", "-codec:a", "libmp3lame",
        "-q:a", "2", "-progress", "pipe:1", str(output),
    ]
    global _process
    _process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert _process.stdout is not None
    for line in _process.stdout:
        line = line.strip()
        if line.startswith("out_time=") or line.startswith("progress="):
            print(f"FFmpeg {line}", flush=True)
        elif line:
            print(line, flush=True)
    code = _process.wait()
    _process = None
    if code:
        output.unlink(missing_ok=True)
        print("Не удалось извлечь звук. Проверьте, что видео содержит аудиодорожку.", file=sys.stderr)
        return code
    if not output.is_file() or output.stat().st_size == 0:
        print("FFmpeg завершился без MP3-файла.", file=sys.stderr)
        return 1
    print(f"Готово: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
