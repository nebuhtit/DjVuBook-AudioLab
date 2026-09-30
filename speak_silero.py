#!/usr/bin/env python3
"""Офлайн-озвучивание русского текста Silero v5.5 с экспортом в MP3."""
from __future__ import annotations
import re
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import torch
import imageio_ffmpeg


def chunks(text: str, limit: int = 700, sentence_pause: float = 0.6, paragraph_pause: float = 1.8):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", text, flags=re.M)
    text = re.sub(r"^\s*\d{1,4}\s*$", " ", text, flags=re.M)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"\|", ". ", text)
    text = re.sub(r"[*_~`#]", "", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    result: list[tuple[str, float]] = []
    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[.!?…])\s+", paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        for sentence_index, sentence in enumerate(sentences):
            parts=[]
            while len(sentence) > limit:
                cut = sentence.rfind(" ", 0, limit)
                if cut < limit // 2:
                    cut = limit
                part, sentence = sentence[:cut].strip(), sentence[cut:].strip()
                parts.append(part)
            if sentence:
                parts.append(sentence)
            final_sentence = sentence_index == len(sentences)-1
            for part_index, part in enumerate(parts):
                is_final_part=part_index == len(parts)-1
                pause=(paragraph_pause if final_sentence else sentence_pause) if is_final_part else min(0.3,sentence_pause)
                result.append((part,pause))
    return result


def main():
    if len(sys.argv) not in (5,8):
        raise SystemExit("Использование: speak_silero.py text.txt output.mp3 model.pt speaker [speed sentence_pause paragraph_pause]")
    text_path, output_path, model_path = map(Path, sys.argv[1:4])
    speaker = sys.argv[4]
    speed=float(sys.argv[5]) if len(sys.argv)==8 else 1.0
    sentence_pause=float(sys.argv[6]) if len(sys.argv)==8 else 0.6
    paragraph_pause=float(sys.argv[7]) if len(sys.argv)==8 else 1.8
    if not 0.7 <= speed <= 1.5 or not 0.2 <= sentence_pause <= 2.0 or not 0.8 <= paragraph_pause <= 5.0:
        raise SystemExit("Скорость или пауза вне допустимого диапазона")
    text = text_path.read_text(encoding="utf-8")
    units = chunks(text,sentence_pause=sentence_pause,paragraph_pause=paragraph_pause)
    if not units:
        raise SystemExit("Нет текста для озвучивания")
    model_name = "Silero v3 English" if model_path.name == "v3_en.pt" else "Silero v5.5 Russian"
    print(f"{model_name}: голос {speaker}; частей: {len(units)}; скорость {speed:.2f}×; паузы {sentence_pause:.1f}/{paragraph_pause:.1f} с", flush=True)
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
