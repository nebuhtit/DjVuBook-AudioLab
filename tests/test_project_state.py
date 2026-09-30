import sys,json,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from project_state import claim_engine,read_state,write_state
class ProjectState(unittest.TestCase):
    def test_engine_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as d:
            claim_engine(d,'marker');claim_engine(d,'marker')
            with self.assertRaises(ValueError):claim_engine(d,'tesseract')
    def test_legacy_engine_is_respected(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'source.json').write_text('{}')
            with self.assertRaises(ValueError):claim_engine(d,'marker')
    def test_preferences_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'preferences.json';data={'source':'книга.djvu','files':{'книга.djvu':{'engine':'Marker — внешний диск'}}}
            write_state(p,data);self.assertEqual(read_state(p),data)
