#!/usr/bin/env python3
"""2026-09-28 — локальный DjVu → Marker на внешнем диске. Облако не используется."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from djvubook import pages_arg, digest
from marker_runtime import ROOT, environment
from input_source import resolve_source,tree_digest

child=None

def execute(command, env, log=None):
    global child
    child=subprocess.Popen([str(x) for x in command],env=env,stdout=log or subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
    try:
        if log is None:
            result=child.communicate()[0]
        else:
            started=time.monotonic();position=0
            while True:
                try:
                    child.wait(timeout=15);break
                except subprocess.TimeoutExpired:
                    log.flush()
                    content=Path(log.name).read_text(errors='replace')
                    fresh=content[position:];position=len(content)
                    if fresh:print(fresh,end='' if fresh.endswith('\n') else '\n',flush=True)
                    lines=content.splitlines()
                    last=next((line.strip() for line in reversed(lines) if line.strip()),'Загрузка Python, PyTorch и моделей с внешнего диска…')
                    print(f'Marker: {int(time.monotonic()-started)} с · '+last[-350:],flush=True)
            content=Path(log.name).read_text(errors='replace')
            if content[position:]:print(content[position:],flush=True)
            result=''

        if child.returncode:raise RuntimeError(f'{Path(str(command[0])).name}: код {child.returncode}. '+(result or 'Подробности в marker.log.'))
        return result or ''
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        child=None

def stop(signum,frame):
    if child is not None and child.poll() is None:
        os.killpg(child.pid,signal.SIGINT)
        try:child.wait(timeout=40)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
    raise KeyboardInterrupt


def normalize_chapter_headings(text):
    # Объединяем только явно распознанную метку главы и следующий заголовок.
    # Обычные колонтитулы и подписи к рисункам не считаем главами.
    import re
    pattern=r'(?im)^(?:#{1,6}\s+)?((?:ГЛАВА|ЧАСТЬ|РАЗДЕЛ|CHAPTER|PART)\s+(?:[0-9]+|[IVXLCDM]+))[ \t]*\n+(?:---[ \t]*\n+)?#{1,6}[ \t]+([^\n]+)'
    return re.sub(pattern,lambda m:'## '+m[1]+'. '+m[2],text)


def atomic_text(path, text):
    """Publish a checkpoint only after its complete contents reach disk."""
    pending=path.with_name(path.name+'.tmp')
    with pending.open('w',encoding='utf-8') as stream:
        stream.write(text);stream.flush();os.fsync(stream.fileno())
    pending.replace(path)


def cached(folder, pages):
    try:
        return (json.loads((folder/'ready.json').read_text())=={'pages':pages}
                and (folder/'result/source/source.md').is_file())
    except (OSError,ValueError):
        return False


def work_items(out, pages):
    # Four-page batches run continuously; completed single-page caches remain usable.
    for offset in range(0,len(pages),4):
        group=pages[offset:offset+4]
        legacy=out/f'chunk-{offset//4+1:04d}'
        if cached(legacy,group):
            yield group,legacy
            continue
        pending=[]
        for page in group:
            single=out/f'page-{page:06d}'
            if cached(single,[page]):
                if pending:
                    yield pending,out/('batch-'+'-'.join(map(str,pending)))
                    pending=[]
                yield [page],single
            else:
                pending.append(page)
        if pending:
            yield pending,out/('batch-'+'-'.join(map(str,pending)))


def publish(out,pages,source,title='',author=''):
    import re
    from epub_export import export_epub
    pieces=[];completed=[]
    for group,folder in work_items(out,pages):
        candidates=[(group,folder)] if cached(folder,group) else [([p],out/f'page-{p:06d}') for p in group]
        for selected,location in candidates:
            if not cached(location,selected):continue
            artifact=location/'result/source/source.md'
            text=normalize_chapter_headings(artifact.read_text())
            text=re.sub(r'(?m)^\{(\d+)\}-{5,}\s*$',lambda m:'<!-- Страница DjVu '+str(selected[int(m[1])])+' -->' if int(m[1])<len(selected) else m[0],text)
            relative=artifact.parent.relative_to(out).as_posix()
            text=re.sub(r'(!\[[^\]]*\]\()([^):\s]+)(\))',lambda m:m[1]+relative+'/'+m[2]+m[3],text)
            pieces.append(text);completed.extend(selected)
    if pieces:
        atomic_text(out/'book.md','\n\n'.join(pieces))
        export_epub(out/'book.md',out/'book.epub',title,author)
    atomic_text(out/'marker-report.json',json.dumps({'source':str(source),'requested_pages':pages,'completed_pages':completed,'complete':completed==pages},ensure_ascii=False,indent=2))
    print(f'[{len(completed)}/{len(pages)}] Сохранено страниц; EPUB обновлён' if pieces else f'[0/{len(pages)}] Ожидание первой страницы',flush=True)
    return completed


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pages',default='all')
    parser.add_argument('--title',default='');parser.add_argument('--author',default='')
    parser.add_argument('--memory-profile',choices=['economy','parallel'],default='economy')
    args=parser.parse_args()
    if not (ROOT/'venv/bin/marker_single').is_file():raise RuntimeError('Marker недоступен в выбранной папке окружения. Проверьте путь к библиотекам.')
    env=environment(profile=args.memory_profile)
    print("Marker: профиль "+args.memory_profile+"; параллельных запросов "+env.get("SURYA_INFERENCE_PARALLEL","1")+"; контекст "+env.get("SURYA_INFERENCE_CTX_SIZE","16384")+" токенов. Это не лимит RAM.",flush=True)
    source=args.source.resolve();out=args.output.resolve()
    original=source
    source,kind=resolve_source(source,out)
    count=int(execute(['pdfinfo',source],env).split('Pages:')[1].splitlines()[0].strip()) if kind=='pdf' else int(execute(['djvused',source,'-e','n'],env).strip())
    pages=pages_arg(args.pages,count)
    out.mkdir(parents=True,exist_ok=True)
    from project_state import claim_engine
    claim_engine(out,'marker')
    # Очередь выполняется непрерывно; контрольная точка после каждой порции до четырёх страниц.
    source_hash=tree_digest(original)
    spec={'source_sha256':source_hash,'pages':pages,'engine':'marker-2.0.0-balanced-v2-headers'}
    state=out/'marker-source.json'
    if state.exists() and json.loads(state.read_text())!=spec:raise RuntimeError('В папке другой файл или параметры. Выберите новую папку.')
    # State is published below, while holding the engine lock.
    import fcntl
    with (ROOT/'.job.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('На этом диске уже запущен Marker. Дождитесь завершения текущей книги.')
        atomic_text(state,json.dumps(spec,ensure_ascii=False,indent=2))
        completed=publish(out,pages,source,args.title,args.author)
        pending=[page for page in pages if page not in completed]
        if pending:
            job=out/'worker-job.json'
            atomic_text(job,json.dumps({'source':str(source),'source_kind':kind,'source_original':str(original),'output':str(out),'pages':pages,'pending':pending,'title':args.title,'author':args.author},ensure_ascii=False))
            with (out/'marker.log').open('a') as log:
                execute([ROOT/'venv/bin/python','-u',Path(__file__).with_name('marker_runner.py'),'--book-job',job],env,log)
    print(f'Готово: {out / "book.md"}',flush=True)

if __name__=='__main__':
    signal.signal(signal.SIGINT,stop)
    try:main()
    except KeyboardInterrupt:print('Остановлено. Готовые страницы сохранены. Повторный запуск продолжит обработку.',flush=True);sys.exit(130)
    except Exception as e:print('Ошибка: '+str(e),flush=True);sys.exit(1)
