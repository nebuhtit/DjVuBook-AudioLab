#!/usr/bin/env python3
"""DjVuBook — локальный DjVu → Markdown. 2026-09-28, Europe/Moscow.

Стандартная библиотека Python + DjVuLibre + Tesseract. Сеть не используется.
Страницы обрабатываются независимо; проверяемый кэш позволяет продолжать работу.
Оригинальные hOCR и PNG сохраняются для проверки неоднозначной вёрстки.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import signal
import threading
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
VERSION = '1.0.1'
STOP = threading.Event()


def run(args, timeout=600):
    """Без shell: имена файлов не могут превратиться в исполняемые команды."""
    if STOP.is_set():
        raise RuntimeError('Обработка остановлена')
    p = subprocess.Popen([str(x) for x in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         env={**os.environ, 'OMP_THREAD_LIMIT': '1'})
    deadline = time.monotonic() + timeout
    try:
        while True:
            if STOP.is_set():
                raise RuntimeError('Обработка остановлена')
            if time.monotonic() > deadline:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                stdout, stderr = p.communicate(timeout=.5)
                break
            except subprocess.TimeoutExpired:
                continue
        if p.returncode:
            raise RuntimeError(f'{Path(str(args[0])).name}: {stderr.decode(errors="replace")[-1800:]}')
        return stdout.decode('utf-8', errors='replace')
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
                p.communicate()



def atomic(path, text):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def pages_arg(value, count):
    if value.lower() == 'all':
        return list(range(1, count + 1))
    result = set()
    for item in value.split(','):
        match = re.fullmatch(r'\s*(\d+)(?:\s*-\s*(\d+))?\s*', item)
        if not match:
            raise ValueError('Страницы: all, 1-12 или 1,5,20-25')
        a, b = int(match[1]), int(match[2] or match[1])
        if a < 1 or b > count or b < a:
            raise ValueError(f'Диапазон страниц должен быть в пределах 1–{count}')
        result.update(range(a, b + 1))
    return sorted(result)


def props(element):
    result = {}
    for item in element.get('title', '').split(';'):
        parts = item.strip().split(maxsplit=1)
        if len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


def bbox(element):
    return [int(x) for x in props(element).get('bbox', '0 0 0 0').split()]


def hasclass(element, name):
    return name in element.get('class', '').split()


def parse_hocr(path):
    """Оставляем порядок блоков Tesseract: глобальная сортировка по Y смешала бы колонки."""
    tree = ET.parse(path)
    page = next(e for e in tree.iter() if hasclass(e, 'ocr_page'))
    paragraphs = []
    for par in page.iter():
        if not hasclass(par, 'ocr_par'):
            continue
        lines = []
        for line in par.iter():
            if not (hasclass(line, 'ocr_line') or hasclass(line, 'ocr_header')):
                continue
            words = []
            for word in line.iter():
                if hasclass(word, 'ocrx_word'):
                    text = ''.join(word.itertext()).strip()
                    if text:
                        words.append({'text': text, 'confidence': float(props(word).get('x_wconf', 0)),
                                      'box': bbox(word)})
            if words:
                size = float(props(line).get('x_size', max(1, bbox(line)[3]-bbox(line)[1])))
                lines.append({'words': words, 'box': bbox(line), 'size': size,
                              'text': ' '.join(w['text'] for w in words)})
        if lines:
            paragraphs.append({'box': bbox(par), 'lines': lines})
    return {'box': bbox(page), 'paragraphs': paragraphs}


def escape_md(text):
    # Экранируем OCR как текст, а не HTML/Markdown-команды из исходной книги.
    return re.sub(r'([\\`*_{}\[\]<>#|])', r'\\\1', text)


def join_lines(lines, dehyphenate=False):
    result = ''
    for line in lines:
        text = line['text'].strip()
        if dehyphenate and result.endswith('-') and re.match(r'^[a-zа-яё]', text):
            result = result[:-1] + text
        else:
            result += (' ' if result else '') + text
    return escape_md(result)


def to_markdown(layout, dehyphenate=False):
    """Консервативные заголовки: размер + короткая строка или явное имя раздела.
    Межстрочные интервалы разделяют абзацы, но сами по себе не создают главы.
    Жирность LSTM надёжно не возвращает: мы её не выдумываем.
    """
    pars = layout['paragraphs']
    lines = [line for par in pars for line in par['lines']]
    body_sizes = [l['size'] for l in lines if len(l['text']) > 45]
    baseline = statistics.median(body_sizes or [l['size'] for l in lines] or [1])
    output = []
    for par in pars:
        ls = par['lines']
        text = ' '.join(l['text'] for l in ls)
        # Только изолированные цифры на верхнем/нижнем краю считаем номером страницы.
        if re.fullmatch(r'\d{1,4}', text) and (par['box'][1] < layout['box'][3]*.09 or par['box'][3] > layout['box'][3]*.92):
            continue
        toc = sum(bool(re.search(r'\s\d{1,4}$', l['text'])) for l in ls) >= max(2, len(ls)*.5)
        size = statistics.median(l['size'] for l in ls)
        explicit = bool(re.match(r'^(?:глава|часть|раздел|chapter|part)\s+(?:\d+|[IVXLCDM]+)\b', text, re.I))
        named = text.casefold() in {'содержание', 'оглавление', 'введение', 'заключение', 'предисловие', 'от издательства', 'contents', 'introduction'}
        heading = len(text) < 150 and len(ls) <= 3 and not toc and (explicit or not re.search(r'\s\d{2,4}$', text)) and (explicit or named or size > baseline*1.24)
        if heading:
            level = '##' if explicit or named or size > baseline*1.6 else '###'
            output.append(f'{level} {join_lines(ls)}')
            continue
        # Списки/оглавления и строки с крупным внутренним пробелом не склеиваем.
        tabular = any(any(b['box'][0]-a['box'][2] > baseline*2.5 for a,b in zip(l['words'], l['words'][1:])) for l in ls)
        listing = sum(bool(re.match(r'^(?:[•●–—]|\d+[.)])\s', l['text'])) for l in ls) >= 2
        if toc or tabular or listing:
            output.append('  \n'.join(escape_md(l['text']) for l in ls))
            continue
        group = []
        for line in ls:
            if group and line['box'][1]-group[-1]['box'][3] > baseline*.85:
                output.append(join_lines(group, dehyphenate))
                group = []
            group.append(line)
        if group:
            output.append(join_lines(group, dehyphenate))
    return '\n\n'.join(output).strip() + '\n'


def crop_pgm(source, destination, left, right):
    """Без Pillow: чтение стандартного P5 от ddjvu и горизонтальное обрезание."""
    data = source.read_bytes()
    match = re.match(rb'P5\s+(?:#[^\n]*\n\s*)*(\d+)\s+(\d+)\s+255\s', data)
    if not match:
        raise ValueError('Ожидался 8-битный PGM от ddjvu')
    w, h = map(int, match.groups())
    pixels = data[match.end():]
    if len(pixels) != w*h:
        raise ValueError('Повреждённый PGM')
    x1, x2 = round(w*left), round(w*right)
    destination.write_bytes(f'P5\n{x2-x1} {h}\n255\n'.encode() + b''.join(pixels[y*w+x1:y*w+x2] for y in range(h)))


def process_page(number, source, out, args, fingerprint):
    if STOP.is_set():
        raise RuntimeError('Обработка остановлена')
    folder = out / 'pages' / f'{number:04d}'
    folder.mkdir(parents=True, exist_ok=True)
    state = folder / 'result.json'
    if state.exists() and not args.force:
        old = json.loads(state.read_text())
        required = ['page.png', 'page.md', *old.get('hocr_files', [])]
        if old.get('fingerprint') == fingerprint and all((folder/f).exists() for f in required):
            return old
    started = time.monotonic()
    if str(source).lower().endswith('.pdf'):
        run(['pdftoppm','-f',str(number),'-l',str(number),'-scale-to',str(args.width*3),'-singlefile','-gray',source,folder/'page'])
    else:
        run(['ddjvu', '-format=pgm', f'-page={number}', f'-size={args.width}x{args.width*3}', source, folder/'page.pgm'])
    if sys.platform == 'darwin':
        run(['sips', '-s', 'format', 'png', folder/'page.pgm', '--out', folder/'page.png'])
    else:
        run(['magick', folder/'page.pgm', folder/'page.png'])
    layouts, hocr_files = [], []
    regions = [(0,1)] if args.columns != '2' else [(0,.5),(.5,1)]
    for idx, (left,right) in enumerate(regions):
        image = folder/'page.pgm'
        if len(regions) == 2:
            image = folder/f'column{idx}.pgm'
            crop_pgm(folder/'page.pgm', image, left, right)
        base = folder/f'ocr{idx}'
        psm = '6' if args.columns == '1' else '3'
        run(['tesseract', image, base, '--tessdata-dir', args.models, '-l', args.lang,
             '--oem', '1', '--psm', psm, '-c', 'hocr_font_info=1', '-c', 'tessedit_create_hocr=1'])
        layouts.append(parse_hocr(base.with_suffix('.hocr')))
        hocr_files.append(base.with_suffix('.hocr').name)
        if image.name != 'page.pgm':
            image.unlink(missing_ok=True)
    words = [w for layout in layouts for p in layout['paragraphs'] for l in p['lines'] for w in l['words']]
    weak = [w for w in words if w['confidence'] < 75]
    markdown = '\n\n'.join(to_markdown(l, args.dehyphenate) for l in layouts)
    atomic(folder/'page.md', markdown)
    result = {'page':number, 'fingerprint':fingerprint, 'markdown':markdown, 'layouts':layouts,
              'words':len(words), 'low_confidence':len(weak),
              'mean_confidence':round(statistics.mean(w['confidence'] for w in words),1) if words else None,
              'review_words':[w['text'] for w in weak], 'seconds':round(time.monotonic()-started,1),
              'hocr_files':hocr_files}
    atomic(state, json.dumps(result, ensure_ascii=False, indent=2))
    (folder/'page.pgm').unlink(missing_ok=True)
    return result


def publish(out, source, results, requested, errors, count):
    results = sorted(results, key=lambda r:r['page'])
    header = f'# {escape_md(source.stem)}\n\n'
    book = header + '\n\n'.join(f'<!-- Страница DjVu {r["page"]} -->\n\n{r["markdown"]}' for r in results)
    atomic(out/'book.md', book)
    summary = {'source':str(source), 'total_pages':count, 'requested_pages':requested,
               'completed_pages':[r['page'] for r in results], 'errors':errors,
               'complete':len(results)==len(requested) and not errors,
               'note':'Confidence — оценка движка, не измеренная точность. Жирность и таблицы не восстановлены гарантированно.',
               'pages':[{k:r[k] for k in ('page','words','low_confidence','mean_confidence','review_words','seconds')} for r in results]}
    atomic(out/'report.json', json.dumps(summary,ensure_ascii=False,indent=2))
    cards = []
    for r in results:
        n = r['page']
        folder = f'pages/{n:04d}'
        cards.append(f'''<section id="p{n}"><h2>Страница {n} <small>Слов: {r['words']} · сомнительных: {r['low_confidence']} · confidence: {r['mean_confidence']}</small></h2>
<div class="pair"><a href="{folder}/page.png" target="_blank"><img loading="lazy" src="{folder}/page.png" alt="Скан страницы {n}"></a><div><textarea data-page="{n}" spellcheck="false" aria-label="Markdown страницы {n}">{html.escape(r['markdown'])}</textarea><details><summary>Сомнительные слова</summary>{html.escape(', '.join(r['review_words']))}</details><a href="{folder}/ocr0.hocr">Исходный hOCR</a></div></div></section>''')
    title = html.escape(source.stem)
    document = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DjVuBook — проверка</title>
<style>body{font:16px system-ui;margin:0;background:#f3f4f6;color:#192332}header{padding:20px 4%;background:#fff;position:sticky;top:0;z-index:1;border-bottom:1px solid #ccd}h1{font-size:23px;margin:0 0 8px}button,a{color:#165ab5}button{padding:9px 16px;cursor:pointer}main{margin:24px 4%}section{margin:0 0 30px}h2{font-size:19px}small{font-size:13px;font-weight:400}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}img{width:100%;background:white}textarea{box-sizing:border-box;width:100%;height:75vh;resize:vertical;padding:18px;border:1px solid #bbc;border-radius:6px;font:15px/1.6 ui-monospace,monospace}details{margin:12px 0}@media(max-width:750px){.pair{grid-template-columns:1fr}header{position:static}}</style>
<header><h1>DjVuBook · TITLE</h1><div>STATUS</div><p>Слева — скан, справа — редактируемый Markdown. Правки сохраняются только кнопкой скачивания. Рисунки и таблицы сверяйте со сканом.</p><button id="save">Скачать Markdown с правками</button> <a href="book.md">Исходный Markdown</a> · <a href="report.json">Отчёт OCR</a></header><main>CARDS</main>
<script>
let dirty=false;document.querySelectorAll('textarea').forEach(t=>t.addEventListener('input',()=>dirty=true));
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
document.getElementById('save').onclick=()=>{let text=HEADER;document.querySelectorAll('textarea').forEach(t=>{text+='\\n\\n<!-- Страница DjVu '+t.dataset.page+' -->\\n\\n'+t.value;});let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));a.download='book-edited.md';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);dirty=false;};
</script></html>'''
    document = document.replace('HEADER', json.dumps(header).replace('<','\\u003c'))
    document = document.replace('TITLE',title).replace('STATUS',f'Готово {len(results)} из {len(requested)} выбранных страниц; всего в книге {count}. Ошибок: {len(errors)}.').replace('CARDS','\n'.join(cards))
    atomic(out/'review.html',document)


def main():
    parser = argparse.ArgumentParser(description='Локальный DjVu → Markdown + сканы для проверки')
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pages',default='all',help='all, 1-12 или 1,10,20-25')
    parser.add_argument('--columns',choices=['auto','1','2'],default='auto',help='auto: сегментация Tesseract; 1: единый блок; 2: две половины слева направо')
    parser.add_argument('--width',type=int,default=2600,help='Ширина растра; 3200 для мелкого текста')
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--lang',default='rus+eng')
    parser.add_argument('--models',type=Path,default=ROOT/'models')
    parser.add_argument('--dehyphenate',action='store_true',help='Склеивать переносы; возможна потеря настоящих дефисов')
    parser.add_argument('--force',action='store_true',help='Перераспознать выбранные страницы')
    args = parser.parse_args()
    if not 600 <= args.width <= 6000 or not 1 <= args.workers <= 8:
        parser.error('width: 600–6000; workers: 1–8')
    for command in ('ddjvu','djvused','pdfinfo','pdftoppm','tesseract','sips' if sys.platform=='darwin' else 'magick'):
        if not shutil.which(command):
            parser.error(f'Не найден {command}. См. README.md / Установить.command')
    for lang in args.lang.split('+'):
        if not re.fullmatch(r'[a-zA-Z_]+',lang) or not (args.models/f'{lang}.traineddata').is_file():
            parser.error(f'Нет модели языка {lang} в {args.models}')
    source = args.source.expanduser().resolve()
    if not source.is_file():
        parser.error('Исходный файл не найден')
    count = int(run(['pdfinfo',source]).split('Pages:')[1].splitlines()[0].strip()) if source.suffix.lower()=='.pdf' else int(run(['djvused',source,'-e','n']).strip())
    requested = pages_arg(args.pages,count)
    out = args.output.expanduser().resolve()
    out.mkdir(parents=True,exist_ok=True)
    from project_state import claim_engine
    claim_engine(out,'tesseract')
    # Не смешиваем разные книги даже при случайном выборе одной папки вывода.
    source_hash = digest(source)
    manifest = out/'source.json'
    if manifest.exists() and json.loads(manifest.read_text()).get('sha256') != source_hash:
        parser.error('Эта папка содержит другую книгу. Выберите новую папку вывода.')
    atomic(manifest,json.dumps({'source':str(source),'sha256':source_hash,'version':VERSION},ensure_ascii=False,indent=2))
    spec = {'source':source_hash,'version':VERSION,'width':args.width,'columns':args.columns,
            'lang':args.lang,'dehyphenate':args.dehyphenate,'tesseract':run(['tesseract','--version']).splitlines()[0],
            'models':[digest(args.models/f'{l}.traineddata') for l in args.lang.split('+')]}
    fingerprint = hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
    results, errors = [], []
    print(f'Страниц в книге: {count}; выбрано: {len(requested)}. Вывод: {out}',flush=True)
    # flock освобождается ОС при аварии, поэтому повторный запуск не застрянет на старом lock.
    import fcntl
    with (out/'.lock').open('w') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Эта книга уже обрабатывается другим процессом')
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process_page,n,source,out,args,fingerprint):n for n in requested}
            for future in concurrent.futures.as_completed(futures):
                n = futures[future]
                try:
                    r = future.result()
                    results.append(r)
                    print(f'[{len(results)+len(errors)}/{len(requested)}] стр. {n}: {r["words"]} слов, сомнительных {r["low_confidence"]}',flush=True)
                except Exception as e:
                    errors.append({'page':n,'error':str(e)})
                    print(f'Ошибка страницы {n}: {e}',file=sys.stderr,flush=True)
                publish(out,source,results,requested,errors,count)
    print(f'Готово: {out / "book.md"}\nПроверка: {out / "review.html"}',flush=True)
    return 1 if errors else 0

if __name__=='__main__':
    def interrupt(signum, frame):
        STOP.set()
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, interrupt)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nОстановлено. Повторите ту же команду: готовые страницы будут взяты из кэша.',file=sys.stderr)
        sys.exit(130)
    except (ValueError,RuntimeError,subprocess.TimeoutExpired) as e:
        print(f'Ошибка: {e}',file=sys.stderr)
        sys.exit(1)
