"""Persistent GUI preferences and engine ownership of OCR output folders."""
import json
from pathlib import Path
import fcntl

def read_state(path):
    try:
        data=json.loads(Path(path).read_text())
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}

def write_state(path,data):
    path=Path(path);temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def claim_engine(out,engine):
    out=Path(out)
    with (out/'.engine.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=out/'ocr-engine.json'
        known=set()
        if path.exists():
            data=json.loads(path.read_text());known.add(data.get('engine'))
        if (out/'marker-source.json').exists():known.add('marker')
        if (out/'source.json').exists():known.add('tesseract')
        if known and known!={engine}:
            raise ValueError('В этой папке результаты другого движка OCR. Выберите отдельную папку; смешивание запрещено.')
        write_state(path,{'engine':engine})
