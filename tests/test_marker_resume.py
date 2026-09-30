"""Failure/restart integration test without loading the OCR models."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import marker_backend as backend

class ResumeTests(unittest.TestCase):
    def test_failure_resumes_without_reprocessing_completed_page(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'out';source=root/'book.djvu';source.write_bytes(b'fixture')
            binary=root/'venv/bin/marker_single';binary.parent.mkdir(parents=True);binary.touch()
            attempts=[];fail=True
            def execute(command,env,log=None):
                nonlocal fail
                if command[0]=='djvused':return '6'
                if command[0]=='ddjvu':
                    Path(command[-1]).write_text(command[-3]);return ''
                job=json.loads(Path(command[-1]).read_text())
                for page in job['pending']:
                    attempts.append(page)
                    if page==5 and fail:
                        fail=False;raise RuntimeError('Simulated OCR crash')
                    location=out/f'page-{page:06d}'
                    folder=location/'result/source';folder.mkdir(parents=True,exist_ok=True)
                    (folder/'source.md').write_text('{0}----------\n\nText page '+str(page))
                    backend.atomic_text(location/'ready.json',json.dumps({'pages':[page]}))
                    backend.publish(out,job['pages'],source)
                    self.assertTrue((out/'book.epub').is_file())
                return ''
            argv=['marker_backend.py',str(source),'--output',str(out)]
            with patch.object(backend,'ROOT',root),patch.object(backend,'environment',return_value={}),patch.object(backend,'execute',side_effect=execute),patch.object(sys,'argv',argv):
                with self.assertRaisesRegex(RuntimeError,'Simulated'):backend.main()
                self.assertEqual(json.loads((out/'marker-report.json').read_text())['completed_pages'],[1,2,3,4])
                self.assertIn('Text page 1',(out/'book.md').read_text())
                backend.main()
                self.assertEqual(attempts,[1,2,3,4,5,5,6])
                report=json.loads((out/'marker-report.json').read_text())
                self.assertTrue(report['complete']);self.assertEqual(report['completed_pages'],[1,2,3,4,5,6])
                text=(out/'book.md').read_text()
                self.assertEqual(text.count('Text page 1'),1)
                self.assertLess(text.index('Text page 1'),text.index('Text page 5'))
                backend.main();self.assertEqual(attempts,[1,2,3,4,5,5,6])

    def test_legacy_cache_and_incomplete_batch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'chunk-0001';artifact=folder/'result/source/source.md'
            artifact.parent.mkdir(parents=True);artifact.write_text('old pages')
            (folder/'ready.json').write_text(json.dumps({'pages':[1,2,3,4]}))
            items=list(backend.work_items(root,[1,2,3,4,5,6]))
            self.assertEqual([x[0] for x in items],[[1,2,3,4],[5,6]])
            (folder/'ready.json').write_text('{broken')
            self.assertEqual([x[0] for x in backend.work_items(root,[1,2,3,4])],[[1,2,3,4]])

class ProfileTests(unittest.TestCase):
    def test_memory_profiles(self):
        from marker_runtime import environment
        self.assertEqual(environment(profile='economy')['SURYA_INFERENCE_PARALLEL'],'1')
        env=environment(profile='parallel')
        self.assertEqual(env['SURYA_INFERENCE_PARALLEL'],'2')
        self.assertEqual(env['SURYA_INFERENCE_CTX_SIZE'],'24576')
        with self.assertRaises(ValueError):environment(profile='invalid')
