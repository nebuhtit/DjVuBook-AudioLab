import AppKit
import CryptoKit
import UniformTypeIdentifiers

final class AudioLab: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var sourceField = NSTextField(string: "")
    var textInput = NSTextView()
    var language = NSPopUpButton()
    var voice = NSPopUpButton()
    var ocrLibraryField = NSTextField(string: "")
    var ttsLibraryField = NSTextField(string: "")
    var speedSlider = NSSlider(value:1.0,minValue:0.7,maxValue:1.5,target:nil,action:nil)
    var sentencePauseSlider = NSSlider(value:0.6,minValue:0.2,maxValue:2.0,target:nil,action:nil)
    var paragraphPauseSlider = NSSlider(value:1.8,minValue:0.8,maxValue:5.0,target:nil,action:nil)
    var speedValue = NSTextField(labelWithString:"1.00×")
    var sentencePauseValue = NSTextField(labelWithString:"0.6 с")
    var paragraphPauseValue = NSTextField(labelWithString:"1.8 с")
    var speechProgress = NSProgressIndicator()
    var speechProcess: Process?
    var stopSpeechButton: NSButton!
    var previewVoiceButton: NSButton!
    var previewOutput: URL?
    var loadedOCRText = false
    var pagesField = NSTextField(string: "all")
    var titleField = NSTextField(string: "")
    var authorField = NSTextField(string: "")
    var engine = NSPopUpButton()
    var memory = NSPopUpButton()
    var status = NSTextField(labelWithString: "Выберите DjVu, PDF или папку JPEG/HEIC")
    var timeLabel = NSTextField(labelWithString: "Прошло 00:00:00 · Осталось: —")
    var progress = NSProgressIndicator()
    var log = NSTextView()
    var startButton: NSButton!
    var stopButton: NSButton!
    var mdButton: NSButton!
    var epubButton: NSButton!
    var speakButton: NSButton!
    var speechNotice = NSTextField(labelWithString: "Офлайн-голос Silero пока не установлен")
    var process: Process?
    var startedAt: Date?
    var progressSamples: [(Date, Int)] = []
    var progressDone=0
    var progressTotal=0
    var output: URL?
    var root: URL {
        Bundle.main.bundleURL.deletingLastPathComponent()
    }
    var python: URL { URL(fileURLWithPath: "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3") }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:850,height:760), styleMask:[.titled,.closable,.miniaturizable,.resizable], backing:.buffered, defer:false)
        window.title = "DjVuBook AudioLab"
        window.center()
        let main = NSStackView(); main.orientation = .vertical; main.alignment = .leading; main.spacing = 10; main.edgeInsets = NSEdgeInsets(top:20,left:22,bottom:18,right:22)
        main.translatesAutoresizingMaskIntoConstraints = false
        let outerScroll=NSScrollView();outerScroll.hasVerticalScroller=true;outerScroll.autohidesScrollers=false;outerScroll.translatesAutoresizingMaskIntoConstraints=false
        window.contentView!.addSubview(outerScroll)
        outerScroll.documentView=main
        NSLayoutConstraint.activate([outerScroll.leadingAnchor.constraint(equalTo:window.contentView!.leadingAnchor),outerScroll.trailingAnchor.constraint(equalTo:window.contentView!.trailingAnchor),outerScroll.topAnchor.constraint(equalTo:window.contentView!.topAnchor),outerScroll.bottomAnchor.constraint(equalTo:window.contentView!.bottomAnchor),main.leadingAnchor.constraint(equalTo:outerScroll.contentView.leadingAnchor),main.trailingAnchor.constraint(equalTo:outerScroll.contentView.trailingAnchor),main.topAnchor.constraint(equalTo:outerScroll.contentView.topAnchor),main.widthAnchor.constraint(equalTo:outerScroll.contentView.widthAnchor),main.heightAnchor.constraint(greaterThanOrEqualTo:outerScroll.contentView.heightAnchor)])
        let heading=NSTextField(labelWithString:"DjVuBook AudioLab"); heading.font=NSFont.boldSystemFont(ofSize:23); main.addArrangedSubview(heading)
        let pick=NSButton(title:"Выбрать файл или папку…",target:self,action:#selector(choose)); main.addArrangedSubview(pick)
        sourceField.isEditable=false;sourceField.lineBreakMode = .byTruncatingMiddle;sourceField.widthAnchor.constraint(greaterThanOrEqualToConstant:700).isActive=true;main.addArrangedSubview(sourceField)
        let textActions=NSStackView();textActions.spacing=8
        let importButton=NSButton(title:"Импортировать TXT, MD, HTML или Word…",target:self,action:#selector(importDocument));textActions.addArrangedSubview(importButton)
        let pasteButton=NSButton(title:"Вставить из буфера обмена",target:self,action:#selector(pasteFromClipboard));textActions.addArrangedSubview(pasteButton);main.addArrangedSubview(textActions)
        let textTitle=NSTextField(labelWithString:"Текст книги — можно писать прямо в этом поле");textTitle.font=NSFont.boldSystemFont(ofSize:14);main.addArrangedSubview(textTitle)
        let textScroll=NSScrollView();textScroll.hasVerticalScroller=true;textScroll.borderType = .bezelBorder;textScroll.documentView=textInput;textInput.isEditable=true;textInput.font=NSFont.systemFont(ofSize:14);textInput.minSize=NSSize(width:0,height:120);textInput.maxSize=NSSize(width:CGFloat.greatestFiniteMagnitude,height:CGFloat.greatestFiniteMagnitude);textInput.isVerticallyResizable=true;textInput.isHorizontallyResizable=false;textInput.autoresizingMask=[.width];textScroll.heightAnchor.constraint(equalToConstant:140).isActive=true;textScroll.widthAnchor.constraint(equalToConstant:730).isActive=true
        let textMenu=NSMenu();textMenu.addItem(withTitle:"Вставить",action:#selector(NSText.paste(_:)),keyEquivalent:"v").target=nil;textMenu.addItem(withTitle:"Копировать",action:#selector(NSText.copy(_:)),keyEquivalent:"").target=nil;textMenu.addItem(withTitle:"Вырезать",action:#selector(NSText.cut(_:)),keyEquivalent:"").target=nil;textMenu.addItem(.separator());textMenu.addItem(withTitle:"Выделить всё",action:#selector(NSText.selectAll(_:)),keyEquivalent:"a").target=nil;textInput.menu=textMenu;main.addArrangedSubview(textScroll)
        engine.addItems(withTitles:["Marker — внешний диск","Tesseract — лёгкий"]);engine.selectItem(at:0)
        memory.addItems(withTitles:["Экономный — один запрос","Больше памяти — два запроса"])
        let choices=NSStackView(views:[label("OCR"),engine,label("Память"),memory]);choices.spacing=8;main.addArrangedSubview(choices)
        addDirectoryRow(title:"Окружение OCR / Marker",field:ocrLibraryField,key:"ocrLibraryRoot",fallback:"/Volumes/DjVuBookLibraries/DjVuBook-Marker",to:main)
        addDirectoryRow(title:"Окружение озвучивания / Silero",field:ttsLibraryField,key:"ttsLibraryRoot",fallback:"/Volumes/DjVuBookLibraries/DjVuBook-Marker",to:main)
        titleField.placeholderString="Название книги";authorField.placeholderString="Автор (необязательно)";pagesField.stringValue="all"
        for (name,field) in [("Название",titleField),("Автор",authorField),("Страницы",pagesField)] { let row=NSStackView(views:[label(name),field]);row.spacing=10;field.widthAnchor.constraint(equalToConstant:570).isActive=true;main.addArrangedSubview(row) }
        let buttons=NSStackView();buttons.spacing=8
        startButton=NSButton(title:"Распознать / продолжить",target:self,action:#selector(start));buttons.addArrangedSubview(startButton)
        stopButton=NSButton(title:"Остановить OCR",target:self,action:#selector(stop));stopButton.isEnabled=false;buttons.addArrangedSubview(stopButton)
        mdButton=NSButton(title:"Сохранить Markdown…",target:self,action:#selector(saveMD));mdButton.isEnabled=false;buttons.addArrangedSubview(mdButton)
        epubButton=NSButton(title:"Сохранить EPUB…",target:self,action:#selector(saveEPUB));epubButton.isEnabled=false;buttons.addArrangedSubview(epubButton)
        main.addArrangedSubview(buttons)
        let speechRow=NSStackView();speechRow.spacing=8
        language.addItems(withTitles:["Русский","English"]);language.selectItem(at:0);language.target=self;language.action=#selector(languageChanged);speechRow.addArrangedSubview(language)
        updateVoiceOptions();speechRow.addArrangedSubview(voice)
        speakButton=NSButton(title:"Озвучить и сохранить MP3…",target:self,action:#selector(speakText));speakButton.isEnabled=false;speechRow.addArrangedSubview(speakButton)
        previewVoiceButton=NSButton(title:"Прослушать пример",target:self,action:#selector(previewVoice));speechRow.addArrangedSubview(previewVoiceButton)
        stopSpeechButton=NSButton(title:"Остановить озвучивание",target:self,action:#selector(stopSpeech));stopSpeechButton.isEnabled=false;speechRow.addArrangedSubview(stopSpeechButton)
        main.addArrangedSubview(speechRow)
        speedSlider.target=self;speedSlider.action=#selector(speechSettingsChanged);speedSlider.numberOfTickMarks=17
        sentencePauseSlider.target=self;sentencePauseSlider.action=#selector(speechSettingsChanged);sentencePauseSlider.numberOfTickMarks=10
        paragraphPauseSlider.target=self;paragraphPauseSlider.action=#selector(speechSettingsChanged);paragraphPauseSlider.numberOfTickMarks=15
        speedValue.widthAnchor.constraint(equalToConstant:55).isActive=true;sentencePauseValue.widthAnchor.constraint(equalToConstant:55).isActive=true;paragraphPauseValue.widthAnchor.constraint(equalToConstant:55).isActive=true
        for (title,slider,value) in [("Скорость чтения",speedSlider,speedValue),("Пауза между предложениями",sentencePauseSlider,sentencePauseValue),("Пауза между абзацами",paragraphPauseSlider,paragraphPauseValue)] {let row=NSStackView(views:[label(title),slider,value]);row.spacing=10;slider.widthAnchor.constraint(equalToConstant:430).isActive=true;main.addArrangedSubview(row)}
        speechNotice.textColor = .secondaryLabelColor;main.addArrangedSubview(speechNotice)
        let voiceInfo=NSTextField(wrappingLabelWithString:"Русские голоса подписаны по полу. У английской модели только номера голосов без надёжных описаний, поэтому выберите вариант и нажмите «Прослушать пример».");voiceInfo.textColor = .secondaryLabelColor;main.addArrangedSubview(voiceInfo)
        speechProgress.isIndeterminate=true;speechProgress.isDisplayedWhenStopped=false;speechProgress.widthAnchor.constraint(equalToConstant:730).isActive=true;main.addArrangedSubview(speechProgress)
        status.lineBreakMode = .byWordWrapping;main.addArrangedSubview(status)
        main.addArrangedSubview(timeLabel)
        progress.isIndeterminate=false;progress.maxValue=1;progress.isDisplayedWhenStopped=false;progress.widthAnchor.constraint(equalToConstant:720).isActive=true;main.addArrangedSubview(progress)
        let scroll=NSScrollView();scroll.hasVerticalScroller=true;scroll.documentView=log;log.isEditable=false;log.font=NSFont.monospacedSystemFont(ofSize:11,weight:.regular);scroll.heightAnchor.constraint(greaterThanOrEqualToConstant:200).isActive=true;scroll.widthAnchor.constraint(equalToConstant:730).isActive=true;main.addArrangedSubview(scroll)
        NotificationCenter.default.addObserver(self,selector:#selector(textChanged),name:NSText.didChangeNotification,object:textInput)
        restore();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true);window.makeFirstResponder(textInput)
    }
    func label(_ text:String)->NSTextField { NSTextField(labelWithString:text) }
    func addDirectoryRow(title:String,field:NSTextField,key:String,fallback:String,to stack:NSStackView){
        field.stringValue=UserDefaults.standard.string(forKey:key) ?? fallback
        field.isEditable=false;field.lineBreakMode = .byTruncatingMiddle
        let button=NSButton(title:"Выбрать…",target:self,action:#selector(selectLibraryDirectory(_:)))
        button.identifier=NSUserInterfaceItemIdentifier(key)
        field.widthAnchor.constraint(equalToConstant:495).isActive=true
        let row=NSStackView(views:[label(title),field,button]);row.spacing=8;stack.addArrangedSubview(row)
    }
    @objc func selectLibraryDirectory(_ sender:NSButton){
        guard let key=sender.identifier?.rawValue else{return}
        let panel=NSOpenPanel();panel.canChooseFiles=false;panel.canChooseDirectories=true;panel.allowsMultipleSelection=false;panel.message="Выберите папку установленного окружения библиотек"
        if panel.runModal() == .OK,let url=panel.url{
            if key=="ocrLibraryRoot"{ocrLibraryField.stringValue=url.path}else{ttsLibraryField.stringValue=url.path}
            UserDefaults.standard.set(url.path,forKey:key);speechNotice.stringValue="Путь библиотек сохранён: \(url.path)"
        }
    }
    @objc func choose() {
        let p=NSOpenPanel();p.canChooseFiles=true;p.canChooseDirectories=true;p.allowsMultipleSelection=false;p.message="DjVu/PDF файлы или папка с JPEG/PNG/HEIC"
        if p.runModal() == .OK, let url=p.url { sourceField.stringValue=url.path;if titleField.stringValue.isEmpty{titleField.stringValue=url.deletingPathExtension().lastPathComponent};savePrefs() }
    }
    @objc func importDocument(){
        let panel=NSOpenPanel();panel.canChooseFiles=true;panel.canChooseDirectories=false;panel.allowsMultipleSelection=false;panel.message="Выберите текстовый документ для загрузки в поле"
        panel.allowedContentTypes=["txt","md","markdown","mdown","html","htm","xhtml","docx","doc"].compactMap{UTType(filenameExtension:$0)}
        guard panel.runModal() == .OK,let url=panel.url else{return}
        do {
            let imported=try runCapture([root.appendingPathComponent("import_text.py").path,url.path])
            textInput.string=imported;textInput.setSelectedRange(NSRange(location:0,length:0));textChanged()
            if titleField.stringValue.isEmpty{titleField.stringValue=url.deletingPathExtension().lastPathComponent}
            savePrefs();window.makeFirstResponder(textInput);speechNotice.stringValue="Загружен текст из \(url.lastPathComponent)"
            status.stringValue="Текст загружен в поле. Его можно редактировать, дополнять и экспортировать."
        }catch{status.stringValue="Не удалось прочитать файл: \(error.localizedDescription)"}
    }
    @objc func pasteFromClipboard(){
        guard let text=NSPasteboard.general.string(forType:.string),!text.isEmpty else{status.stringValue="В буфере обмена нет обычного текста.";return}
        window.makeFirstResponder(textInput)
        textInput.insertText(text,replacementRange:textInput.selectedRange())
        textChanged();status.stringValue="Текст вставлен в поле. Можно продолжить редактирование."
    }
    func savePrefs(){UserDefaults.standard.set(sourceField.stringValue,forKey:"source");UserDefaults.standard.set(pagesField.stringValue,forKey:"pages");UserDefaults.standard.set(titleField.stringValue,forKey:"title");UserDefaults.standard.set(authorField.stringValue,forKey:"author");UserDefaults.standard.set(engine.indexOfSelectedItem,forKey:"engine");UserDefaults.standard.set(memory.indexOfSelectedItem,forKey:"memory");UserDefaults.standard.set(language.indexOfSelectedItem,forKey:"speechLanguage");UserDefaults.standard.set(speedSlider.doubleValue,forKey:"speechSpeed");UserDefaults.standard.set(sentencePauseSlider.doubleValue,forKey:"sentencePause");UserDefaults.standard.set(paragraphPauseSlider.doubleValue,forKey:"paragraphPause");UserDefaults.standard.set(textInput.string,forKey:"draftText");UserDefaults.standard.set(ocrLibraryField.stringValue,forKey:"ocrLibraryRoot");UserDefaults.standard.set(ttsLibraryField.stringValue,forKey:"ttsLibraryRoot")}
    func restore(){sourceField.stringValue=UserDefaults.standard.string(forKey:"source") ?? "";pagesField.stringValue=UserDefaults.standard.string(forKey:"pages") ?? "all";titleField.stringValue=UserDefaults.standard.string(forKey:"title") ?? "";authorField.stringValue=UserDefaults.standard.string(forKey:"author") ?? "";textInput.string=UserDefaults.standard.string(forKey:"draftText") ?? "";ocrLibraryField.stringValue=UserDefaults.standard.string(forKey:"ocrLibraryRoot") ?? ocrLibraryField.stringValue;ttsLibraryField.stringValue=UserDefaults.standard.string(forKey:"ttsLibraryRoot") ?? ttsLibraryField.stringValue;engine.selectItem(at:UserDefaults.standard.integer(forKey:"engine"));memory.selectItem(at:UserDefaults.standard.integer(forKey:"memory"));language.selectItem(at:UserDefaults.standard.integer(forKey:"speechLanguage"));speedSlider.doubleValue=UserDefaults.standard.object(forKey:"speechSpeed") as? Double ?? 1.0;sentencePauseSlider.doubleValue=UserDefaults.standard.object(forKey:"sentencePause") as? Double ?? 0.6;paragraphPauseSlider.doubleValue=UserDefaults.standard.object(forKey:"paragraphPause") as? Double ?? 1.8;updateVoiceOptions();speechSettingsChanged();textChanged()}
    func append(_ s:String){log.textStorage?.append(NSAttributedString(string:s));log.scrollToEndOfDocument(nil)}
    @objc func languageChanged(){updateVoiceOptions();savePrefs()}
    @objc func speechSettingsChanged(){speedValue.stringValue=String(format:"%.2f×",speedSlider.doubleValue);sentencePauseValue.stringValue=String(format:"%.1f с",sentencePauseSlider.doubleValue);paragraphPauseValue.stringValue=String(format:"%.1f с",paragraphPauseSlider.doubleValue);savePrefs()}
    func updateVoiceOptions(){
        voice.removeAllItems()
        if language.indexOfSelectedItem == 0 {
            voice.addItems(withTitles:["Женский — Бая","Женский — Ксения","Женский — Xenia","Мужской — Айдар","Мужской — Евгений"])
        } else {
            let samples=[0,12,24,48,72,96,117]
            voice.addItems(withTitles:samples.enumerated().map{"Вариант \($0.offset + 1) (en_\($0.element))"})
        }
        voice.selectItem(at:0)
    }
    @objc func textChanged(){let hasText = !textInput.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty;speakButton.isEnabled=hasText;mdButton.isEnabled=hasText || output != nil;epubButton.isEnabled=hasText || output != nil;UserDefaults.standard.set(textInput.string,forKey:"draftText")}
    func loadOCRTextIfAvailable(){
        guard !loadedOCRText,let output=output else{return}
        let md=output.appendingPathComponent("book.md")
        guard let text=try? String(contentsOf:md,encoding:.utf8),!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return}
        if textInput.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty{textInput.string=text;loadedOCRText=true;textChanged();speechNotice.stringValue="Распознанный текст загружен для озвучивания"}
    }
    @objc func speakText(){
        guard speechProcess == nil else{return}
        let text=textInput.string.trimmingCharacters(in:.whitespacesAndNewlines)
        guard !text.isEmpty else{return}
        let panel=NSSavePanel();panel.nameFieldStringValue=(titleField.stringValue.isEmpty ? "book":titleField.stringValue)+".mp3";panel.allowedContentTypes=[.mp3]
        guard panel.runModal() == .OK,let dest=panel.url else{return}
        launchSpeech(text:text,destination:dest,isPreview:false)
    }
    @objc func previewVoice(){
        guard speechProcess == nil else{return}
        let sample=language.indexOfSelectedItem==0 ? "Здравствуйте. Это пример звучания выбранного голоса. Послушайте тембр и выберите подходящий." : "Hello. This is a short sample of the selected voice. Listen to the tone and choose the one you prefer."
        let dest=FileManager.default.temporaryDirectory.appendingPathComponent("AudioLab-voice-preview-\(UUID().uuidString).mp3")
        previewOutput=dest
        launchSpeech(text:sample,destination:dest,isPreview:true)
    }
    func launchSpeech(text:String,destination dest:URL,isPreview:Bool){
        let isEnglish=language.indexOfSelectedItem==1
        let libraryRoot=URL(fileURLWithPath:ttsLibraryField.stringValue).standardizedFileURL
        let model=libraryRoot.appendingPathComponent("models/silero-tts/\(isEnglish ? "v3_en.pt":"v5_5_ru.pt")")
        let py=libraryRoot.appendingPathComponent("venv/bin/python")
        guard FileManager.default.fileExists(atPath:model.path),FileManager.default.isExecutableFile(atPath:py.path) else {
            if isPreview { previewOutput=nil }
            let alert=NSAlert();alert.messageText="Голосовая модель или Python не найдены";alert.informativeText="Проверьте выбранную папку окружения Silero и подключение диска.";alert.runModal();return
        }
        do {
            let temp=FileManager.default.temporaryDirectory.appendingPathComponent("AudioLab-TTS-\(UUID().uuidString)",isDirectory:true)
            try FileManager.default.createDirectory(at:temp,withIntermediateDirectories:true)
            let txt=temp.appendingPathComponent("text.txt");try text.write(to:txt,atomically:true,encoding:.utf8)
            let script=root.appendingPathComponent("speak_silero.py")
            let speakers=["baya","kseniya","xenia","aidar","eugene"]
            let englishSpeakers=[0,12,24,48,72,96,117]
            let selectedSpeaker=isEnglish ? "en_\(englishSpeakers[voice.indexOfSelectedItem])" : speakers[voice.indexOfSelectedItem]
            let proc=Process();proc.executableURL=py;proc.arguments=[script.path,txt.path,dest.path,model.path,selectedSpeaker,String(format:"%.2f",speedSlider.doubleValue),String(format:"%.1f",sentencePauseSlider.doubleValue),String(format:"%.1f",paragraphPauseSlider.doubleValue)]
            let channel=Pipe();proc.standardOutput=channel;proc.standardError=channel
            channel.fileHandleForReading.readabilityHandler={ [weak self] h in let data=h.availableData;if data.isEmpty{return};let s=String(decoding:data,as:UTF8.self);DispatchQueue.main.async{self?.append(s);self?.speechNotice.stringValue=String(s.split(separator:"\n").last ?? "Озвучивание…")}}
            proc.terminationHandler={ [weak self] p in DispatchQueue.main.async{guard let self=self else{return};self.speechProcess=nil;self.stopSpeechButton.isEnabled=false;self.previewVoiceButton.isEnabled=true;self.speechProgress.stopAnimation(nil);self.speakButton.isEnabled = !self.textInput.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty;if p.terminationStatus==0{self.speechNotice.stringValue=isPreview ? "Пример готов — открываю MP3" : "MP3 готов: \(dest.lastPathComponent)";self.append("MP3 сохранён: \(dest.path)\n");if isPreview{NSWorkspace.shared.open(dest)}}else{self.speechNotice.stringValue="Озвучивание остановлено или завершилось с ошибкой; подробности в журнале"};if self.previewOutput==dest{self.previewOutput=nil};try? FileManager.default.removeItem(at:temp)}}
            try proc.run();speechProcess=proc;speechProgress.startAnimation(nil);speakButton.isEnabled=false;previewVoiceButton.isEnabled=false;stopSpeechButton.isEnabled=true;speechNotice.stringValue="Загружаю модель и озвучиваю…";append("\nЗапуск Silero \(isEnglish ? "v3 English":"v5.5 Russian"), голос \(selectedSpeaker)\n")
        } catch {previewOutput=nil;previewVoiceButton.isEnabled=true;speechNotice.stringValue="Не удалось запустить озвучивание: \(error)"}
    }
    @objc func stopSpeech(){guard let p=speechProcess else{return};speechNotice.stringValue="Останавливаю озвучивание…";p.terminate()}
    func textBookDirectory() throws -> URL {
        let dir=root.appendingPathComponent("books/Вставленный-текст",isDirectory:true)
        try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
        let content=textInput.string.trimmingCharacters(in:.whitespacesAndNewlines)
        guard !content.isEmpty else{throw NSError(domain:"Вставьте текст книги или выберите книгу OCR.",code:1)}
        let md=dir.appendingPathComponent("book.md")
        try ("# \(titleField.stringValue.isEmpty ? "Текст" : titleField.stringValue)\n\n\(content)\n").write(to:md,atomically:true,encoding:.utf8)
        output=dir;return dir
    }
    @objc func start(){
        guard process==nil else{return};let raw=sourceField.stringValue
        guard !raw.isEmpty else{status.stringValue="Сначала выберите входной файл или папку.";return}
        savePrefs();let src=URL(fileURLWithPath:raw);let marker=engine.indexOfSelectedItem==0
        let key=SHA256.hash(data:Data("\(raw)|\(pagesField.stringValue)|\(engine.indexOfSelectedItem)".utf8)).map{String(format:"%02x",$0)}.joined().prefix(10)
        let base=marker ? URL(fileURLWithPath:ocrLibraryField.stringValue).appendingPathComponent("results/books") : root.appendingPathComponent("books")
        var isDirectory: ObjCBool = false
        _ = FileManager.default.fileExists(atPath: src.path, isDirectory: &isDirectory)
        let name=(isDirectory.boolValue ? src.lastPathComponent+"-images" : src.deletingPathExtension().lastPathComponent)+"-"+key
        output=base.appendingPathComponent(name)
        var input=src
        if !marker && isDirectory.boolValue {
            do { try FileManager.default.createDirectory(at:output!,withIntermediateDirectories:true);let p=try runCapture([python.path,root.appendingPathComponent("prepare_input.py").path,src.path,output!.path]);input=URL(fileURLWithPath:p.trimmingCharacters(in:.whitespacesAndNewlines)) }
            catch { status.stringValue="Подготовка изображений: \(error)";return }
        }
        let script=root.appendingPathComponent(marker ? "marker_backend.py" : "djvubook.py")
        var args=[script.path,input.path,"--output",output!.path,"--pages",pagesField.stringValue]
        if marker {args += ["--title",titleField.stringValue,"--author",authorField.stringValue,"--memory-profile",memory.indexOfSelectedItem==0 ? "economy":"parallel"]}
        else {args += ["--columns","auto"]}
        let p=Process();p.executableURL=python;p.arguments=args
        let pipe=Pipe();p.standardOutput=pipe;p.standardError=pipe
        pipe.fileHandleForReading.readabilityHandler={ [weak self] h in let d=h.availableData;if d.isEmpty{return};let s=String(decoding:d,as:UTF8.self);DispatchQueue.main.async{self?.append(s);self?.updateStatus(s)} }
        if marker {var env=ProcessInfo.processInfo.environment;env["DJVUBOOK_MARKER_ROOT"]=ocrLibraryField.stringValue;p.environment=env}
        do {try p.run();process=p;startedAt=Date();progressSamples=[];progressDone=0;progressTotal=0;startButton.isEnabled=false;stopButton.isEnabled=true;progress.doubleValue=0;status.stringValue="OCR запущен — ожидаю первую страницу";append("\nСтарт \(Date())\n");Timer.scheduledTimer(withTimeInterval:1,repeats:true){[weak self,weak p] t in guard let self=self,let p=p else{t.invalidate();return};if !p.isRunning{t.invalidate();self.finish(p)}else{self.updateClock()}}}
        catch {status.stringValue="Не удалось запустить OCR: \(error)"}
    }
    func runCapture(_ args:[String]) throws -> String {let p=Process();p.executableURL=python;p.arguments=args;let pipe=Pipe();p.standardOutput=pipe;p.standardError=pipe;try p.run();let data=pipe.fileHandleForReading.readDataToEndOfFile();p.waitUntilExit();guard p.terminationStatus==0 else{throw NSError(domain:String(decoding:data,as:UTF8.self),code:Int(p.terminationStatus))};return String(decoding:data,as:UTF8.self)}
    func updateStatus(_ s:String){let pattern="\\[(\\d+)/(\\d+)\\]";if let regex=try? NSRegularExpression(pattern:pattern){let ns=s as NSString;let matches=regex.matches(in:s,range:NSRange(location:0,length:ns.length));if let match=matches.last,let done=Int(ns.substring(with:match.range(at:1))),let total=Int(ns.substring(with:match.range(at:2))){progressDone=done;progressTotal=total;progress.maxValue=Double(max(total,1));progress.doubleValue=Double(done);status.stringValue="Сохранено страниц: \(done) из \(total)";if progressSamples.last?.1 != done{progressSamples.append((Date(),done));if progressSamples.count>20{progressSamples.removeFirst()}}}};if progressDone==0,let line=s.split(separator:"\n").last,line.contains("Marker:"){status.stringValue="Marker работает — страница ещё обрабатывается"};updateClock();if let output=output,FileManager.default.fileExists(atPath:output.appendingPathComponent("book.md").path){mdButton.isEnabled=true;epubButton.isEnabled=true;loadOCRTextIfAvailable()}}
    func updateClock(){guard let startedAt=startedAt else{return};let now=Date();let elapsed=max(0,Int(now.timeIntervalSince(startedAt)));var eta="сбор данных";if progressTotal>0,progressDone>=progressTotal{eta="00:00:00"}else if progressSamples.count>=2,let first=progressSamples.first,let last=progressSamples.last,last.1>first.1{let interval=last.0.timeIntervalSince(first.0);let pages=last.1-first.1;if interval>=5,pages>0{let secondsPerPage=interval/Double(pages);let remaining=max(0,secondsPerPage*Double(progressTotal-progressDone)-now.timeIntervalSince(last.0));eta=String(format:"≈ %02d:%02d:%02d",Int(remaining)/3600,Int(remaining)/60%60,Int(remaining)%60)}};timeLabel.stringValue=String(format:"Прошло %02d:%02d:%02d · Осталось %@ · %d/%d стр.",elapsed/3600,elapsed/60%60,elapsed%60,eta,progressDone,progressTotal)}
    func finish(_ p:Process){if process !== p{return};process=nil;startButton.isEnabled=true;stopButton.isEnabled=false;progress.stopAnimation(nil);mdButton.isEnabled=true;epubButton.isEnabled=true;status.stringValue=p.terminationStatus==0 ? "Готово: распознано страниц \(progressDone) из \(progressTotal)." : "Остановлено: сохранено \(progressDone) из \(progressTotal) страниц. Можно продолжить позже.";loadOCRTextIfAvailable()}
    @objc func stop(){status.stringValue="Останавливаю OCR после сохранения текущей страницы…";process?.interrupt()}
    func save(kind:String){let dir:URL;do{if !textInput.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty{dir=try textBookDirectory()}else if let output=output{dir=output}else{status.stringValue="Выберите книгу или вставьте текст.";return}}catch{status.stringValue="Нет текста для сохранения.";return};let panel=NSSavePanel();panel.nameFieldStringValue=(titleField.stringValue.isEmpty ? "book":titleField.stringValue)+"."+(kind=="md" ? "md":"epub");if panel.runModal() == .OK, let dest=panel.url{do{let args=[root.appendingPathComponent("export_cli.py").path,kind,dir.appendingPathComponent("book.md").path,dest.path,"--title",titleField.stringValue,"--author",authorField.stringValue];_=try runCapture(args);status.stringValue="Сохранена текущая готовая часть: \(dest.path)"}catch{status.stringValue="Экспорт не удался: \(error)"}}}
    @objc func saveMD(){save(kind:"md")};@objc func saveEPUB(){save(kind:"epub")}
}
let app=NSApplication.shared;let delegate=AudioLab();app.setActivationPolicy(.regular);app.delegate=delegate;app.run()
