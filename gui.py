#!/usr/bin/env python3
"""28.09.2026 — лёгкий настольный интерфейс DjVuBook; OCR в отдельном процессе."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from epub_export import export_epub
from markdown_export import save_markdown
from project_state import read_state,write_state
from timing import Estimate
from input_source import resolve_source
from marker_runtime import ROOT as MARKER_ROOT

ROOT = Path(__file__).resolve().parent
os.environ['PATH'] = '/opt/homebrew/bin:/usr/local/bin:' + os.environ.get('PATH','')

class App:
    def __init__(self, window):
        self.window = window
        window.title('DjVuBook AudioLab — Markdown, EPUB и аудио')
        window.geometry('800x820')
        window.minsize(690,650)
        self.proc = None
        self.events = queue.Queue()
        self.output = None
        self.markdown = None
        self.source = tk.StringVar()
        self.pages = tk.StringVar(value='all')
        self.title = tk.StringVar()
        self.author = tk.StringVar()
        self.columns = tk.StringVar(value='Автоматически')
        self.engine = tk.StringVar(value='Tesseract — лёгкий')
        self.hyphens = tk.BooleanVar(value=False)
        self.memory_profile=tk.StringVar(value='Экономный — 1 запрос (для 8 ГБ)')
        self.timer=None
        self.time_status=tk.StringVar(value='Прошло 00:00:00 · Осталось: —')
        self.page_status=tk.StringVar(value='Сохранено страниц: 0')
        self.status = tk.StringVar(value='Выберите DjVu или готовый Markdown. Всё работает офлайн.')
        self.dest = ROOT/'books'
        self.stopping = False
        frame = ttk.Frame(window,padding=24)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='DjVuBook AudioLab',font=('Helvetica',24,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Из сканированной книги — в Markdown и EPUB',font=('Helvetica',13)).pack(anchor='w',pady=(2,18))
        row=ttk.Frame(frame);row.pack(fill='x')
        ttk.Button(row,text='Выбрать файл…',command=self.choose_djvu).pack(side='left')
        ttk.Button(row,text='Папка JPEG/HEIC…',command=self.choose_image_folder).pack(side='left',padx=8)
        ttk.Button(row,text='Открыть Markdown…',command=self.choose_markdown).pack(side='left',padx=8)
        ttk.Button(row,text='Папка сохранения…',command=self.choose_dest).pack(side='right')
        ttk.Label(frame,textvariable=self.source,wraplength=700).pack(anchor='w',pady=(8,14))
        engines=ttk.Frame(frame);engines.pack(fill='x',pady=(0,10))
        ttk.Label(engines,text='Распознавание').pack(side='left',padx=(0,12))
        picker=ttk.Combobox(engines,textvariable=self.engine,state='readonly',values=['Tesseract — лёгкий','Marker — внешний диск'],width=35)
        picker.pack(side='left');picker.bind('<<ComboboxSelected>>',self.engine_changed)
        memory=ttk.Frame(frame);memory.pack(fill='x',pady=(0,8))
        ttk.Label(memory,text='Память Marker').pack(side='left',padx=(0,12))
        ttk.Combobox(memory,textvariable=self.memory_profile,state='readonly',width=45,values=['Экономный — 1 запрос (для 8 ГБ)','Больше памяти — 2 запроса']).pack(side='left')
        ttk.Label(frame,text='Это параллелизм, не лимит ГБ. На 8 ГБ второй режим может замедлить Mac из-за подкачки.',wraplength=700).pack(anchor='w')
        form=ttk.Frame(frame);form.pack(fill='x')
        form.columnconfigure(1,weight=1)
        for n,(label,var) in enumerate([('Название книги',self.title),('Автор (необязательно)',self.author),('Страницы DjVu',self.pages)]):
            ttk.Label(form,text=label).grid(row=n,column=0,sticky='w',padx=(0,12),pady=5)
            ttk.Entry(form,textvariable=var).grid(row=n,column=1,sticky='ew',pady=5)
        ttk.Label(form,text='all — вся книга; 1-12 или 1,5,20-25 — часть',foreground='#666666').grid(row=3,column=1,sticky='w')
        ttk.Label(form,text='Разметка').grid(row=4,column=0,sticky='w',pady=8)
        self.column_picker=ttk.Combobox(form,textvariable=self.columns,state='readonly',values=['Автоматически','Один текстовый блок','Две равные колонки'])
        self.column_picker.grid(row=4,column=1,sticky='ew',pady=8)
        self.hyphen_box=ttk.Checkbutton(frame,text='Склеивать переносы слов (может убрать настоящий дефис)',variable=self.hyphens)
        self.hyphen_box.pack(anchor='w')
        actions=ttk.Frame(frame);actions.pack(fill='x',pady=(18,12))
        self.start_button=ttk.Button(actions,text='Распознать книгу',command=self.start)
        self.start_button.pack(side='left')
        self.stop_button=ttk.Button(actions,text='Остановить',command=self.stop,state='disabled')
        self.stop_button.pack(side='left',padx=8)
        ttk.Label(frame,textvariable=self.page_status).pack(anchor='w')
        ttk.Label(frame,textvariable=self.time_status).pack(anchor='w')
        ttk.Button(frame,text='Открыть текущий EPUB',command=self.open_current_epub).pack(anchor='w')
        self.progress=ttk.Progressbar(frame,mode='determinate');self.progress.pack(fill='x')
        ttk.Label(frame,textvariable=self.status,wraplength=700).pack(anchor='w',pady=10)
        export=ttk.Frame(frame);export.pack(fill='x',pady=(4,8))
        self.md_button=ttk.Button(export,text='Сохранить Markdown…',command=self.save_md,state='disabled');self.md_button.pack(side='left')
        self.epub_button=ttk.Button(export,text='Сохранить EPUB…',command=self.save_epub,state='disabled');self.epub_button.pack(side='left',padx=8)
        self.review_button=ttk.Button(export,text='Сверить со сканами',command=self.review,state='disabled');self.review_button.pack(side='left')
        ttk.Label(frame,text='EPUB содержит текст, оглавление и локальные иллюстрации Marker.\nСложные таблицы и ошибки OCR требуют проверки.',foreground='#666666',wraplength=700).pack(anchor='w',pady=(8,0))
        logs=ttk.Frame(frame);logs.pack(fill='x',pady=(8,4))
        ttk.Label(logs,text='Журнал работы').pack(side='left')
        ttk.Button(logs,text='Сохранить журнал…',command=self.save_log).pack(side='right')
        self.log_view=tk.Text(frame,height=7,wrap='word',state='disabled')
        self.log_view.pack(fill='both',expand=True)
        self.preferences_path=ROOT/'preferences.json'
        self.preferences=read_state(self.preferences_path)
        self.save_timer=None
        self.restore_selection(self.preferences.get('source',''))
        for variable in (self.source,self.pages,self.title,self.author,self.engine,self.columns,self.hyphens,self.memory_profile):
            variable.trace_add('write',self.schedule_save)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.after(100,self.poll)
        if len(sys.argv)>1 and Path(sys.argv[1]).suffix.lower()=='.md':
            self.load_md(Path(sys.argv[1]))

    def schedule_save(self,*args):
        if self.save_timer:self.window.after_cancel(self.save_timer)
        self.save_timer=self.window.after(300,self.save_preferences)

    def save_preferences(self):
        self.save_timer=None
        path=self.source.get()
        data={key:getattr(self,key).get() for key in ('pages','title','author','engine','columns','hyphens','memory_profile')}
        data['destination']=str(self.dest)
        self.preferences['source']=path
        self.preferences.setdefault('files',{})[path]=data
        try:write_state(self.preferences_path,self.preferences)
        except OSError as error:self.status.set('Не удалось сохранить настройки: '+str(error))

    def restore_selection(self,path):
        if not path:return
        data=self.preferences.get('files',{}).get(path,{})
        self.source.set(path)
        self.title.set(data.get('title',Path(path).stem))
        for key in ('pages','author','engine','columns','hyphens','memory_profile'):
            if key in data:getattr(self,key).set(data[key])
        self.engine_changed()
        if data.get('destination'):self.dest=Path(data['destination'])
        self.status.set('Восстановлены файл и настройки. Нажмите «Распознать книгу» для продолжения.')

    def append_log(self,text):
        self.log_view.configure(state='normal')
        self.log_view.insert('end',text)
        self.log_view.see('end')
        self.log_view.configure(state='disabled')
        if self.output:
            try:
                if getattr(self,'active_marker',False) and not MARKER_ROOT.exists():
                    raise OSError('Внешний диск отключён')
                self.output.mkdir(parents=True,exist_ok=True)
                with (self.output/'session.log').open('a',encoding='utf-8') as stream:
                    stream.write(text)
            except OSError:
                # The in-memory log and event loop must survive a missing disk.
                self.status.set('Не удалось записать журнал на диск. Журнал остаётся в окне.')

    def save_log(self):
        target=filedialog.asksaveasfilename(title='Сохранить журнал',initialfile='DjVuBook-log.txt',defaultextension='.txt')
        if not target:return
        try:
            text=self.log_view.get('1.0','end')
            if self.output:
                for path in sorted(self.output.rglob('marker.log')):
                    text+='\n\n--- '+str(path.relative_to(self.output))+' ---\n'+path.read_text(errors='replace')[-100000:]
            Path(target).write_text(text,encoding='utf-8')
        except Exception as e:messagebox.showerror('Ошибка журнала',str(e))

    def engine_changed(self,event=None):
        marker=self.engine.get().startswith('Marker')
        self.dest=MARKER_ROOT/'results/books' if marker else ROOT/'books'
        self.column_picker.configure(state='disabled' if marker else 'readonly')
        self.hyphen_box.configure(state='disabled' if marker else 'normal')
        if self.proc is None:
            self.status.set('Marker: проверьте выбранный внешний каталог. Сначала попробуйте 3–4 страницы.' if marker else 'Tesseract: быстрый локальный режим.')

    def busy(self):
        if self.proc is not None:
            messagebox.showinfo('Идёт распознавание','Дождитесь окончания или нажмите «Остановить».')
            return True
        return False

    def choose_djvu(self):
        if self.busy():return
        p=filedialog.askopenfilename(title='Выберите DjVu или PDF',filetypes=[('Книги','*.djvu *.djv *.pdf'),('Все файлы','*')])
        if p:
            self.save_preferences()
            self.restore_selection(p)
            self.markdown=None;self.output=None;self.set_exports(False)
            self.status.set('Готово к распознаванию. При повторном запуске используется кэш.')

    def choose_image_folder(self):
        if self.busy():return
        p=filedialog.askdirectory(title='Выберите папку с JPEG, PNG или HEIC')
        if p:
            self.save_preferences();self.restore_selection(p)
            self.markdown=None;self.output=None;self.set_exports(False)
            self.title.set(Path(p).name)
            self.status.set('Изображения будут упорядочены по имени и собраны в страницы книги.')

    def choose_markdown(self):
        if self.busy():return
        p=filedialog.askopenfilename(title='Выберите готовый Markdown',filetypes=[('Markdown','*.md'),('Все файлы','*')])
        if p:self.load_md(Path(p))

    def load_md(self,p):
        try:
            text=p.read_text(encoding='utf-8-sig')
        except Exception as e:
            messagebox.showerror('Не удалось открыть',str(e));return
        self.markdown=p;self.output=p.parent;self.source.set(str(p))
        match=re.search(r'^# (.+)$',text,re.M)
        self.title.set(match[1] if match else p.stem)
        self.set_exports(True)
        self.status.set('Markdown открыт. Можно сразу сохранить EPUB — повторный OCR не нужен.')

    def choose_dest(self):
        if self.busy():return
        p=filedialog.askdirectory(title='Где сохранять результаты?',initialdir=str(self.dest if self.dest.exists() else ROOT))
        if p:self.dest=Path(p);self.status.set('Папка результатов: '+p);self.save_preferences()

    def set_exports(self,enabled):
        state='normal' if enabled else 'disabled'
        self.md_button.configure(state=state);self.epub_button.configure(state=state)
        self.review_button.configure(state='normal' if enabled and self.output and (self.output/'review.html').exists() else 'disabled')

    def start(self):
        if self.busy():return
        source=Path(self.source.get())
        if not source.exists() or not (source.is_dir() or source.suffix.lower() in ('.djvu','.djv','.pdf')):
            messagebox.showinfo('Выберите источник','Выберите DjVu/PDF или папку с JPEG/PNG/HEIC.');return
        self.save_preferences()
        mode={'Автоматически':'auto','Один текстовый блок':'1','Две равные колонки':'2'}[self.columns.get()]
        marker=self.engine.get().startswith('Marker')
        if marker and not (MARKER_ROOT/'venv/bin/marker_single').is_file():
            messagebox.showerror('Нет окружения Marker','Проверьте выбранную папку с установленным Marker.');return
        spec=json.dumps([str(source.resolve()),self.pages.get(),mode,self.hyphens.get(),self.engine.get()])
        key=hashlib.sha256(spec.encode()).hexdigest()[:10]
        self.output=self.dest/((source.stem if source.is_file() else source.name+'-images')+'-'+key)
        try:
            resolved,kind=resolve_source(source,self.output)
        except Exception as error:
            messagebox.showerror('Не удалось подготовить входные файлы',str(error));return
        input_path=source if marker else resolved
        args=[sys.executable,str(ROOT/('marker_backend.py' if marker else 'djvubook.py')),str(input_path),'--output',str(self.output),'--pages',self.pages.get()]
        if marker:
            args.extend(['--title',self.title.get(),'--author',self.author.get()])
            args.extend(['--memory-profile','economy' if self.memory_profile.get().startswith('Экономный') else 'parallel'])
        if not marker:
            args.extend(['--columns',mode])
            if self.hyphens.get():args.append('--dehyphenate')
        self.markdown=None;self.set_exports(False);self.progress['value']=0
        self.active_marker=marker
        self.progress.configure(mode='indeterminate' if marker else 'determinate')
        if marker:self.progress.start(18)
        self.start_button.configure(state='disabled');self.stop_button.configure(state='normal')
        self.status.set('Подготовка книги…');self.stopping=False
        self.append_log('\n'+time.strftime('%Y-%m-%d %H:%M:%S')+' · Запуск '+self.engine.get()+'\n')
        self.started_at=time.time()
        self.timer=Estimate(time.monotonic())
        try:
            self.proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        except Exception as e:
            self.progress.stop();self.proc=None;self.start_button.configure(state='normal');self.stop_button.configure(state='disabled');messagebox.showerror('Ошибка запуска',str(e));return
        proc=self.proc
        def worker():
            tail=[]
            for line in proc.stdout:
                tail.append(line);tail=tail[-12:];self.events.put(('line',line))
            self.events.put(('done',(proc.wait(),''.join(tail))))
        threading.Thread(target=worker,daemon=True).start()

    def refresh_live_exports(self):
        if self.proc is None or self.output is None:return
        try:
            md=self.output/'book.md'
            if md.is_file() and md.stat().st_size:
                self.markdown=md
                self.set_exports(True)
        except OSError:
            pass  # A disconnected disk must not stop the UI event loop.

    def export_destination_allowed(self,path):
        if self.proc is not None and self.output and Path(path).resolve().is_relative_to(self.output.resolve()):
            messagebox.showinfo('Сохранение копии','Выберите папку вне рабочей папки распознавания, чтобы сохранить отдельную копию и не перезаписать текущие результаты OCR.')
            return False
        return True

    def poll(self):
        try:
            self.refresh_live_exports()
            if self.proc is not None and self.timer:self.time_status.set(self.timer.label(time.monotonic()))
            while True:
                kind,data=self.events.get_nowait()
                if kind=='line':
                    self.append_log(data)
                    m=re.match(r'\[(\d+)/(\d+)\]',data)
                    if m:
                        if self.timer:self.timer.update(int(m[1]),int(m[2]),time.monotonic())
                        self.page_status.set(f'Сохранено страниц: {m[1]} из {m[2]}')
                        if not getattr(self,'active_marker',False):
                            self.progress['maximum']=int(m[2]);self.progress['value']=int(m[1])
                        self.status.set(data.strip())
                    elif data.startswith(('Ошибка','Marker:')):self.status.set(data.strip())
                else:
                    code,details=data;self.proc=None
                    self.progress.stop();self.progress.configure(mode='determinate')
                    self.start_button.configure(state='normal');self.stop_button.configure(state='disabled')
                    md=self.output/'book.md'
                    if md.exists() and md.stat().st_mtime >= self.started_at:
                        self.markdown=md;self.set_exports(True)
                    if self.stopping:
                        self.status.set('Остановлено. Готовые страницы сохранены; экспорт может быть неполным.')
                    elif code==0:
                        self.progress['maximum']=1;self.progress['value']=1
                        self.status.set('Готово. Сохраните Markdown или EPUB; результат уже находится в папке книги.')
                    else:
                        self.status.set('Есть ошибка. Если часть страниц готова, можно экспортировать неполную книгу.')
                        messagebox.showerror('Ошибка распознавания',details)
        except queue.Empty:pass
        except OSError as error:
            self.status.set('Диск недоступен: '+str(error))
        finally:
            self.window.after(100,self.poll)

    def stop(self):
        if not self.proc:return
        proc=self.proc
        self.stopping=True
        try:
            if proc.poll() is None:proc.send_signal(signal.SIGINT)
        except ProcessLookupError:pass
        self.stop_button.configure(state='disabled')
        self.status.set('Останавливаем; готовые страницы останутся в кэше…')
        def force_stop():
            if self.proc is proc and proc.poll() is None:
                proc.terminate()
                self.window.after(5000,lambda:proc.kill() if proc.poll() is None else None)
        self.window.after(50000,force_stop)

    def save_md(self):
        if not self.markdown:return
        p=filedialog.asksaveasfilename(title='Сохранить Markdown',defaultextension='.md',initialfile='book.md',filetypes=[('Markdown','*.md')])
        if p and self.export_destination_allowed(p):
            try:
                save_markdown(self.markdown,p);self.status.set('Сохранена текущая копия Markdown: '+p)
            except Exception as e:messagebox.showerror('Ошибка сохранения',str(e))

    def open_current_epub(self):
        path=self.output/'book.epub' if self.output else None
        if path and path.exists():subprocess.Popen(['open',str(path)])
        else:messagebox.showinfo('EPUB','EPUB появится после первой сохранённой страницы.')

    def save_epub(self):
        if not self.markdown:return
        p=filedialog.asksaveasfilename(title='Сохранить EPUB',defaultextension='.epub',initialfile='book.epub',filetypes=[('EPUB','*.epub')])
        if p and self.export_destination_allowed(p):
            try:
                n=export_epub(self.markdown,p,self.title.get(),self.author.get())
                self.status.set(f'Текущая копия EPUB сохранена: {p}. Разделов: {n}.')
            except Exception as e:messagebox.showerror('Ошибка EPUB',str(e))

    def review(self):
        if self.output:subprocess.Popen(['open',str(self.output/'review.html')])

    def close(self):
        if self.proc is not None:
            messagebox.showinfo('Идёт распознавание','Сначала нажмите «Остановить» и дождитесь сохранения результатов.');return
        self.save_preferences()
        self.window.destroy()

if __name__=='__main__':
    window=tk.Tk();app=App(window);window.mainloop()
