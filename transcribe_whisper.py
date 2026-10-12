#!/usr/bin/env python3
"""Transcribe an audio file locally with whisper.cpp and an installed ggml model."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


_active_process: subprocess.Popen[str] | None = None


def stop_child(signum: int, _frame: object) -> None:
    """Ensure stopping the app also stops the whisper worker it launched."""
    if _active_process is not None and _active_process.poll() is None:
        _active_process.terminate()
        try:
            _active_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _active_process.kill()
    raise SystemExit(128 + signum)


def main() -> int:
    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    if len(sys.argv) != 6:
        print("Usage: transcribe_whisper.py INPUT OUTPUT.txt MODEL WHISPER_CLI LANGUAGE", file=sys.stderr)
        return 2

    source, output, model, whisper_cli = map(Path, sys.argv[1:5])
    language = sys.argv[5]
    if language not in {"ru", "en"}:
        print("Language must be ru or en", file=sys.stderr)
        return 2
    if not source.is_file() or not model.is_file() or not whisper_cli.is_file():
        print("Не найдены аудиофайл, модель Whisper или whisper-cli.", file=sys.stderr)
        return 2

    try:
        import imageio_ffmpeg
    except ImportError:
        print("В окружении озвучивания не найден imageio-ffmpeg для подготовки аудио.", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="audiolab-stt-") as temporary:
        wav = Path(temporary) / "input-16khz-mono.wav"
        print("Подготавливаю аудио для локального распознавания…", flush=True)
        convert = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
             "-i", str(source), "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
            capture_output=True, text=True,
        )
        if convert.returncode:
            print(convert.stderr.strip() or "Не удалось прочитать аудиофайл.", file=sys.stderr)
            return convert.returncode

        output_base = output.with_suffix("")
        command = [
            str(whisper_cli), "--model", str(model), "--file", str(wav),
            "--language", language, "--no-timestamps", "--output-txt", "--output-file", str(output_base),
            "--threads", str(max(2, min((os.cpu_count() or 4) - 2, 8))), "--no-gpu",
        ]
        print(f"Whisper: модель {model.name}; язык {'русский' if language == 'ru' else 'English'}; офлайн.", flush=True)
        global _active_process
        _active_process = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stdout, text=True)
        result_code = _active_process.wait()
        _active_process = None
        if result_code:
            return result_code

    generated = output_base.with_suffix(".txt")
    if generated != output and generated.exists():
        generated.replace(output)
    if not output.is_file() or not output.read_text(encoding="utf-8").strip():
        print("Whisper не вернул текст. Проверьте, что в записи есть разборчивая речь.", file=sys.stderr)
        return 1
    print(f"Распознавание завершено: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
