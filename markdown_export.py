"""28.09.2026 — сохранить Markdown вместе с локальными рисунками Marker."""
from pathlib import Path
import hashlib
import re
import shutil

def save_markdown(source,destination):
    source=Path(source).resolve();destination=Path(destination).resolve()
    text=source.read_text(encoding='utf-8')
    if source==destination:return
    assets=destination.parent/(destination.stem+'-images')
    def copy_image(match):
        link=match[2]
        if ':' in link or link.startswith('/'):
            return match[0]
        original=(source.parent/link).resolve()
        # Не копируем произвольные файлы из ссылок, созданных OCR.
        if not original.is_relative_to(source.parent) or not original.is_file():return match[0]
        if original.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.gif'):return match[0]
        name=hashlib.sha256(original.read_bytes()).hexdigest()[:16]+original.suffix.lower()
        assets.mkdir(exist_ok=True)
        shutil.copyfile(original,assets/name)
        return match[1]+assets.name+'/'+name+match[3]
    text=re.sub(r'(!\[[^\]]*\]\()([^):\s]+)(\))',copy_image,text)
    temporary=destination.with_suffix(destination.suffix+'.tmp')
    temporary.write_text(text,encoding='utf-8');temporary.replace(destination)
