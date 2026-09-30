import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gui import App
class DiskDisconnect(unittest.TestCase):
    def test_missing_disk_does_not_break_log(self):
        app=App.__new__(App)
        app.log_view=Mock();app.status=Mock();app.output=Mock();app.active_marker=True
        with patch('gui.os.path.ismount',return_value=False):app.append_log('test\n')
        app.output.mkdir.assert_not_called()
        app.log_view.insert.assert_called_once_with('end','test\n')
        app.status.set.assert_called_once()
