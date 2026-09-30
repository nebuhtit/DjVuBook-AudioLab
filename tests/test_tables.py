import sys,tempfile,unittest,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from epub_export import export_epub,inline
class Tables(unittest.TestCase):
    def test_table_and_safe_formatting(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);md=p/'book.md'
            md.write_text('| <b>Об авторах</b> | 15 |\n|---|---|\n| <i>Действие 4.1.</i> | 78 |\n\nОбычный текст | остаётся.\n')
            export_epub(md,p/'book.epub')
            with zipfile.ZipFile(p/'book.epub') as z:
                text=z.read('EPUB/chapter-0001.xhtml').decode();root=ET.fromstring(text)
                self.assertEqual(len(root.findall('.//{http://www.w3.org/1999/xhtml}tr')),2)
                self.assertIn('<strong>Об авторах</strong>',text)
                self.assertIn('<em>Действие 4.1.</em>',text)
                self.assertNotIn('|---|',text)
                self.assertIn('Обычный текст | остаётся.',text)
    def test_unbalanced_and_untrusted_html(self):
        text=inline('<b>Текст<i>курсив</b><br><script>x</script><img src="x" onerror="x">')
        ET.fromstring('<p>'+text+'</p>')
        self.assertIn('&lt;script&gt;',text)
        self.assertNotIn('<img',text)
