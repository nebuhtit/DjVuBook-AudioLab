"""Local converter for common book/document formats. Uses macOS and DjVuLibre/Poppler tools."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from epub_export import export_epub
from import_text import import_text

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".bmp", ".webp"}
TEXT_EXTS = {".txt", ".md", ".markdown", ".mdown", ".html", ".htm", ".xhtml", ".docx", ".doc"}
ALIASES = {"jpeg": "jpg", "markdown": "md"}


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        for candidate in (f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}", f"/usr/bin/{name}", f"/usr/sbin/{name}"):
            if Path(candidate).is_file():
                return candidate
        raise RuntimeError(f"Не найдена программа {name}. Установите нужные инструменты (Poppler или DjVuLibre).")
    return path


def run(args: list[str]) -> None:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail or f"Команда завершилась с кодом {proc.returncode}: {args[0]}")


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def pages_from_pdf(source: Path) -> int:
    result = subprocess.run([tool("pdfinfo"), str(source)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Не удалось прочитать PDF")
    match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.M)
    if not match:
        raise RuntimeError("В PDF не найдено ни одной страницы")
    return int(match[1])


def to_pdf(source: Path, temporary: Path) -> Path:
    if source.suffix.lower() == ".pdf":
        return source
    destination = temporary / "source.pdf"
    run([tool("ddjvu"), "-format=pdf", str(source), str(destination)])
    return destination


def epub_text(source: Path) -> str:
    class Blocks(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []
            self.skip = 0

        def handle_starttag(self, tag, attrs):
            if tag in {"script", "style", "svg", "nav"}:
                self.skip += 1
            elif not self.skip and tag in {"p", "div", "br", "li", "blockquote", "section", "article", "tr"}:
                self.parts.append("\n")
            elif not self.skip and tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                level = int(tag[1]); self.parts.append("\n" + "#" * level + " ")

        def handle_endtag(self, tag):
            if tag in {"script", "style", "svg", "nav"} and self.skip:
                self.skip -= 1
            elif not self.skip and tag in {"p", "div", "br", "li", "blockquote", "section", "article", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
                self.parts.append("\n")

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

    with zipfile.ZipFile(source) as archive:
        names = set(archive.namelist())
        if "META-INF/container.xml" not in names:
            raise RuntimeError("В EPUB не найден META-INF/container.xml")
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next((e.attrib.get("full-path") for e in container.iter() if e.tag.endswith("rootfile")), None)
        if not rootfile or rootfile not in names:
            raise RuntimeError("Не найден файл оглавления EPUB")
        package = ET.fromstring(archive.read(rootfile))
        manifest = {}
        for item in package.iter():
            if item.tag.endswith("item"):
                manifest[item.attrib.get("id", "")] = item.attrib.get("href", "")
        spine = next((e for e in package.iter() if e.tag.endswith("spine")), None)
        if spine is None:
            raise RuntimeError("В EPUB отсутствует последовательность глав")
        base = posixpath.dirname(rootfile)
        chapters = []
        for itemref in spine:
            href = manifest.get(itemref.attrib.get("idref", ""))
            if not href:
                continue
            member = posixpath.normpath(posixpath.join(base, href.split("#", 1)[0]))
            if member.startswith("../") or member not in names:
                continue
            parser = Blocks()
            parser.feed(archive.read(member).decode("utf-8", "replace"))
            chapter = "".join(parser.parts)
            chapter = re.sub(r"[ \t]+\n", "\n", chapter)
            chapter = re.sub(r"\n{3,}", "\n\n", chapter).strip()
            if chapter:
                chapters.append(chapter)
    if not chapters:
        raise RuntimeError("В EPUB не удалось извлечь текст из глав")
    return "\n\n".join(chapters)


def text_source(source: Path) -> str:
    if source.suffix.lower() == ".epub":
        return epub_text(source)
    return import_text(source)


def save_text(source: Path, target: str, destination: Path, title: str = "") -> None:
    if source.suffix.lower() in {".pdf", ".djvu", ".djv"}:
        with tempfile.TemporaryDirectory(prefix="djvubook-text-") as folder:
            pdf = to_pdf(source, Path(folder))
            if source.suffix.lower() == ".pdf":
                proc = subprocess.run([tool("pdftotext"), "-layout", str(pdf), "-"], capture_output=True, text=True)
                text = proc.stdout if proc.returncode == 0 else ""
            else:
                proc = subprocess.run([tool("djvutxt"), str(source)], capture_output=True, text=True)
                text = proc.stdout if proc.returncode == 0 else ""
        if not text.strip():
            raise RuntimeError("В файле нет извлекаемого текстового слоя. Для скана сначала запустите OCR Marker или Tesseract.")
    else:
        text = text_source(source)
    text = text.strip() + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if target == "txt":
        destination.write_text(re.sub(r"^#{1,6}\s+", "", text, flags=re.M), encoding="utf-8")
    elif target == "md":
        if source.suffix.lower() != ".epub" and source.suffix.lower() not in TEXT_EXTS:
            text = "# " + (title or source.stem) + "\n\n" + text
        destination.write_text(text, encoding="utf-8")
    elif target == "epub":
        md = destination.parent / (destination.stem + ".conversion.md")
        try:
            md.write_text(text if re.search(r"^#{1,6}\s", text, re.M) else f"# {title or source.stem}\n\n{text}", encoding="utf-8")
            export_epub(md, destination, title=title or source.stem)
        finally:
            md.unlink(missing_ok=True)
    elif target == "pdf":
        with tempfile.TemporaryDirectory(prefix="djvubook-print-") as folder:
            txt = Path(folder) / "document.txt"
            txt.write_text(re.sub(r"^#{1,6}\s+", "", text, flags=re.M), encoding="utf-8")
            proc = subprocess.run([tool("cupsfilter"), "-i", "text/plain", "-m", "application/pdf", str(txt)], capture_output=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "macOS не смог создать PDF")
            destination.write_bytes(proc.stdout)
    else:
        raise RuntimeError(f"Нельзя сохранить текст в формате {target}")


def image_files(inputs: list[Path]) -> list[Path]:
    files = []
    for item in inputs:
        if item.is_dir():
            files.extend(p for p in item.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
        elif item.suffix.lower() in IMAGE_EXTS:
            files.append(item)
        else:
            raise RuntimeError(f"Не является изображением: {item.name}")
    unique = list(dict.fromkeys(p.resolve() for p in files))
    if not unique:
        raise RuntimeError("В выбранной папке не найдены изображения поддерживаемых форматов")
    return sorted(unique, key=natural_key)


def images_to_pdf(images: list[Path], destination: Path, temporary: Path) -> None:
    pdfs = []
    for index, image in enumerate(images, 1):
        path = temporary / f"image-{index:05d}.pdf"
        run(["/usr/bin/sips", "-s", "format", "pdf", str(image), "--out", str(path)])
        pdfs.append(path)
    if len(pdfs) == 1:
        shutil.copyfile(pdfs[0], destination)
    else:
        run([tool("pdfunite"), *map(str, pdfs), str(destination)])


def pdf_to_images(pdf: Path, target: str, destination_dir: Path) -> int:
    destination_dir.mkdir(parents=True, exist_ok=True)
    before = set(destination_dir.iterdir())
    args = [tool("pdftoppm"), "-r", "200"]
    if target == "jpg":
        args += ["-jpegopt", "quality=92", "-jpeg"]
    else:
        args.append("-png")
    run(args + [str(pdf), str(destination_dir / "page")])
    created = [p for p in destination_dir.iterdir() if p not in before and p.is_file()]
    for old in sorted(created, key=natural_key):
        match = re.search(r"-(\d+)\.(?:png|jpg)$", old.name, re.I)
        number = int(match[1]) if match else created.index(old) + 1
        new = destination_dir / f"page-{number:04d}.{target}"
        if old != new:
            old.rename(new)
    return len(created)


def images_to_djvu(images: list[Path], destination: Path, temporary: Path) -> None:
    pages = []
    for index, image in enumerate(images, 1):
        normalized = temporary / f"page-{index:05d}.jpg"
        run(["/usr/bin/sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(image), "--out", str(normalized)])
        page = temporary / f"page-{index:05d}.djvu"
        run([tool("c44"), "-dpi", "200", str(normalized), str(page)])
        pages.append(page)
    if len(pages) == 1:
        shutil.copyfile(pages[0], destination)
    else:
        run([tool("djvm"), "-c", str(destination), *map(str, pages)])


def images_to_epub(images: list[Path], destination: Path, title: str, temporary: Path) -> None:
    assets = temporary / "images"
    assets.mkdir()
    markdown = temporary / "book.md"
    lines = [f"# {title or 'Сборник изображений'}", ""]
    for index, image in enumerate(images, 1):
        name = f"page-{index:04d}.jpg"
        run(["/usr/bin/sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(image), "--out", str(assets / name)])
        lines.extend([f"![Страница {index}](images/{name})", ""])
    markdown.write_text("\n".join(lines), encoding="utf-8")
    export_epub(markdown, destination, title=title or "Сборник изображений")


def convert(inputs: list[Path], target: str, destination: Path, title: str = "") -> str:
    target = ALIASES.get(target.lower().lstrip("."), target.lower().lstrip("."))
    ext = inputs[0].suffix.lower()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if target in {"txt", "md", "epub"} and (ext in TEXT_EXTS or ext in {".epub", ".pdf", ".djvu", ".djv"}):
        if len(inputs) != 1:
            raise RuntimeError("Для текстового экспорта выберите один документ")
        save_text(inputs[0], target, destination, title)
        return f"Сохранено: {destination}"
    if target == "pdf" and (ext in TEXT_EXTS or ext == ".epub"):
        save_text(inputs[0], target, destination, title)
        return f"Создан простой PDF из текста: {destination}"
    if target == "pdf" and ext == ".pdf":
        shutil.copyfile(inputs[0], destination)
        return f"Скопирован PDF: {destination}"
    if target == "pdf" and ext in {".djvu", ".djv"}:
        run([tool("ddjvu"), "-format=pdf", str(inputs[0]), str(destination)])
        return f"DjVu преобразован в PDF: {destination}"
    if target == "djvu" and ext in {".pdf", ".djvu", ".djv"}:
        if ext in {".djvu", ".djv"}:
            raise RuntimeError("Источник уже в DjVu. Выберите PDF, PNG/JPEG или текстовый формат.")
        with tempfile.TemporaryDirectory(prefix="djvubook-pdf-djvu-") as folder:
            temp = Path(folder)
            count = pdf_to_images(to_pdf(inputs[0], temp), "jpg", temp / "raster")
            images = sorted((temp / "raster").glob("*.jpg"), key=natural_key)
            images_to_djvu(images, destination, temp)
        return f"PDF растрирован в {count} страницы и сохранён как DjVu: {destination}"
    if target == "epub" and (ext in IMAGE_EXTS or inputs[0].is_dir()):
        files = image_files(inputs)
        with tempfile.TemporaryDirectory(prefix="djvubook-images-epub-") as folder:
            images_to_epub(files, destination, title or inputs[0].stem, Path(folder))
        return f"Создан EPUB со страницами-изображениями ({len(files)} шт.): {destination}"
    if target in {"pdf", "djvu"}:
        files = image_files(inputs)
        with tempfile.TemporaryDirectory(prefix="djvubook-convert-") as folder:
            temp = Path(folder)
            if target == "pdf":
                images_to_pdf(files, destination, temp)
            else:
                images_to_djvu(files, destination, temp)
        return f"Сохранено {len(files)} изображений в {target.upper()}: {destination}"
    if target in {"png", "jpg"}:
        with tempfile.TemporaryDirectory(prefix="djvubook-raster-") as folder:
            temp = Path(folder)
            if ext == ".pdf" or ext in {".djvu", ".djv"}:
                pdf = to_pdf(inputs[0], temp)
                count = pdf_to_images(pdf, target, destination)
            elif ext in IMAGE_EXTS or inputs[0].is_dir():
                files = image_files(inputs)
                destination.mkdir(parents=True, exist_ok=True)
                for i, image in enumerate(files, 1):
                    run(["/usr/bin/sips", "-s", "format", "jpeg" if target == "jpg" else "png", str(image), "--out", str(destination / f"image-{i:04d}.{target}")])
                count = len(files)
            else:
                raise RuntimeError(f"Преобразование {ext or 'файла'} в изображения не поддерживается")
        return f"Создано изображений: {count}. Папка: {destination}"
    raise RuntimeError(f"Маршрут {ext or 'папка'} → {target.upper()} не поддерживается. Для EPUB используйте TXT, MD или PDF; для изображений и сканов доступен OCR отдельной кнопкой.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=["pdf", "djvu", "jpg", "jpeg", "png", "txt", "md", "markdown", "epub"])
    parser.add_argument("--output", required=True, type=Path, help="Файл или папка для постраничных изображений")
    parser.add_argument("--title", default="")
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        print(convert(args.inputs, args.target, args.output, args.title), flush=True)
    except Exception as exc:
        print(f"Ошибка: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
