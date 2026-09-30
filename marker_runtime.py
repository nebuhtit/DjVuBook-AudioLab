"""28.09.2026 — пути и ограничения локального Marker на внешнем диске."""
import os
from pathlib import Path
ROOT=Path(os.environ.get('DJVUBOOK_MARKER_ROOT','/Volumes/DjVuBookLibraries/DjVuBook-Marker')).expanduser()

def environment(offline=True, profile="economy"):
    if profile not in ("economy","parallel"):
        raise ValueError("Неизвестный профиль памяти")
    env=os.environ.copy()
    env.pop('PYTHONPYCACHEPREFIX',None)
    values={
        'TMPDIR':ROOT/'tmp', 'XDG_CACHE_HOME':ROOT/'cache',
        'PIP_CACHE_DIR':ROOT/'cache/pip','HF_HOME':ROOT/'cache/huggingface',
        'HF_HUB_CACHE':ROOT/'cache/huggingface/hub','TORCH_HOME':ROOT/'cache/torch',
        'MODEL_CACHE_DIR':ROOT/'models/datalab','PYTHONDONTWRITEBYTECODE':'1',
        'MPLCONFIGDIR':ROOT/'cache/matplotlib',
        'LLAMA_CPP_BINARY':ROOT/'bin/llama-b11224/llama-server',
        'SURYA_GGUF_LOCAL_MODEL_PATH':ROOT/'models/surya-2.gguf',
        'SURYA_GGUF_LOCAL_MMPROJ_PATH':ROOT/'models/surya-2-mmproj.gguf',
        'SURYA_INFERENCE_BACKEND':'llamacpp','SURYA_INFERENCE_PARALLEL':'1',
        'SURYA_INFERENCE_KEEP_ALIVE':'false','SURYA_INFERENCE_CTX_SIZE':'16384',
        'FAST_LAYOUT_BATCH_SIZE':'1','FAST_LAYOUT_SERVER_MAX_BATCH':'1',
        'DETECTOR_BATCH_SIZE':'1','OCR_ERROR_BATCH_SIZE':'1',
        'FAST_DETECTOR_DEVICE':'cpu','FAST_LAYOUT_NUM_THREADS':'2',
        'OMP_NUM_THREADS':'2','TOKENIZERS_PARALLELISM':'false','HF_HUB_DISABLE_TELEMETRY':'1'}
    if profile=='parallel':
        values.update(SURYA_INFERENCE_PARALLEL='2',SURYA_INFERENCE_CTX_SIZE='24576')
    env.update({k:str(v) for k,v in values.items()})
    env['PATH']=str(ROOT/'venv/bin')+':/opt/homebrew/bin:'+env.get('PATH','')
    if offline:
        env['HF_HUB_OFFLINE']='1';env['TRANSFORMERS_OFFLINE']='1'
    return env
