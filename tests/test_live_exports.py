import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gui import App
class LiveExports(unittest.TestCase):
    def test_buttons_enabled_during_running_ocr(self):
        with tempfile.TemporaryDirectory() as d:
            app=App.__new__(App);app.proc=Mock();app.output=Path(d);app.markdown=None;app.set_exports=Mock()
            app.refresh_live_exports();app.set_exports.assert_not_called()
            (app.output/'book.md').write_text('Первая готовая страница')
            app.refresh_live_exports()
            self.assertEqual(app.markdown,app.output/'book.md')
            app.set_exports.assert_called_once_with(True)
            app.proc.terminate.assert_not_called()
    def test_working_output_protected(self):
        with tempfile.TemporaryDirectory() as d:
            app=App.__new__(App);app.proc=Mock();app.output=Path(d)/'work'
            with patch('gui.messagebox.showinfo'):
                self.assertFalse(app.export_destination_allowed(app.output/'book.epub'))
                self.assertTrue(app.export_destination_allowed(Path(d)/'copy.epub'))
