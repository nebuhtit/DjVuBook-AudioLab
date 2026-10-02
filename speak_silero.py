#!/usr/bin/env python3
"""Офлайн-озвучивание русского текста Silero v5.5 с экспортом в MP3."""
from __future__ import annotations
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import torch
import imageio_ffmpeg
from speech_text import chunks

def main():
    if len(sys.argv) not in (5,9,10):
        raise SystemExit("Использование: speak_silero.py text.txt output.mp3 model.pt speaker [speed sentence_pause paragraph_pause punctuation_pause read_numbers]")
    text_path, output_path, model_path = map(Path, sys.argv[1:4])
    speaker = sys.argv[4]
    speed=float(sys.argv[5]) if len(sys.argv)>=9 else 1.0
    sentence_pause=float(sys.argv[6]) if len(sys.argv)>=9 else 0.6
    paragraph_pause=float(sys.argv[7]) if len(sys.argv)>=9 else 1.8
    punctuation_pause=float(sys.argv[8]) if len(sys.argv)>=9 else 0.25
    read_numbers = sys.argv[9] != "0" if len(sys.argv) == 10 else True
    if not 0.7 <= speed <= 1.5 or not 0.2 <= sentence_pause <= 2.0 or not 0.8 <= paragraph_pause <= 5.0 or not 0.05 <= punctuation_pause <= 1.0:
        raise SystemExit("Скорость или пауза вне допустимого диапазона")
    text = text_path.read_text(encoding="utf-8")
    is_english=model_path.name == "v3_en.pt"
    units = chunks(text,sentence_pause=sentence_pause,paragraph_pause=paragraph_pause,punctuation_pause=punctuation_pause,language="en" if is_english else "ru",read_numbers=read_numbers)
    if not units:
        raise SystemExit("Нет текста для озвучивания")
    model_name = "Silero v3 English" if is_english else "Silero v5.5 Russian"
    print(f"{model_name}: голос {speaker}; частей: {len(units)}; скорость {speed:.2f}×; паузы {sentence_pause:.1f}/{paragraph_pause:.1f}/{punctuation_pause:.2f} с", flush=True)
    torch.set_num_threads(2)
    model = torch.package.PackageImporter(str(model_path)).load_pickle("tts_models", "model")
    model.to(torch.device("cpu"))
    print("Модель загружена; начинаю озвучивать", flush=True)
    with tempfile.TemporaryDirectory(prefix="audiolab-tts-") as work:
        wav_path = Path(work) / "speech.wav"
        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            for index, (part,pause_after) in enumerate(units, 1):
                samples = model.apply_tts(text=part, speaker=speaker, sample_rate=48000)
                pcm = (samples.clamp(-1, 1) * 32767).short().cpu().numpy().tobytes()
                wav.writeframes(pcm)
                if index < len(units):
                    # atempo shortens silence too; scale frames so the chosen pause survives unchanged.
                    silent_frames=round(pause_after*speed*48000)
                    wav.writeframes(b"\x00\x00" * silent_frames)
                print(f"Озвучено частей: {index}/{len(units)}", flush=True)
        result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_path), "-af", f"atempo={speed:.3f}", "-codec:a", "libmp3lame", "-q:a", "3", str(output_path)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Системный конвертер не смог создать MP3")
    print(f"Готово: {output_path}", flush=True)


if __name__ == "__main__":
    main()
