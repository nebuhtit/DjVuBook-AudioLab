import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from format_converter import convert, epub_text
from epub_export import export_epub


class FormatConverterTests(unittest.TestCase):
    def test_epub_spine_text_extraction_and_text_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            md = root / "source.md"
            md.write_text("# Первая глава\n\nТекст для проверки конвертации.", encoding="utf-8")
            epub = root / "book.epub"
            export_epub(md, epub, "Проверочная книга")
            extracted = epub_text(epub)
            self.assertIn("Первая глава", extracted)
            self.assertIn("Текст для проверки конвертации", extracted)
            out = root / "book.txt"
            convert([epub], "txt", out)
            self.assertIn("Текст для проверки конвертации", out.read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("cupsfilter") and shutil.which("pdfinfo") and shutil.which("ddjvu") and shutil.which("c44") and shutil.which("djvm"), "нужны системные средства macOS, Poppler и DjVuLibre")
    def test_pdf_djvu_pdf_and_page_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            txt = root / "source.txt"
            txt.write_text("Conversion smoke test.\nA second line.", encoding="utf-8")
            pdf = root / "source.pdf"
            with pdf.open("wb") as stream:
                result = subprocess.run([shutil.which("cupsfilter"), "-i", "text/plain", "-m", "application/pdf", str(txt)], stdout=stream, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
            djvu = root / "converted.djvu"
            convert([pdf], "djvu", djvu)
            self.assertGreater(djvu.stat().st_size, 0)
            roundtrip = root / "roundtrip.pdf"
            convert([djvu], "pdf", roundtrip)
            self.assertGreater(roundtrip.stat().st_size, 0)
            images = root / "pages"
            convert([roundtrip], "png", images)
            self.assertTrue(list(images.glob("*.png")))

    @unittest.skipUnless(shutil.which("sips") and shutil.which("pdfinfo"), "нужен macOS sips")
    def test_image_folder_to_pdf_in_natural_order(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("page10.png", "page2.png"):
                # Tiny, valid PPM is converted by sips into a PNG fixture.
                ppm = root / (name + ".ppm")
                ppm.write_bytes(b"P6\n2 2\n255\n" + bytes([255, 0, 0] * 4))
                target = root / name
                p = subprocess.run(["/usr/bin/sips", "-s", "format", "png", str(ppm), "--out", str(target)], capture_output=True)
                if p.returncode:
                    self.skipTest("sips не смог создать тестовое изображение")
            pdf = root / "images.pdf"
            convert([root], "pdf", pdf)
            info = subprocess.run([shutil.which("pdfinfo"), str(pdf)], capture_output=True, text=True)
            self.assertRegex(info.stdout, r"Pages:\s+2")
            epub = root / "images.epub"
            convert([root], "epub", epub, "Страницы")
            self.assertGreater(epub.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
