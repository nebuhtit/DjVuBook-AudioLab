import sys
import tempfile
from pathlib import Path
import unittest
import zipfile
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from epub_export import export_epub

class EpubTests(unittest.TestCase):
    def test_package_navigation_text_and_xml(self):
        with tempfile.TemporaryDirectory() as folder:
            md=Path(folder)/'book.md';out=Path(folder)/'book.epub'
            md.write_text('# Книга\n\n<!-- Страница DjVu 1 -->\n\nТекст & \\<script\\>\n\n## Глава 1\n\nПродолжение.\n')
            self.assertEqual(export_epub(md,out,'Тест & книга','Автор'),2)
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.infolist()[0].filename,'mimetype')
                self.assertEqual(z.infolist()[0].compress_type,zipfile.ZIP_STORED)
                self.assertEqual(z.read('mimetype'),b'application/epub+zip')
                for name in z.namelist():
                    if name.endswith(('.xml','.xhtml','.opf')):ET.fromstring(z.read(name))
                nav=ET.fromstring(z.read('EPUB/nav.xhtml'))
                ns={'h':'http://www.w3.org/1999/xhtml'}
                links=nav.findall('.//h:a',ns)
                self.assertEqual(len(links),2)
                for link in links:self.assertIn('EPUB/'+link.get('href'),z.namelist())
                body=z.read('EPUB/chapter-0001.xhtml').decode()
                self.assertIn('Текст &amp; &lt;script&gt;',body)
                self.assertNotIn('<!-- Страница',body)

    def test_empty_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            md=Path(folder)/'empty.md';md.write_text('')
            out=Path(folder)/'book.epub';out.write_bytes(b'original')
            with self.assertRaises(ValueError):export_epub(md,out)
            self.assertEqual(out.read_bytes(),b'original')

if __name__=='__main__':unittest.main()
