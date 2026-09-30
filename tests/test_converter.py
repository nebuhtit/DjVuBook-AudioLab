"""Проверки контрактов: колонки, интервалы, переносы, диапазоны и экранирование."""
import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from djvubook import pages_arg, crop_pgm, to_markdown, parse_hocr, escape_md


def line(text,y,size=20):
    return {'text':text,'box':[20,y,400,y+size],'size':size,'words':[{'text':text,'box':[20,y,400,y+size],'confidence':95}]}

class Tests(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(pages_arg('1,3-5,3',7),[1,3,4,5])
        for bad in ['0','2-1','8','x','1-2-3']:
            with self.assertRaises(ValueError): pages_arg(bad,7)

    def test_gap_is_paragraph_not_chapter(self):
        layout={'box':[0,0,500,800],'paragraphs':[{'box':[20,100,400,500],'lines':[line('Обычный текст первого абзаца.',100),line('Следующий абзац после большого интервала.',250)]}]}
        md=to_markdown(layout)
        self.assertIn('абзаца.\n\nСледующий',md)
        self.assertNotIn('##',md)

    def test_title_and_hyphen_policy(self):
        layout={'box':[0,0,500,800],'paragraphs':[{'box':[20,100,400,140],'lines':[line('Глава 1. Начало',100,40)]},{'box':[20,200,400,240],'lines':[line('пере-',200),line('нос',225)]}]}
        self.assertTrue(to_markdown(layout).startswith('## Глава 1. Начало'))
        self.assertIn('пере- нос',to_markdown(layout))
        self.assertIn('перенос',to_markdown(layout,True))

    def test_two_columns_crop_does_not_interleave(self):
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'src.pgm'; dst=Path(folder)/'dst.pgm'
            src.write_bytes(b'P5\n4 2\n255\nabcdefgh')
            crop_pgm(src,dst,.5,1)
            self.assertEqual(dst.read_bytes(),b'P5\n2 2\n255\ncdgh')

    def test_hocr_keeps_column_order(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'page.hocr'
            p.write_text('''<html><div class="ocr_page" title="bbox 0 0 500 800"><p class="ocr_par"><span class="ocr_line" title="bbox 0 500 100 520"><span class="ocrx_word" title="x_wconf 90">Левая</span></span></p><p class="ocr_par"><span class="ocr_line" title="bbox 300 10 400 30"><span class="ocrx_word" title="x_wconf 90">Правая</span></span></p></div></html>''')
            md=to_markdown(parse_hocr(p))
            self.assertLess(md.index('Левая'),md.index('Правая'))

    def test_untrusted_text_escaped(self):
        self.assertEqual(escape_md('<script>'),r'\<script\>')

if __name__=='__main__': unittest.main()
