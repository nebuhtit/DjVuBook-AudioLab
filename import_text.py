#!/usr/bin/env python3
"""Извлекает читаемый текст из TXT, Markdown, HTML, DOCX и старого DOC."""
from __future__ import annotations

import html
from html.parser import HTMLParser
import re
import subprocess
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


class TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section", "article", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        elif not self.skip and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
        elif not self.skip and tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def decode(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            pass
    return data.decode("utf-8", errors="replace")


def html_text(source: str) -> str:
    parser = TextExtractor()
    parser.feed(source)
    parser.close()
    return "".join(parser.parts)


def markdown_text(source: str) -> str:
    source = re.sub(r"```.*?```|~~~.*?~~~", " ", source, flags=re.S)
    source = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", source)
    source = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", source)
    source = re.sub(r"<https?://[^>]+>", " ", source)
    source = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", source, flags=re.M)
    source = re.sub(r"^\s*#{1,6}\s*", "", source, flags=re.M)
    source = re.sub(r"^\s*>\s?", "", source, flags=re.M)
    source = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s+", "", source, flags=re.M)
    source = re.sub(r"\|", ". ", source)
    source = re.sub(r"[*_~`]", "", source)
    return html.unescape(source)


def docx_text(path: Path) -> str:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", ns)
    if body is None:
        return ""
    blocks = []
    for child in body:
        name = child.tag.rsplit("}", 1)[-1]
        if name == "p":
            bits = []
            for item in child.iter():
                local = item.tag.rsplit("}", 1)[-1]
                if local == "t" and item.text:
                    bits.append(item.text)
                elif local == "tab":
                    bits.append("\t")
            if bits:
                blocks.append("".join(bits))
        elif name == "tbl":
            for row in child.findall("w:tr", ns):
                cells = []
                for cell in row.findall("w:tc", ns):
                    cells.append(" ".join("".join(t.text or "" for t in p.findall(".//w:t", ns)) for p in cell.findall("w:p", ns)))
                blocks.append(". ".join(x for x in cells if x))
    return "\n\n".join(blocks)


def import_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".docx", ".docm"):
        return docx_text(path)
    if ext == ".doc":
        result = subprocess.run(["/usr/bin/textutil", "-convert", "txt", "-stdout", str(path)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "macOS не смог прочитать этот Word-файл")
        return result.stdout
    raw = decode(path)
    if ext in (".html", ".htm", ".xhtml"):
        return html_text(raw)
    if ext in (".md", ".markdown", ".mdown"):
        return markdown_text(raw)
    if ext in (".txt", ".text"):
        return raw
    raise ValueError("Поддерживаются TXT, Markdown, HTML, DOCX и DOC")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Использование: import_text.py файл")
    result = re.sub(r"[ \t]+\n", "\n", import_text(Path(sys.argv[1])))
    result = re.sub(r"\n[ \t]+", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    if not result:
        raise SystemExit("В документе не найден читаемый текст")
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
