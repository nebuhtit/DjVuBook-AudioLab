"""Instrument the installed Marker without modifying third-party files."""
import functools
import time

def event(message):
    print(time.strftime('%H:%M:%S')+' · '+message,flush=True)

def main():
    event('Этап 1/5: импорт PyTorch и Marker с внешнего диска (модели ещё не загружены)')
    from marker.scripts.convert_single import convert_single_cli
    import surya.inference.backends.spawn as spawn
    import surya.inference.backends.llamacpp as llama
    import surya.common.batch_service.client as batch
    from surya.layout import LayoutPredictor
    from surya.recognition import RecognitionPredictor
    event('Этап 1/5 завершён: библиотеки импортированы')
    event('План balanced: 2 нейросетевые службы — Surya OCR 2 (расположение блоков и текст; файлы surya-2.gguf + surya-2-mmproj.gguf) и OCR Error Detection (проверка текстового слоя). RF-DETR в этом режиме не нужен. Службы запускаются по необходимости.')
    ready=set()
    original=spawn.attach_or_spawn
    @functools.wraps(original)
    def attach(*args,**kwargs):
        name=kwargs.get('backend','unknown')
        model=kwargs.get('expected_model_name','не указан')
        started=time.monotonic()
        event(f'Этап 2/5: запуск или подключение службы {name}; модель {model}; готово служб {len(ready)}/2')
        result=original(*args,**kwargs)
        ready.add(name)
        event(f'Служба {name} отвечает: модель готова к запросам; готово служб {len(ready)}/2; ожидание {time.monotonic()-started:.1f} с')
        return result
    spawn.attach_or_spawn=attach
    llama.attach_or_spawn=attach
    batch.attach_or_spawn=attach
    old_stop=spawn._stop_process
    def stop(pid,name):
        event(f'Этап 5/5: завершение вспомогательного процесса {name}, PID {pid}')
        result=old_stop(pid,name)
        event(f'Завершение процесса {name}: процедура очистки закончена')
        return result
    spawn._stop_process=stop
    def instrument(cls,label):
        original_call=cls.__call__
        @functools.wraps(original_call)
        def call(self,*args,**kwargs):
            event('Этап 3/5: '+label)
            start=time.monotonic()
            result=original_call(self,*args,**kwargs)
            event(label+f': завершено за {time.monotonic()-start:.1f} с')
            return result
        cls.__call__=call
    instrument(LayoutPredictor,'Анализ расположения блоков страницы')
    instrument(RecognitionPredictor,'Распознавание текста')
    import marker.scripts.convert_single as cli
    save=cli.save_output
    def save_output(*args,**kwargs):
        event('Этап 4/5: запись Markdown и иллюстраций')
        result=save(*args,**kwargs)
        event('Markdown и иллюстрации записаны; осталось завершить службы')
        return result
    cli.save_output=save_output
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='--book-job':
        run_book(sys.argv[2])
    else:
        convert_single_cli()

def run_book(job_path):
    import json,os,subprocess
    from pathlib import Path
    from marker.models import create_model_dict
    from marker.converters.pdf import PdfConverter
    from marker.output import save_output
    from marker_backend import atomic_text,publish
    job=json.loads(Path(job_path).read_text());out=Path(job['output'])
    models=create_model_dict()
    event('Одна сессия на всю очередь: модели остаются в памяти между страницами')
    for page in job['pending']:
        event(f'Начата физическая страница DjVu {page}')
        folder=out/f'page-{page:06d}';folder.mkdir(exist_ok=True)
        pdf=folder/'source.pdf'
        if job.get('source_kind')=='pdf':
            subprocess.run(['qpdf',job['source'],'--pages',job['source'],str(page),'--',str(pdf)],check=True)
        else:
            subprocess.run(['ddjvu','-format=pdf','-size=2600x7800',f'-page={page}',job['source'],str(pdf)],check=True)
        converter=PdfConverter(artifact_dict=models,config={'mode':'balanced','force_ocr':True,'paginate_output':True,'keep_pageheader_in_output':True,'use_llm':False})
        rendered=converter(str(pdf))
        destination=folder/'result/source';destination.mkdir(parents=True,exist_ok=True)
        save_output(rendered,str(destination),'source')
        if not (destination/'source.md').is_file():raise RuntimeError('Не создан Markdown страницы')
        atomic_text(folder/'ready.json',json.dumps({'pages':[page]}))
        publish(out,job['pages'],job['source'],job['title'],job['author'])
        del rendered,converter

if __name__=='__main__':main()
