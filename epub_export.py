"""28.09.2026 — локальный текстовый EPUB 3 из Markdown DjVuBook, без зависимостей."""
from pathlib import Path
from datetime import datetime, timezone
import html
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET


def plain(text):
    return re.sub(r'\\([\\`*_{}\[\]<>#|])', r'\1', text)


def markdown_inline(text):
    """Базовое начертание Markdown; HTML из исходника остаётся обычным текстом."""
    pattern=re.compile(r"\\([\\`*_{}\[\]<>#|])|\*\*(.+?)\*\*|\*([^*\n]+)\*")
    result=[];end=0
    for m in pattern.finditer(text):
        result.append(html.escape(text[end:m.start()]))
        if m[1] is not None:result.append(html.escape(m[1]))
        elif m[2] is not None:result.append('<strong>'+html.escape(plain(m[2]))+'</strong>')
        else:result.append('<em>'+html.escape(plain(m[3]))+'</em>')
        end=m.end()
    result.append(html.escape(text[end:]))
    return ''.join(result)


def inline(text):
    # Only these formatting tags are accepted, without attributes or executable HTML.
    tags={'b':'strong','strong':'strong','i':'em','em':'em','sup':'sup','sub':'sub'}
    parts=re.split(r'(<\s*/?\s*(?:b|strong|i|em|sup|sub|br)\s*/?\s*>)',text,flags=re.I)
    result=[];stack=[]
    for part in parts:
        match=re.fullmatch(r'<\s*(/?)\s*(b|strong|i|em|sup|sub|br)\s*/?\s*>',part,re.I)
        if not match:
            result.append(markdown_inline(part));continue
        name=match[2].lower()
        if name=='br':result.append('<br/>');continue
        tag=tags[name]
        if match[1]:
            if tag in stack:
                while stack:
                    closing=stack.pop();result.append('</'+closing+'>')
                    if closing==tag:break
        else:
            stack.append(tag);result.append('<'+tag+'>')
    result.extend('</'+tag+'>' for tag in reversed(stack))
    return ''.join(result)


def table_cells(line):
    line=line.strip()
    if not line.startswith('|') or not line.endswith('|'):return None
    return [cell.strip() for cell in re.split(r'(?<!\\)\|',line[1:-1])]


def table_blocks(text):
    lines=text.splitlines();i=0
    while i<len(lines):
        row=table_cells(lines[i])
        separator=table_cells(lines[i+1]) if i+1<len(lines) else None
        if row and separator and len(row)==len(separator) and all(re.fullmatch(r':?-{3,}:?',x) for x in separator):
            rows=[row];i+=2
            while i<len(lines):
                cells=table_cells(lines[i])
                if cells is None:break
                rows.append(cells);i+=1
            yield rows
        else:
            yield lines[i];i+=1


def xhtml(title, body):
    return '<?xml version="1.0" encoding="utf-8"?>' + f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="ru" xml:lang="ru"><head><title>{html.escape(title)}</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body>{body}</body></html>'


def export_epub(markdown, destination, title='', author=''):
    """Поддерживает формат собственного OCR: заголовки, абзацы, переводы строк.
    Произвольный HTML из книги никогда не исполняется и не включается как разметка.
    Локальные иллюстрации Marker включаются в EPUB; внешние адреса не загружаются.
    """
    source = Path(markdown)
    text = source.read_text(encoding='utf-8-sig')
    # XML 1.0 не разрешает управляющие символы, кроме tab/CR/LF.
    text = re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    first = re.search(r'^# (.+)$', text, re.M)
    title = title.strip() or (plain(first[1]) if first else source.stem)
    resources = {}
    sections = []
    current = {'title': title, 'body': []}
    paragraph = []
    def flush():
        if paragraph:
            current['body'].append('<p>' + '<br/>'.join(inline(x) for x in paragraph) + '</p>')
            paragraph.clear()
    for line in table_blocks(text):
        if isinstance(line,list):
            flush()
            rows=''.join('<tr>'+''.join('<td>'+inline(cell)+'</td>' for cell in row)+'</tr>' for row in line)
            current['body'].append('<table><tbody>'+rows+'</tbody></table>')
            continue
        if re.fullmatch(r'\s*<!--.*-->\s*', line):
            flush()
            continue
        picture=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line.strip())
        if picture:
            flush()
            image=(source.parent/picture[2]).resolve()
            kinds={'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.gif':'image/gif'}
            if image.is_relative_to(source.parent.resolve()) and image.is_file() and image.suffix.lower() in kinds:
                name=f'images/image-{len(resources)+1:04d}'+image.suffix.lower()
                resources[name]=(image.read_bytes(),kinds[image.suffix.lower()])
                current['body'].append(f'<figure><img src="{name}" alt="{html.escape(picture[1] or "Иллюстрация",quote=True)}"/></figure>')
            else:
                current['body'].append('<p>[Иллюстрация недоступна для экспорта]</p>')
            continue
        if line.strip()=='---':
            flush();current['body'].append('<hr/>');continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading:
            flush()
            level, label = len(heading[1]), plain(heading[2])
            if level <= 2 and current['body']:
                sections.append(current)
                current = {'title': label, 'body': []}
            elif not current['body']:
                current['title'] = label
            current['body'].append(f'<h{level}>{html.escape(label)}</h{level}>')
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.rstrip())
    flush()
    if current['body']:
        sections.append(current)
    if not sections:
        raise ValueError('Markdown пуст: нечего сохранять в EPUB')
    uid = 'urn:uuid:' + str(uuid.uuid4())
    modified = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    manifest = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/>'
    spine, toc = '', ''
    files = {}
    for i, section in enumerate(sections, 1):
        name = f'chapter-{i:04d}.xhtml'
        files['EPUB/'+name] = xhtml(section['title'], '\n'.join(section['body']))
        manifest += f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>'
        spine += f'<itemref idref="c{i}"/>'
        toc += f'<li><a href="{name}">{html.escape(section["title"])}</a></li>'
    for i,(name,(data,mime)) in enumerate(resources.items(),1):
        files['EPUB/'+name]=data
        manifest+=f'<item id="img{i}" href="{name}" media-type="{mime}"/>'
    files['EPUB/nav.xhtml'] = xhtml('Оглавление', f'<nav epub:type="toc" id="toc"><h1>Оглавление</h1><ol>{toc}</ol></nav>')
    creator = f'<dc:creator>{html.escape(author.strip())}</dc:creator>' if author.strip() else ''
    files['EPUB/package.opf'] = f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:language>ru</dc:language>{creator}<meta property="dcterms:modified">{modified}</meta></metadata><manifest>{manifest}</manifest><spine>{spine}</spine></package>'''
    files['META-INF/container.xml'] = '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
    files['EPUB/style.css'] = 'body{line-height:1.55;}p{margin:.6em 0;text-indent:1.2em}h1,h2,h3{line-height:1.2;text-indent:0;break-after:avoid}nav li{margin:.5em 0}img{max-width:100%;height:auto}figure{margin:1em 0}table{width:100%;border-collapse:collapse;margin:1em 0}td{padding:.3em .5em;vertical-align:top;border-bottom:1px solid #ddd;text-indent:0}td:last-child{white-space:normal}'
    # Проверяем XML до атомарной замены файла пользователя.
    for name, value in files.items():
        if name.endswith(('.xml','.opf','.xhtml')):
            ET.fromstring(value)
    destination = Path(destination)
    temporary = destination.with_suffix(destination.suffix+'.tmp')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
            for name, value in files.items():
                z.writestr(name,value.encode('utf-8') if isinstance(value,str) else value)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return len(sections)
