import base64
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from epub_export import export_epub,inline
from markdown_export import save_markdown
from marker_backend import normalize_chapter_headings

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=')

class MarkerExports(unittest.TestCase):
    def test_explicit_chapter_heading_is_joined(self):
        text='ГЛАВА 10\n\n---\n\n## Основные компоненты терапии\n\nЛюди — сложные системы.'
        self.assertEqual(normalize_chapter_headings(text),'## ГЛАВА 10. Основные компоненты терапии\n\nЛюди — сложные системы.')
        ordinary='Глава 8. Обсуждение в тексте\n\n### Подраздел'
        self.assertEqual(normalize_chapter_headings(ordinary),ordinary)

    def test_inline_preserves_literal_escapes(self):
        self.assertEqual(inline('**Жирный** и *курсив*'),'<strong>Жирный</strong> и <em>курсив</em>')
        self.assertEqual(inline(r'\*текст\* <script>'),'*текст* &lt;script&gt;')

    def test_image_and_caption_in_epub(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);(folder/'figure.png').write_bytes(PNG)
            md=folder/'book.md';md.write_text('# Книга\n\n![Схема](figure.png)\n\n**Рис. 1.** Описание\n')
            epub=folder/'book.epub';export_epub(md,epub)
            with zipfile.ZipFile(epub) as z:
                self.assertEqual(z.read('EPUB/images/image-0001.png'),PNG)
                page=z.read('EPUB/chapter-0001.xhtml').decode()
                self.assertIn('<strong>Рис. 1.</strong>',page)
                root=ET.fromstring(z.read('EPUB/package.opf'))
                self.assertTrue(any(e.get('media-type')=='image/png' for e in root.iter()))

    def test_save_md_copies_images_and_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);src=folder/'source';src.mkdir();dest=folder/'export';dest.mkdir()
            (src/'figure.png').write_bytes(PNG);(folder/'private.png').write_bytes(PNG)
            md=src/'book.md';md.write_text('![Схема](figure.png)\n![Outside](../private.png)')
            out=dest/'book.md';save_markdown(md,out)
            images=list((dest/'book-images').glob('*.png'))
            self.assertEqual(len(images),1)
            self.assertIn('../private.png',out.read_text())
            self.assertIn(images[0].name,out.read_text())

if __name__=='__main__':unittest.main()
