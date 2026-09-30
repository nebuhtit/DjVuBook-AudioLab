"""Prepare image folders as an ordered local PDF for existing OCR engines."""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess

IMAGE_EXTS={'.jpg','.jpeg','.png','.heic','.heif'}

def natural_key(path):
    return [(0,int(piece)) if piece.isdigit() else (1,piece.casefold())
            for piece in re.split(r'(\d+)',Path(path).name)]

def tree_digest(path):
    path=Path(path)
    if path.is_file():
        h=hashlib.sha256();h.update(path.read_bytes());return h.hexdigest()
    h=hashlib.sha256()
    for file in sorted((p for p in path.rglob('*') if p.is_file()),key=natural_key):
        h.update(file.relative_to(path).as_posix().encode());h.update(file.stat().st_size.to_bytes(8,'big'))
        with file.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def prepare_images(folder,destination):
    folder=Path(folder);destination=Path(destination)
    images=sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS),key=natural_key)
    if not images:raise ValueError('В папке не найдены JPEG, PNG или HEIC изображения.')
    manifest=destination.with_suffix('.images.json')
    fingerprint=tree_digest(folder)
    if destination.is_file() and manifest.is_file() and manifest.read_text()==fingerprint:
        return destination
    if not shutil.which('sips') or not shutil.which('pdfunite'):raise RuntimeError('Для конвертации изображений нужны sips и pdfunite (macOS + Poppler).')
    work=destination.parent/'image-pages';work.mkdir(parents=True,exist_ok=True)
    pages=[]
    for i,image in enumerate(images,1):
        out=work/f'{i:06d}.pdf'
        subprocess.run(['sips','-s','format','pdf',str(image),'--out',str(out)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        pages.append(out)
    temporary=destination.with_suffix('.pdf.tmp')
    subprocess.run(['pdfunite',*map(str,pages),str(temporary)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    temporary.replace(destination)
    manifest.write_text(fingerprint)
    return destination

def resolve_source(source,out):
    source=Path(source).resolve()
    if source.is_dir():return prepare_images(source,Path(out)/'prepared-images.pdf'),'pdf'
    if source.suffix.lower()=='.pdf':return source,'pdf'
    if source.suffix.lower() in ('.djvu','.djv'):return source,'djvu'
    raise ValueError('Выберите DjVu, PDF или папку изображений JPEG/HEIC.')
