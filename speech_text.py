"""Prepare readable speech chunks with pause durations; no TTS dependencies."""
from __future__ import annotations

import re
import sys


_NUMBERS = re.compile(r"(?<!\w)-?\d+(?:[.,]\d+)?%?")

_EN_SMALL = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
_EN_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_RU_SMALL = ("ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять", "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать")
_RU_FEM = ("ноль", "одна", "две") + _RU_SMALL[3:]
_RU_TENS = ("", "десять", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто")
_RU_HUNDREDS = ("", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот")


def _english_integer(number: int) -> str:
    if number < 20:
        return _EN_SMALL[number]
    if number < 100:
        return _EN_TENS[number // 10] + ("-" + _EN_SMALL[number % 10] if number % 10 else "")
    if number < 1000:
        tail = _english_integer(number % 100) if number % 100 else ""
        return f"{_EN_SMALL[number // 100]} hundred" + (f" {tail}" if tail else "")
    for size, name in ((10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        if number >= size:
            head, rest = divmod(number, size)
            return _english_integer(head) + " " + name + (" " + _english_integer(rest) if rest else "")
    return str(number)


def _russian_group(number: int, feminine: bool = False) -> str:
    words: list[str] = []
    hundreds, rest = divmod(number, 100)
    if hundreds:
        words.append(_RU_HUNDREDS[hundreds])
    small = _RU_FEM if feminine else _RU_SMALL
    if rest < 20:
        if rest:
            words.append(small[rest])
    else:
        tens, units = divmod(rest, 10)
        words.append(_RU_TENS[tens])
        if units:
            words.append(small[units])
    return " ".join(words)


def _russian_integer(number: int) -> str:
    if number < 1000:
        return _russian_group(number) or "ноль"
    scales = ((10**12, "триллион", "триллиона", "триллионов", False), (10**9, "миллиард", "миллиарда", "миллиардов", False), (10**6, "миллион", "миллиона", "миллионов", False), (1000, "тысяча", "тысячи", "тысяч", True))
    words: list[str] = []
    remainder = number
    for size, one, few, many, feminine in scales:
        group, remainder = divmod(remainder, size)
        if group:
            words.append(_russian_group(group, feminine))
            last_two, last = group % 100, group % 10
            form = one if last == 1 and last_two != 11 else few if 2 <= last <= 4 and not 12 <= last_two <= 14 else many
            words.append(form)
    if remainder:
        words.append(_russian_group(remainder))
    return " ".join(words)


def number_words(value: str, language: str = "ru") -> str:
    """Speak a numeric token as words. Large identifiers are read digit by digit."""
    english = language.lower().startswith("en")
    token = value
    percent = token.endswith("%")
    if percent:
        token = token[:-1]
    negative = token.startswith("-")
    token = token.lstrip("-")
    separator = "," if "," in token else "." if "." in token else None
    whole, fraction = token.split(separator, 1) if separator else (token, "")
    number = int(whole)
    formatter = _english_integer if english else _russian_integer
    if number >= 10**15:
        spoken = " ".join((_EN_SMALL if english else _RU_SMALL)[int(digit)] for digit in whole)
    else:
        spoken = formatter(number)
    if fraction:
        mark = "point" if english else "запятая"
        spoken += " " + mark + " " + " ".join((_EN_SMALL if english else _RU_SMALL)[int(digit)] for digit in fraction)
    if negative:
        spoken = ("minus " if english else "минус ") + spoken
    if percent:
        if english:
            spoken += " percent"
        else:
            last_two, last = number % 100, number % 10
            spoken += " процент" if last == 1 and last_two != 11 else " процента" if 2 <= last <= 4 and not 12 <= last_two <= 14 else " процентов"
    return spoken


def normalize_numbers(text: str, language: str = "ru", read_numbers: bool = True) -> str:
    """Expand numeric tokens, or omit them when number reading is disabled."""
    if read_numbers:
        return _NUMBERS.sub(lambda match: number_words(match.group(), language), text)
    text = _NUMBERS.sub(" ", text)
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def _sentences(paragraph: str) -> list[str]:
    """Split after sentence punctuation, keeping a closing quote with its sentence."""
    result: list[str] = []
    start = 0
    pattern = re.compile(r"[.!?…]+(?:[»”\"'])?(?=\s+|$)")
    for match in pattern.finditer(paragraph):
        end = match.end()
        piece = paragraph[start:end].strip()
        if piece:
            result.append(piece)
        start = end
        while start < len(paragraph) and paragraph[start].isspace():
            start += 1
    tail = paragraph[start:].strip()
    if tail:
        result.append(tail)
    return result


def chunks(
    text: str,
    limit: int = 700,
    sentence_pause: float = 0.6,
    paragraph_pause: float = 1.8,
    punctuation_pause: float = 0.25,
    language: str = "ru",
    read_numbers: bool = True,
) -> list[tuple[str, float]]:
    """Return speech fragments and silence after each, preserving punctuation."""
    text = normalize_numbers(text, language, read_numbers)
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
    clause_pattern = re.compile(r"(?<=[,;:)\]»”’\"'])\s+")

    for paragraph_index, paragraph in enumerate(paragraphs):
        sentences = _sentences(paragraph)
        for sentence_index, sentence in enumerate(sentences):
            clauses = [part.strip() for part in clause_pattern.split(sentence) if part.strip()]
            for clause_index, clause in enumerate(clauses):
                parts = []
                remainder = clause
                while len(remainder) > limit:
                    cut = remainder.rfind(" ", 0, limit)
                    if cut < limit // 2:
                        cut = limit
                    parts.append(remainder[:cut].strip())
                    remainder = remainder[cut:].strip()
                if remainder:
                    parts.append(remainder)

                for part_index, part in enumerate(parts):
                    final_part = part_index == len(parts) - 1
                    final_clause = clause_index == len(clauses) - 1
                    final_sentence = sentence_index == len(sentences) - 1
                    final_paragraph = paragraph_index == len(paragraphs) - 1
                    if not final_part:
                        pause = min(0.3, sentence_pause)
                    elif not final_clause:
                        pause = punctuation_pause
                    elif not final_sentence:
                        pause = sentence_pause
                    elif not final_paragraph:
                        pause = paragraph_pause
                    else:
                        pause = 0.0
                    result.append((part, pause))
    return result


if __name__ == "__main__" and len(sys.argv) == 6 and sys.argv[1] == "normalize":
    input_path, output_path, language, should_read = sys.argv[2:]
    source = open(input_path, encoding="utf-8").read()
    open(output_path, "w", encoding="utf-8").write(normalize_numbers(source, language, should_read == "1"))
