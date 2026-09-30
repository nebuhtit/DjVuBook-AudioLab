import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from timing import duration,Estimate
class Timing(unittest.TestCase):
    def test_hours(self):self.assertEqual(duration(3661),'01:01:01')
    def test_cache_and_eta(self):
        e=Estimate(0);e.update(16,20,10)
        self.assertIn('идёт оценка',e.label(11))
        e.update(17,20,70)
        self.assertIn('00:03:00',e.label(70))
        e.update(20,20,250)
        self.assertIn('Осталось 00:00:00',e.label(250))
