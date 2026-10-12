import AppKit
import AVFoundation
import CryptoKit
import UniformTypeIdentifiers

final class AudioLab: NSObject, NSApplicationDelegate, AVAudioPlayerDelegate {
    var window: NSWindow!
    var sourceField = NSTextField(string: "")
    var textInput = NSTextView()
    var language = NSPopUpButton()
    var recognitionLanguage = NSPopUpButton()
    var speechEngine = NSPopUpButton()
    var voice = NSPopUpButton()
    var ocrLibraryField = NSTextField(string: "")
    var ttsLibraryField = NSTextField(string: "")
    var sttLibraryField = NSTextField(string: "")
    var speedSlider = NSSlider(value:1.0,minValue:0.7,maxValue:1.5,target:nil,action:nil)
    var sentencePauseSlider = NSSlider(value:0.6,minValue:0.2,maxValue:2.0,target:nil,action:nil)
    var paragraphPauseSlider = NSSlider(value:1.8,minValue:0.8,maxValue:5.0,target:nil,action:nil)
    var punctuationPauseSlider = NSSlider(value:0.25,minValue:0.05,maxValue:1.0,target:nil,action:nil)
    var numbersCheckbox = NSButton(checkboxWithTitle:"Читать числа словами",target:nil,action:nil)
    var speedValue = NSTextField(labelWithString:"1.00×")
    var sentencePauseValue = NSTextField(labelWithString:"0.6 с")
    var paragraphPauseValue = NSTextField(labelWithString:"1.8 с")
    var punctuationPauseValue = NSTextField(labelWithString:"0.25 с")
    var audioPlayer: AVAudioPlayer?
    var audioTimer: Timer?
    var audioSeekSlider = NSSlider(value:0,minValue:0,maxValue:1,target:nil,action:nil)
    var audioTimeLabel = NSTextField(labelWithString:"00:00 / 00:00")
    var playAudioButton: NSButton!
    var stopAudioButton: NSButton!
    var extractVideoButton: NSButton!
    var stopVideoExtractionButton: NSButton!
    var videoExtractionProcess: Process?
    var videoExtractionProgress = NSProgressIndicator()
    var videoExtractionNotice = NSTextField(labelWithString: "Извлекайте аудиодорожку из видео в MP3 офлайн")
    var convertFormatsButton: NSButton!
    var formatConversionProcess: Process?
    var formatConversionNotice = NSTextField(labelWithString: "PDF, DjVu, изображения, EPUB и текстовые форматы")
    var speechProgress = NSProgressIndicator()
    var speechProcess: Process?
    var transcriptionProcess: Process?
    var audioRecorder: AVAudioRecorder?
    var recordingURL: URL?
    var recordingStartedAt: Date?
    var recordingTimer: Timer?
    var recordVoiceButton: NSButton!
    var transcribeFileButton: NSButton!
    var stopTranscriptionButton: NSButton!
    var transcriptionProgress = NSProgressIndicator()
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
        let sourceActions=NSStackView();sourceActions.spacing=8
        let pick=NSButton(title:"Выбрать файл или папку…",target:self,action:#selector(choose));sourceActions.addArrangedSubview(pick)
        convertFormatsButton=NSButton(title:"Конвертировать форматы…",target:self,action:#selector(convertFileFormats));sourceActions.addArrangedSubview(convertFormatsButton);main.addArrangedSubview(sourceActions)
        sourceField.isEditable=false;sourceField.lineBreakMode = .byTruncatingMiddle;sourceField.widthAnchor.constraint(greaterThanOrEqualToConstant:700).isActive=true;main.addArrangedSubview(sourceField)
        let textActions=NSStackView();textActions.spacing=8
        let importButton=NSButton(title:"Импортировать TXT, MD, HTML или Word…",target:self,action:#selector(importDocument));textActions.addArrangedSubview(importButton)
        let pasteButton=NSButton(title:"Вставить из буфера обмена",target:self,action:#selector(pasteFromClipboard));textActions.addArrangedSubview(pasteButton);main.addArrangedSubview(textActions)
        let voiceInputRow=NSStackView();voiceInputRow.spacing=8
        recognitionLanguage.addItems(withTitles:["Речь: русский","Speech: English"]);recognitionLanguage.selectItem(at:0);recognitionLanguage.target=self;recognitionLanguage.action=#selector(recognitionLanguageChanged);voiceInputRow.addArrangedSubview(recognitionLanguage)
        recordVoiceButton=NSButton(title:"🎙 Записать речь",target:self,action:#selector(toggleVoiceRecording));voiceInputRow.addArrangedSubview(recordVoiceButton)
        transcribeFileButton=NSButton(title:"Распознать аудиофайл…",target:self,action:#selector(chooseAudioForTranscription));voiceInputRow.addArrangedSubview(transcribeFileButton)
        stopTranscriptionButton=NSButton(title:"Остановить",target:self,action:#selector(stopTranscription));stopTranscriptionButton.isEnabled=false;voiceInputRow.addArrangedSubview(stopTranscriptionButton);main.addArrangedSubview(voiceInputRow)
        transcriptionProgress.isIndeterminate=true;transcriptionProgress.isDisplayedWhenStopped=false;transcriptionProgress.widthAnchor.constraint(equalToConstant:730).isActive=true;main.addArrangedSubview(transcriptionProgress)
        let textTitle=NSTextField(labelWithString:"Текст книги — можно писать прямо в этом поле");textTitle.font=NSFont.boldSystemFont(ofSize:14);main.addArrangedSubview(textTitle)
        let textScroll=NSScrollView();textScroll.hasVerticalScroller=true;textScroll.borderType = .bezelBorder;textScroll.documentView=textInput;textInput.isEditable=true;textInput.font=NSFont.systemFont(ofSize:14);textInput.minSize=NSSize(width:0,height:120);textInput.maxSize=NSSize(width:CGFloat.greatestFiniteMagnitude,height:CGFloat.greatestFiniteMagnitude);textInput.isVerticallyResizable=true;textInput.isHorizontallyResizable=false;textInput.autoresizingMask=[.width];textScroll.heightAnchor.constraint(equalToConstant:140).isActive=true;textScroll.widthAnchor.constraint(equalToConstant:730).isActive=true
        let textMenu=NSMenu();textMenu.addItem(withTitle:"Вставить",action:#selector(NSText.paste(_:)),keyEquivalent:"v").target=nil;textMenu.addItem(withTitle:"Копировать",action:#selector(NSText.copy(_:)),keyEquivalent:"").target=nil;textMenu.addItem(withTitle:"Вырезать",action:#selector(NSText.cut(_:)),keyEquivalent:"").target=nil;textMenu.addItem(.separator());textMenu.addItem(withTitle:"Выделить всё",action:#selector(NSText.selectAll(_:)),keyEquivalent:"a").target=nil;textInput.menu=textMenu;main.addArrangedSubview(textScroll)
        engine.addItems(withTitles:["Marker — внешний диск","Tesseract — лёгкий"]);engine.selectItem(at:0)
        memory.addItems(withTitles:["Экономный — один запрос","Больше памяти — два запроса"])
        let choices=NSStackView(views:[label("OCR"),engine,label("Память"),memory]);choices.spacing=8;main.addArrangedSubview(choices)
        addDirectoryRow(title:"Окружение OCR / Marker",field:ocrLibraryField,key:"ocrLibraryRoot",fallback:"/Volumes/4TB_FILES_2025/DjVuBook-Marker",to:main)
        addDirectoryRow(title:"Окружение озвучивания / Silero",field:ttsLibraryField,key:"ttsLibraryRoot",fallback:"/Volumes/4TB_FILES_2025/DjVuBook-Marker",to:main)
        addDirectoryRow(title:"Офлайн распознавание речи / Whisper",field:sttLibraryField,key:"sttLibraryRoot",fallback:"/Volumes/4TB_FILES_2025/DjVuBook-AudioLab/speech-runtime",to:main)
        titleField.placeholderString="Название книги";authorField.placeholderString="Автор (необязательно)";pagesField.stringValue="all"
        for (name,field) in [("Название",titleField),("Автор",authorField),("Страницы",pagesField)] { let row=NSStackView(views:[label(name),field]);row.spacing=10;field.widthAnchor.constraint(equalToConstant:570).isActive=true;main.addArrangedSubview(row) }
        let buttons=NSStackView();buttons.spacing=8
        startButton=NSButton(title:"Распознать / продолжить",target:self,action:#selector(start));buttons.addArrangedSubview(startButton)
        stopButton=NSButton(title:"Остановить OCR",target:self,action:#selector(stop));stopButton.isEnabled=false;buttons.addArrangedSubview(stopButton)
        mdButton=NSButton(title:"Сохранить Markdown…",target:self,action:#selector(saveMD));mdButton.isEnabled=false;buttons.addArrangedSubview(mdButton)
        epubButton=NSButton(title:"Сохранить EPUB…",target:self,action:#selector(saveEPUB));epubButton.isEnabled=false;buttons.addArrangedSubview(epubButton)
        main.addArrangedSubview(buttons)
        let speechRow=NSStackView();speechRow.spacing=8
        let speechEngineRow=NSStackView(views:[label("Движок озвучивания"),speechEngine]);speechEngineRow.spacing=8;main.addArrangedSubview(speechEngineRow)
        language.addItems(withTitles:["Русский","English"]);language.selectItem(at:0);language.target=self;language.action=#selector(languageChanged);speechRow.addArrangedSubview(language)
        speechEngine.addItems(withTitles:["Silero — нейросетевой","Системный голос macOS"]);speechEngine.target=self;speechEngine.action=#selector(speechEngineChanged)
        updateVoiceOptions();speechRow.addArrangedSubview(voice)
        speakButton=NSButton(title:"Озвучить и сохранить аудио…",target:self,action:#selector(speakText));speakButton.isEnabled=false;speechRow.addArrangedSubview(speakButton)
        previewVoiceButton=NSButton(title:"Прослушать пример",target:self,action:#selector(previewVoice));speechRow.addArrangedSubview(previewVoiceButton)
        stopSpeechButton=NSButton(title:"Остановить озвучивание",target:self,action:#selector(stopSpeech));stopSpeechButton.isEnabled=false;speechRow.addArrangedSubview(stopSpeechButton)
        main.addArrangedSubview(speechRow)
        numbersCheckbox.target=self;numbersCheckbox.action=#selector(numberReadingChanged);numbersCheckbox.state = .on;main.addArrangedSubview(numbersCheckbox)
        speedSlider.target=self;speedSlider.action=#selector(speechSettingsChanged);speedSlider.numberOfTickMarks=17
        sentencePauseSlider.target=self;sentencePauseSlider.action=#selector(speechSettingsChanged);sentencePauseSlider.numberOfTickMarks=10
        paragraphPauseSlider.target=self;paragraphPauseSlider.action=#selector(speechSettingsChanged);paragraphPauseSlider.numberOfTickMarks=15
        punctuationPauseSlider.target=self;punctuationPauseSlider.action=#selector(speechSettingsChanged);punctuationPauseSlider.numberOfTickMarks=20
        for value in [speedValue,sentencePauseValue,paragraphPauseValue,punctuationPauseValue]{value.widthAnchor.constraint(equalToConstant:60).isActive=true}
        for (title,slider,value) in [("Скорость чтения",speedSlider,speedValue),("Пауза между предложениями",sentencePauseSlider,sentencePauseValue),("Пауза между абзацами",paragraphPauseSlider,paragraphPauseValue),("Пауза после запятых, скобок и кавычек",punctuationPauseSlider,punctuationPauseValue)] {let row=NSStackView(views:[label(title),slider,value]);row.spacing=10;slider.widthAnchor.constraint(equalToConstant:430).isActive=true;main.addArrangedSubview(row)}
        updateSpeechEngineUI()
        speechNotice.textColor = .secondaryLabelColor;main.addArrangedSubview(speechNotice)
        let voiceInfo=NSTextField(wrappingLabelWithString:"Русские голоса подписаны по полу. У английской модели только номера голосов без надёжных описаний, поэтому выберите вариант и нажмите «Прослушать пример».");voiceInfo.textColor = .secondaryLabelColor;main.addArrangedSubview(voiceInfo)
        speechProgress.isIndeterminate=true;speechProgress.isDisplayedWhenStopped=false;speechProgress.widthAnchor.constraint(equalToConstant:730).isActive=true;main.addArrangedSubview(speechProgress)
        let playerRow=NSStackView();playerRow.spacing=8
        let openAudio=NSButton(title:"Открыть аудио…",target:self,action:#selector(openAudioFile));playerRow.addArrangedSubview(openAudio)
        playAudioButton=NSButton(title:"▶ Слушать",target:self,action:#selector(toggleAudio));playAudioButton.isEnabled=false;playerRow.addArrangedSubview(playAudioButton)
        stopAudioButton=NSButton(title:"Стоп",target:self,action:#selector(stopAudio));stopAudioButton.isEnabled=false;playerRow.addArrangedSubview(stopAudioButton)
        audioSeekSlider.isEnabled=false;audioSeekSlider.target=self;audioSeekSlider.action=#selector(seekAudio);audioSeekSlider.widthAnchor.constraint(equalToConstant:300).isActive=true;playerRow.addArrangedSubview(audioSeekSlider)
        audioTimeLabel.widthAnchor.constraint(equalToConstant:100).isActive=true;playerRow.addArrangedSubview(audioTimeLabel);main.addArrangedSubview(playerRow)
        let videoRow=NSStackView();videoRow.spacing=8
        extractVideoButton=NSButton(title:"Извлечь MP3 из видео…",target:self,action:#selector(extractAudioFromVideo));videoRow.addArrangedSubview(extractVideoButton)
        stopVideoExtractionButton=NSButton(title:"Остановить конвертацию",target:self,action:#selector(stopVideoExtraction));stopVideoExtractionButton.isEnabled=false;videoRow.addArrangedSubview(stopVideoExtractionButton)
        videoExtractionProgress.isIndeterminate=true;videoExtractionProgress.isDisplayedWhenStopped=false;videoExtractionProgress.widthAnchor.constraint(equalToConstant:180).isActive=true;videoRow.addArrangedSubview(videoExtractionProgress);main.addArrangedSubview(videoRow)
        videoExtractionNotice.textColor = .secondaryLabelColor;main.addArrangedSubview(videoExtractionNotice)
        formatConversionNotice.textColor = .secondaryLabelColor;main.addArrangedSubview(formatConversionNotice)
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
            if key=="ocrLibraryRoot"{ocrLibraryField.stringValue=url.path}else if key=="ttsLibraryRoot"{ttsLibraryField.stringValue=url.path}else{sttLibraryField.stringValue=url.path}
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
    @objc func recognitionLanguageChanged(){savePrefs()}
    @objc func toggleVoiceRecording(){
        if let recorder=audioRecorder,recorder.isRecording{
            recorder.stop();audioRecorder=nil;recordingTimer?.invalidate();recordingTimer=nil;recordingStartedAt=nil
            transcriptionProgress.stopAnimation(nil);stopTranscriptionButton.isEnabled=false;stopTranscriptionButton.title="Остановить";speechNotice.textColor = .secondaryLabelColor
            recordVoiceButton.title="🎙 Записать речь";recordVoiceButton.isEnabled=false;transcribeFileButton.isEnabled=true
            guard let url=recordingURL else{recordVoiceButton.isEnabled=true;return}
            speechNotice.textColor = .secondaryLabelColor;speechNotice.stringValue="Запись завершена; начинаю распознавание офлайн…";transcribeAudio(url,deleteAfter:true);return
        }
        let authorization=AVCaptureDevice.authorizationStatus(for:.audio)
        if authorization == .authorized{beginVoiceRecording()}
        else if authorization == .notDetermined{
            recordVoiceButton.isEnabled=false;speechNotice.stringValue="Запрашиваю доступ к микрофону…"
            AVCaptureDevice.requestAccess(for:.audio){[weak self] granted in DispatchQueue.main.async{guard let self=self else{return};if granted{self.beginVoiceRecording()}else{self.recordVoiceButton.isEnabled=true;self.speechNotice.stringValue="Разрешите доступ к микрофону в системных настройках macOS."}}}
        }else{speechNotice.stringValue="Разрешите доступ к микрофону в системных настройках macOS."}
    }
    func beginVoiceRecording(){
        recordVoiceButton.isEnabled=true
        let whisper=URL(fileURLWithPath:sttLibraryField.stringValue).appendingPathComponent("bin/whisper-cli")
        let model=URL(fileURLWithPath:sttLibraryField.stringValue).appendingPathComponent("models/ggml-small-q5_1.bin")
        guard FileManager.default.isExecutableFile(atPath:whisper.path),FileManager.default.fileExists(atPath:model.path) else{speechNotice.stringValue="Сначала установите Whisper на внешний диск.";let alert=NSAlert();alert.messageText="Whisper ещё не установлен";alert.informativeText="Для офлайн-распознавания нужны whisper-cli и модель ggml-small-q5_1.bin (~190 МБ).";alert.runModal();return}
        let url=FileManager.default.temporaryDirectory.appendingPathComponent("AudioLab-voice-\(UUID().uuidString).m4a")
        let settings:[String:Any]=[AVFormatIDKey:kAudioFormatMPEG4AAC,AVSampleRateKey:44100,AVNumberOfChannelsKey:1,AVEncoderBitRateKey:96000,AVEncoderAudioQualityKey:AVAudioQuality.high.rawValue]
        do{
            let recorder=try AVAudioRecorder(url:url,settings:settings);guard recorder.record() else{throw NSError(domain:"Не удалось начать запись с микрофона.",code:1)}
            audioRecorder=recorder;recordingURL=url;recordingStartedAt=Date();recordVoiceButton.isEnabled=true;recordVoiceButton.title="■ Завершить и распознать";speechNotice.textColor = .systemRed
            transcribeFileButton.isEnabled=false;stopTranscriptionButton.title="Отменить запись";stopTranscriptionButton.isEnabled=true;transcriptionProgress.startAnimation(nil);updateRecordingStatus()
            recordingTimer=Timer.scheduledTimer(withTimeInterval:1,repeats:true){[weak self] _ in self?.updateRecordingStatus()}
        }
        catch{recordVoiceButton.isEnabled=true;speechNotice.stringValue="Не удалось записать звук: \(error.localizedDescription)"}
    }
    func updateRecordingStatus(){
        guard let started=recordingStartedAt,audioRecorder?.isRecording == true else{return}
        let seconds=max(0,Int(Date().timeIntervalSince(started)));speechNotice.stringValue=String(format:"● ИДЁТ ЗАПИСЬ · %02d:%02d · нажмите «Завершить и распознать»",seconds/60,seconds%60)
    }
    @objc func chooseAudioForTranscription(){
        let panel=NSOpenPanel();panel.canChooseFiles=true;panel.canChooseDirectories=false;panel.allowsMultipleSelection=false;panel.allowedContentTypes=[.mp3,.aiff,.wav,.mpeg4Audio];panel.message="Выберите запись речи. Она будет распознана на Mac без отправки в интернет."
        if panel.runModal() == .OK,let url=panel.url{transcribeAudio(url)}
    }
    func transcribeAudio(_ audioURL:URL,deleteAfter:Bool=false){
        guard transcriptionProcess==nil else{return}
        let library=URL(fileURLWithPath:sttLibraryField.stringValue).standardizedFileURL
        let whisper=library.appendingPathComponent("bin/whisper-cli")
        let model=library.appendingPathComponent("models/ggml-small-q5_1.bin")
        guard FileManager.default.isExecutableFile(atPath:whisper.path),FileManager.default.fileExists(atPath:model.path) else{
            recordVoiceButton.isEnabled=true;transcribeFileButton.isEnabled=true;stopTranscriptionButton.isEnabled=false;transcriptionProgress.stopAnimation(nil)
            let alert=NSAlert();alert.messageText="Whisper ещё не установлен";alert.informativeText="Подключите диск 4TB_FILES_2025 или выберите папку Whisper. Для офлайн-распознавания нужны whisper-cli и модель ggml-small-q5_1.bin (~190 МБ).";alert.runModal();return
        }
        do{
            let temp=FileManager.default.temporaryDirectory.appendingPathComponent("AudioLab-STT-\(UUID().uuidString)",isDirectory:true);try FileManager.default.createDirectory(at:temp,withIntermediateDirectories:true)
            let transcript=temp.appendingPathComponent("transcript.txt"),script=root.appendingPathComponent("transcribe_whisper.py")
            let audioPython=URL(fileURLWithPath:ttsLibraryField.stringValue).appendingPathComponent("venv/bin/python")
            guard FileManager.default.isExecutableFile(atPath:audioPython.path) else{throw NSError(domain:"Не найден Python из выбранного окружения Marker/Silero. Он нужен для конвертации формата аудио.",code:1)}
            let process=Process();process.executableURL=audioPython;process.arguments=[script.path,audioURL.path,transcript.path,model.path,whisper.path,recognitionLanguage.indexOfSelectedItem==0 ? "ru":"en"]
            var environment=ProcessInfo.processInfo.environment;let libraryPath=library.appendingPathComponent("lib").path;environment["DYLD_LIBRARY_PATH"]=libraryPath+(environment["DYLD_LIBRARY_PATH"].map{":"+$0} ?? "");process.environment=environment
            let pipe=Pipe();process.standardOutput=pipe;process.standardError=pipe
            pipe.fileHandleForReading.readabilityHandler={[weak self] handle in let data=handle.availableData;if !data.isEmpty{let message=String(decoding:data,as:UTF8.self);DispatchQueue.main.async{self?.append(message);self?.speechNotice.stringValue=String(message.split(separator:"\n").last ?? "Распознаю речь…")}}}
            process.terminationHandler={[weak self] finished in DispatchQueue.main.async{guard let self=self else{return};self.transcriptionProcess=nil;self.transcriptionProgress.stopAnimation(nil);self.stopTranscriptionButton.isEnabled=false;self.stopTranscriptionButton.title="Остановить";self.recordVoiceButton.isEnabled=true;self.transcribeFileButton.isEnabled=true;if finished.terminationStatus==0,let transcript=try? String(contentsOf:transcript,encoding:.utf8),!transcript.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty{let result=transcript.trimmingCharacters(in:.whitespacesAndNewlines);let selected=self.textInput.selectedRange();let insertion=(selected.location==self.textInput.string.utf16.count && !self.textInput.string.isEmpty ? "\n\n":"")+result;self.textInput.insertText(insertion,replacementRange:selected);self.textChanged();self.speechNotice.stringValue="Речь распознана и добавлена в поле текста";self.window.makeFirstResponder(self.textInput)}else{self.speechNotice.stringValue="Не удалось распознать запись; подробности есть в журнале."};try? FileManager.default.removeItem(at:temp);if deleteAfter{try? FileManager.default.removeItem(at:audioURL)}}}
            try process.run();transcriptionProcess=process;recordVoiceButton.isEnabled=false;transcribeFileButton.isEnabled=false;stopTranscriptionButton.title="Остановить распознавание";stopTranscriptionButton.isEnabled=true;transcriptionProgress.startAnimation(nil);speechNotice.textColor = .secondaryLabelColor;speechNotice.stringValue="Распознаю речь локально на Mac…";append("\nWhisper: файл \(audioURL.lastPathComponent), язык \(recognitionLanguage.indexOfSelectedItem==0 ? "русский":"английский")\n")
        }catch{recordVoiceButton.isEnabled=true;transcribeFileButton.isEnabled=true;stopTranscriptionButton.isEnabled=false;transcriptionProgress.stopAnimation(nil);speechNotice.stringValue="Не удалось запустить распознавание: \(error.localizedDescription)"}
    }
    @objc func stopTranscription(){
        if let recorder=audioRecorder,recorder.isRecording{
            recorder.stop();audioRecorder=nil;recordingTimer?.invalidate();recordingTimer=nil;recordingStartedAt=nil
            if let url=recordingURL{try? FileManager.default.removeItem(at:url)};recordingURL=nil
            transcriptionProgress.stopAnimation(nil);recordVoiceButton.title="🎙 Записать речь";recordVoiceButton.isEnabled=true;transcribeFileButton.isEnabled=true;stopTranscriptionButton.title="Остановить";stopTranscriptionButton.isEnabled=false;speechNotice.textColor = .secondaryLabelColor;speechNotice.stringValue="Запись отменена; аудиофайл удалён."
        }else{transcriptionProcess?.terminate()}
    }
    func savePrefs(){UserDefaults.standard.set(sourceField.stringValue,forKey:"source");UserDefaults.standard.set(pagesField.stringValue,forKey:"pages");UserDefaults.standard.set(titleField.stringValue,forKey:"title");UserDefaults.standard.set(authorField.stringValue,forKey:"author");UserDefaults.standard.set(engine.indexOfSelectedItem,forKey:"engine");UserDefaults.standard.set(memory.indexOfSelectedItem,forKey:"memory");UserDefaults.standard.set(language.indexOfSelectedItem,forKey:"speechLanguage");UserDefaults.standard.set(recognitionLanguage.indexOfSelectedItem,forKey:"recognitionLanguage");UserDefaults.standard.set(speechEngine.indexOfSelectedItem,forKey:"speechEngine");UserDefaults.standard.set(numbersCheckbox.state == .on,forKey:"readNumbers");UserDefaults.standard.set(speedSlider.doubleValue,forKey:"speechSpeed");UserDefaults.standard.set(sentencePauseSlider.doubleValue,forKey:"sentencePause");UserDefaults.standard.set(paragraphPauseSlider.doubleValue,forKey:"paragraphPause");UserDefaults.standard.set(punctuationPauseSlider.doubleValue,forKey:"punctuationPause");UserDefaults.standard.set(textInput.string,forKey:"draftText");UserDefaults.standard.set(ocrLibraryField.stringValue,forKey:"ocrLibraryRoot");UserDefaults.standard.set(ttsLibraryField.stringValue,forKey:"ttsLibraryRoot");UserDefaults.standard.set(sttLibraryField.stringValue,forKey:"sttLibraryRoot")}
    func restore(){sourceField.stringValue=UserDefaults.standard.string(forKey:"source") ?? "";pagesField.stringValue=UserDefaults.standard.string(forKey:"pages") ?? "all";titleField.stringValue=UserDefaults.standard.string(forKey:"title") ?? "";authorField.stringValue=UserDefaults.standard.string(forKey:"author") ?? "";textInput.string=UserDefaults.standard.string(forKey:"draftText") ?? "";ocrLibraryField.stringValue=UserDefaults.standard.string(forKey:"ocrLibraryRoot") ?? ocrLibraryField.stringValue;ttsLibraryField.stringValue=UserDefaults.standard.string(forKey:"ttsLibraryRoot") ?? ttsLibraryField.stringValue;sttLibraryField.stringValue=UserDefaults.standard.string(forKey:"sttLibraryRoot") ?? sttLibraryField.stringValue;engine.selectItem(at:UserDefaults.standard.integer(forKey:"engine"));memory.selectItem(at:UserDefaults.standard.integer(forKey:"memory"));language.selectItem(at:UserDefaults.standard.integer(forKey:"speechLanguage"));recognitionLanguage.selectItem(at:UserDefaults.standard.integer(forKey:"recognitionLanguage"));speechEngine.selectItem(at:UserDefaults.standard.integer(forKey:"speechEngine"));numbersCheckbox.state=(UserDefaults.standard.object(forKey:"readNumbers") as? Bool ?? true) ? .on:.off;speedSlider.doubleValue=UserDefaults.standard.object(forKey:"speechSpeed") as? Double ?? 1.0;sentencePauseSlider.doubleValue=UserDefaults.standard.object(forKey:"sentencePause") as? Double ?? 0.6;paragraphPauseSlider.doubleValue=UserDefaults.standard.object(forKey:"paragraphPause") as? Double ?? 1.8;punctuationPauseSlider.doubleValue=UserDefaults.standard.object(forKey:"punctuationPause") as? Double ?? 0.25;updateVoiceOptions();speechSettingsChanged();updateSpeechEngineUI();textChanged()}
    func append(_ s:String){log.textStorage?.append(NSAttributedString(string:s));log.scrollToEndOfDocument(nil)}
    @objc func languageChanged(){updateVoiceOptions();savePrefs()}
    @objc func speechEngineChanged(){updateVoiceOptions();updateSpeechEngineUI();savePrefs()}
    @objc func numberReadingChanged(){savePrefs()}
    func updateSpeechEngineUI(){let isSystem=speechEngine.indexOfSelectedItem==1;language.isEnabled=true;voice.isEnabled=true;previewVoiceButton.isEnabled=speechProcess == nil;for slider in [speedSlider,sentencePauseSlider,paragraphPauseSlider,punctuationPauseSlider]{slider.isEnabled = !isSystem};if isSystem{speechNotice.stringValue="Системный голос macOS; в списке показаны установленные голоса выбранного языка."}else{speechNotice.stringValue="Офлайн-голос Silero"}}
    func installedSystemVoices()->[(name:String,locale:String)]{let process=Process();process.executableURL=URL(fileURLWithPath:"/usr/bin/say");process.arguments=["-v","?"];let pipe=Pipe();process.standardOutput=pipe;process.standardError=FileHandle.nullDevice;do{try process.run();let data=pipe.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit();let text=String(decoding:data,as:UTF8.self);let pattern=try NSRegularExpression(pattern:"^(.+?)\\s+([a-z]{2}_[A-Z]{2})\\s+#",options:.anchorsMatchLines);let ns=text as NSString;return pattern.matches(in:text,range:NSRange(location:0,length:ns.length)).compactMap{m in guard m.numberOfRanges>2 else{return nil};return(ns.substring(with:m.range(at:1)).trimmingCharacters(in:.whitespaces),ns.substring(with:m.range(at:2)))}}catch{return []}}
    @objc func speechSettingsChanged(){speedValue.stringValue=String(format:"%.2f×",speedSlider.doubleValue);sentencePauseValue.stringValue=String(format:"%.1f с",sentencePauseSlider.doubleValue);paragraphPauseValue.stringValue=String(format:"%.1f с",paragraphPauseSlider.doubleValue);punctuationPauseValue.stringValue=String(format:"%.2f с",punctuationPauseSlider.doubleValue);savePrefs()}
    func updateVoiceOptions(){
        voice.removeAllItems()
        if speechEngine.indexOfSelectedItem == 1 {
            let prefix=language.indexOfSelectedItem==0 ? "ru_":"en_";let voices=installedSystemVoices().filter{$0.locale.hasPrefix(prefix)}
            voice.addItems(withTitles:voices.map{$0.name+" (\($0.locale))"})
            let preferred=language.indexOfSelectedItem==0 ? "Milena":"Samantha";voice.selectItem(at:max(0,voices.firstIndex(where:{$0.name==preferred}) ?? 0))
        } else if language.indexOfSelectedItem == 0 {
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
        let panel=NSSavePanel();panel.nameFieldStringValue=(titleField.stringValue.isEmpty ? "book":titleField.stringValue)+(speechEngine.indexOfSelectedItem==1 ? ".aiff":".mp3");panel.allowedContentTypes=speechEngine.indexOfSelectedItem==1 ? [UTType(filenameExtension:"aiff") ?? .audio] : [.mp3]
        guard panel.runModal() == .OK,let dest=panel.url else{return}
        launchSpeech(text:text,destination:dest,isPreview:false)
    }
    @objc func previewVoice(){
        guard speechProcess == nil else{return}
        let sample=language.indexOfSelectedItem==0 ? "Здравствуйте. Это пример звучания выбранного голоса. Послушайте тембр и выберите подходящий." : "Hello. This is a short sample of the selected voice. Listen to the tone and choose the one you prefer."
        let dest=FileManager.default.temporaryDirectory.appendingPathComponent("AudioLab-voice-preview-\(UUID().uuidString)"+(speechEngine.indexOfSelectedItem==1 ? ".aiff":".mp3"))
        previewOutput=dest
        launchSpeech(text:sample,destination:dest,isPreview:true)
    }
    func launchSpeech(text:String,destination dest:URL,isPreview:Bool){
        if speechEngine.indexOfSelectedItem==1{launchMacSpeech(text:text,destination:dest,isPreview:isPreview);return}
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
            let proc=Process();proc.executableURL=py;proc.arguments=[script.path,txt.path,dest.path,model.path,selectedSpeaker,String(format:"%.2f",speedSlider.doubleValue),String(format:"%.1f",sentencePauseSlider.doubleValue),String(format:"%.1f",paragraphPauseSlider.doubleValue),String(format:"%.2f",punctuationPauseSlider.doubleValue),numbersCheckbox.state == .on ? "1":"0"]
            let channel=Pipe();proc.standardOutput=channel;proc.standardError=channel
            channel.fileHandleForReading.readabilityHandler={ [weak self] h in let data=h.availableData;if data.isEmpty{return};let s=String(decoding:data,as:UTF8.self);DispatchQueue.main.async{self?.append(s);self?.speechNotice.stringValue=String(s.split(separator:"\n").last ?? "Озвучивание…")}}
            proc.terminationHandler={ [weak self] p in DispatchQueue.main.async{guard let self=self else{return};self.speechProcess=nil;self.stopSpeechButton.isEnabled=false;self.previewVoiceButton.isEnabled=true;self.speechProgress.stopAnimation(nil);self.speakButton.isEnabled = !self.textInput.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty;if p.terminationStatus==0{self.speechNotice.stringValue=isPreview ? "Пример голоса готов" : "MP3 готов: \(dest.lastPathComponent)";self.append("MP3 сохранён: \(dest.path)\n");self.loadAudio(dest,autoplay:isPreview)}else{self.speechNotice.stringValue="Озвучивание остановлено или завершилось с ошибкой; подробности в журнале"};if self.previewOutput==dest{self.previewOutput=nil};try? FileManager.default.removeItem(at:temp)}}
            try proc.run();speechProcess=proc;speechProgress.startAnimation(nil);speakButton.isEnabled=false;previewVoiceButton.isEnabled=false;stopSpeechButton.isEnabled=true;speechNotice.stringValue="Загружаю модель и озвучиваю…";append("\nЗапуск Silero \(isEnglish ? "v3 English":"v5.5 Russian"), голос \(selectedSpeaker)\n")
        } catch {previewOutput=nil;previewVoiceButton.isEnabled=true;speechNotice.stringValue="Не удалось запустить озвучивание: \(error)"}
    }
    func launchMacSpeech(text:String,destination dest:URL,isPreview:Bool){
        guard speechProcess == nil else{return}
        let temp=FileManager.default.temporaryDirectory.appendingPathComponent("AudioLab-macOS-TTS-\(UUID().uuidString)",isDirectory:true)
        do{
            try FileManager.default.createDirectory(at:temp,withIntermediateDirectories:true)
            let textFile=temp.appendingPathComponent("text.txt");try text.write(to:textFile,atomically:true,encoding:.utf8)
            _ = try runCapture([python.path,root.appendingPathComponent("speech_text.py").path,"normalize",textFile.path,textFile.path,language.indexOfSelectedItem==0 ? "ru":"en",numbersCheckbox.state == .on ? "1":"0"])
            let available=installedSystemVoices().filter{$0.locale.hasPrefix(language.indexOfSelectedItem==0 ? "ru_":"en_")};let voiceName=available.dropFirst(max(0,voice.indexOfSelectedItem)).first?.name ?? (language.indexOfSelectedItem==0 ? "Milena":"Samantha")
            let proc=Process();proc.executableURL=URL(fileURLWithPath:"/usr/bin/say");proc.arguments=["-v",voiceName,"-r",String(Int(180*speedSlider.doubleValue)),"-o",dest.path,"-f",textFile.path]
            let pipe=Pipe();proc.standardOutput=pipe;proc.standardError=pipe
            pipe.fileHandleForReading.readabilityHandler={[weak self] h in let data=h.availableData;if !data.isEmpty{let s=String(decoding:data,as:UTF8.self);DispatchQueue.main.async{self?.append(s)}}}
            proc.terminationHandler={[weak self] p in DispatchQueue.main.async{guard let self=self else{return};self.speechProcess=nil;self.stopSpeechButton.isEnabled=false;self.previewVoiceButton.isEnabled=true;self.speechProgress.stopAnimation(nil);self.speakButton.isEnabled = !self.textInput.string.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty;if p.terminationStatus==0{self.speechNotice.stringValue=isPreview ? "Пример системного голоса готов" : "Аудио готово: \(dest.lastPathComponent)";self.append("Системная озвучка сохранена: \(dest.path)\n");self.loadAudio(dest,autoplay:isPreview)}else{self.speechNotice.stringValue="Системная озвучка завершилась с ошибкой"};if self.previewOutput==dest{self.previewOutput=nil};try? FileManager.default.removeItem(at:temp)}}
            try proc.run();speechProcess=proc;speechProgress.startAnimation(nil);speakButton.isEnabled=false;previewVoiceButton.isEnabled=false;stopSpeechButton.isEnabled=true;speechNotice.stringValue="Озвучиваю встроенным голосом macOS…";append("\nЗапуск системного голоса macOS (\(voiceName))\n")
        }catch{if isPreview{previewOutput=nil};previewVoiceButton.isEnabled=true;speechNotice.stringValue="Не удалось запустить системное озвучивание: \(error.localizedDescription)"}
    }
    @objc func stopSpeech(){guard let p=speechProcess else{return};speechNotice.stringValue="Останавливаю озвучивание…";p.terminate()}
    func loadAudio(_ url:URL,autoplay:Bool=false){
        do{
            stopAudio()
            let player=try AVAudioPlayer(contentsOf:url)
            player.delegate=self;player.prepareToPlay();audioPlayer=player
            audioSeekSlider.minValue=0;audioSeekSlider.maxValue=max(player.duration,1);audioSeekSlider.doubleValue=0;audioSeekSlider.isEnabled=true
            audioTimeLabel.stringValue="00:00 / \(clockString(player.duration))"
            playAudioButton.isEnabled=true;stopAudioButton.isEnabled=true
            if autoplay{toggleAudio()}
        }catch{speechNotice.stringValue="Не удалось открыть MP3: \(error.localizedDescription)"}
    }
    func clockString(_ seconds:TimeInterval)->String{let value=max(0,Int(seconds));return String(format:"%02d:%02d",value/60,value%60)}
    @objc func openAudioFile(){
        let panel=NSOpenPanel();panel.canChooseFiles=true;panel.canChooseDirectories=false;panel.allowsMultipleSelection=false;panel.allowedContentTypes=[.mp3,.aiff,.wav,.mpeg4Audio];panel.message="Выберите MP3, AIFF, WAV или M4A для прослушивания"
        if panel.runModal() == .OK,let url=panel.url{loadAudio(url);speechNotice.stringValue="Готово к прослушиванию: \(url.lastPathComponent)"}
    }
    @objc func convertFileFormats(){
        guard formatConversionProcess == nil else{formatConversionNotice.stringValue="Дождитесь завершения текущей конвертации или остановите её.";return}
        let sourcePanel=NSOpenPanel();sourcePanel.canChooseFiles=true;sourcePanel.canChooseDirectories=true;sourcePanel.allowsMultipleSelection=true;sourcePanel.message="Выберите документ, одно или несколько изображений либо папку с изображениями"
        guard sourcePanel.runModal() == .OK,!sourcePanel.urls.isEmpty else{return}
        let sources=sourcePanel.urls
        let ext=sources.first?.pathExtension.lowercased() ?? ""
        let isImageSet=sources.first?.hasDirectoryPath == true || ["jpg","jpeg","png","heic","tif","tiff","bmp","webp"].contains(ext)
        let isEpub=ext=="epub",isText=["txt","md","markdown","mdown","html","htm","xhtml","docx","doc"].contains(ext)
        let formats:[(String,String)]
        if isImageSet{formats=[("PDF","pdf"),("DjVu — со сжатием страниц","djvu"),("EPUB — книга из страниц-изображений","epub"),("PNG — страницы","png"),("JPEG — страницы","jpg")]}
        else if isEpub{formats=[("TXT — текст глав","txt"),("Markdown — текст глав","md"),("PDF — простой текстовый документ","pdf")]}
        else if isText{formats=[("TXT — простой текст","txt"),("Markdown","md"),("PDF — простой текстовый документ","pdf"),("EPUB — электронная книга","epub")]}
        else if ["pdf","djvu","djv"].contains(ext){formats=[("PDF","pdf"),("DjVu — растрированные страницы","djvu"),("PNG — страницы","png"),("JPEG — страницы","jpg"),("TXT — текстовый слой","txt"),("Markdown — текстовый слой","md"),("EPUB — из текстового слоя","epub")]}
        else{formatConversionNotice.stringValue="Формат \(ext.uppercased()) не поддерживается.";return}
        let popup=NSPopUpButton(frame:NSRect(x:0,y:0,width:330,height:28),pullsDown:false)
        popup.addItems(withTitles:formats.map{$0.0})
        let accessory=NSStackView(views:[label("Формат результата"),popup]);accessory.spacing=10
        let alert=NSAlert();alert.messageText="Преобразовать выбранное";alert.informativeText="Все операции выполняются локально. PDF → DjVu и PDF/DjVu → картинки растрируют страницы. Извлечение текста из скана требует предварительного OCR.";alert.accessoryView=accessory;alert.addButton(withTitle:"Продолжить");alert.addButton(withTitle:"Отмена")
        guard alert.runModal() == .alertFirstButtonReturn else{return}
        let target=formats[popup.indexOfSelectedItem].1
        var destination:URL
        if target=="png" || target=="jpg"{
            let folderPanel=NSOpenPanel();folderPanel.canChooseFiles=false;folderPanel.canChooseDirectories=true;folderPanel.canCreateDirectories=true;folderPanel.message="Выберите папку, в которой создать отдельную папку с изображениями"
            guard folderPanel.runModal() == .OK,let parent=folderPanel.url else{return}
            let base=sources.first!.hasDirectoryPath ? sources.first!.lastPathComponent : sources.first!.deletingPathExtension().lastPathComponent
            destination=parent.appendingPathComponent(base+"-"+target.uppercased(),isDirectory:true)
        }else{
            let save=NSSavePanel();save.nameFieldStringValue=(sources.first!.hasDirectoryPath ? sources.first!.lastPathComponent : sources.first!.deletingPathExtension().lastPathComponent)+"."+target
            save.allowedContentTypes=UTType(filenameExtension:target).map{[$0]} ?? [.data];save.message="Сохранить преобразованный файл"
            guard save.runModal() == .OK,let url=save.url else{return};destination=url
        }
        let library=URL(fileURLWithPath:ttsLibraryField.stringValue).appendingPathComponent("venv/bin/python")
        let fallback=URL(fileURLWithPath:ocrLibraryField.stringValue).appendingPathComponent("venv/bin/python")
        let interpreter=[library,fallback,python,URL(fileURLWithPath:"/opt/homebrew/bin/python3"),URL(fileURLWithPath:"/usr/bin/python3")].first{FileManager.default.isExecutableFile(atPath:$0.path)}
        let script=root.appendingPathComponent("format_converter.py")
        guard let interpreter=interpreter,FileManager.default.isReadableFile(atPath:script.path) else{formatConversionNotice.stringValue="Не найден Python или format_converter.py рядом с приложением.";return}
        let process=Process();process.executableURL=interpreter;process.arguments=[script.path,"--target",target,"--output",destination.path,"--title",titleField.stringValue]+sources.map{$0.path}
        let pipe=Pipe();process.standardOutput=pipe;process.standardError=pipe
        pipe.fileHandleForReading.readabilityHandler={[weak self] handle in
            let data=handle.availableData;guard !data.isEmpty else{return};let message=String(decoding:data,as:UTF8.self)
            DispatchQueue.main.async{guard let self=self else{return};self.append(message);if let last=message.split(separator:"\n").last{self.formatConversionNotice.stringValue=String(last)}}
        }
        process.terminationHandler={[weak self] finished in DispatchQueue.main.async{
            guard let self=self else{return};self.formatConversionProcess=nil;pipe.fileHandleForReading.readabilityHandler=nil
            if finished.terminationStatus==0{self.formatConversionNotice.stringValue="Готово: \(destination.path)";self.status.stringValue="Файл преобразован: \(destination.lastPathComponent)";self.append("Конвертация завершена: \(destination.path)\n")}
            else{self.formatConversionNotice.stringValue="Не удалось выполнить конвертацию. Подробности добавлены в журнал.";self.append("Конвертация завершилась с ошибкой (код \(finished.terminationStatus)).\n")}
        }}
        do{try process.run();formatConversionProcess=process;formatConversionNotice.stringValue="Преобразую локально…";append("\nКонвертация \(sources.map{$0.lastPathComponent}.joined(separator:", ")) → \(target.uppercased())\n")}
        catch{formatConversionNotice.stringValue="Не удалось запустить конвертацию: \(error.localizedDescription)"}
    }
    @objc func extractAudioFromVideo(){
        guard videoExtractionProcess == nil else{return}
        let sourcePanel=NSOpenPanel();sourcePanel.canChooseFiles=true;sourcePanel.canChooseDirectories=false;sourcePanel.allowsMultipleSelection=false
        sourcePanel.allowedContentTypes=["mp4","mov","m4v","mkv","avi","webm","mpeg","mpg","mts","m2ts","3gp"].compactMap{UTType(filenameExtension:$0)}
        sourcePanel.message="Выберите видеофайл. Аудио будет извлечено локально в MP3."
        guard sourcePanel.runModal() == .OK,let source=sourcePanel.url else{return}
        let savePanel=NSSavePanel();savePanel.allowedContentTypes=[.mp3];savePanel.nameFieldStringValue=source.deletingPathExtension().lastPathComponent+"-audio.mp3";savePanel.message="Сохранить извлечённый звук как MP3"
        guard savePanel.runModal() == .OK,let destination=savePanel.url else{return}
        let python=URL(fileURLWithPath:ttsLibraryField.stringValue).appendingPathComponent("venv/bin/python")
        let script=root.appendingPathComponent("extract_video_audio.py")
        guard FileManager.default.isExecutableFile(atPath:python.path),FileManager.default.isReadableFile(atPath:script.path) else{videoExtractionNotice.stringValue="Не найден Python из выбранного окружения Silero/Marker или скрипт конвертации.";return}
        let process=Process();process.executableURL=python;process.arguments=[script.path,source.path,destination.path]
        let pipe=Pipe();process.standardOutput=pipe;process.standardError=pipe
        pipe.fileHandleForReading.readabilityHandler={[weak self] handle in
            let data=handle.availableData;guard !data.isEmpty else{return};let message=String(decoding:data,as:UTF8.self)
            DispatchQueue.main.async{
                guard let self=self else{return};self.append(message)
                if let line=message.split(separator:"\n").last, line.hasPrefix("out_time="){
                    self.videoExtractionNotice.stringValue="Извлекаю звук · \(line.dropFirst("out_time=".count).split(separator:".").first ?? "")"
                }
            }
        }
        process.terminationHandler={[weak self] finished in DispatchQueue.main.async{
            guard let self=self else{return};self.videoExtractionProcess=nil;self.videoExtractionProgress.stopAnimation(nil);self.extractVideoButton.isEnabled=true;self.stopVideoExtractionButton.isEnabled=false
            if finished.terminationStatus == 0,FileManager.default.fileExists(atPath:destination.path){
                self.videoExtractionNotice.stringValue="Готово: \(destination.lastPathComponent) — открываю в плеере";self.append("Аудио из видео сохранено: \(destination.path)\n");self.loadAudio(destination)
            }else{
                try? FileManager.default.removeItem(at:destination);self.videoExtractionNotice.stringValue="Конвертация остановлена или не удалась; подробности есть в журнале."
            }
        }}
        do{
            try process.run();videoExtractionProcess=process;extractVideoButton.isEnabled=false;stopVideoExtractionButton.isEnabled=true;videoExtractionProgress.startAnimation(nil);videoExtractionNotice.stringValue="Извлекаю аудиодорожку локально…";append("\nВидео → MP3: \(source.lastPathComponent)\n")
        }catch{extractVideoButton.isEnabled=true;stopVideoExtractionButton.isEnabled=false;videoExtractionProgress.stopAnimation(nil);videoExtractionNotice.stringValue="Не удалось запустить конвертацию: \(error.localizedDescription)"}
    }
    @objc func stopVideoExtraction(){videoExtractionNotice.stringValue="Останавливаю и удаляю незавершённый MP3…";videoExtractionProcess?.terminate()}
    @objc func toggleAudio(){
        guard let player=audioPlayer else{return}
        if player.isPlaying{player.pause();playAudioButton.title="▶ Продолжить";audioTimer?.invalidate();audioTimer=nil}
        else{if player.currentTime>=player.duration{player.currentTime=0};player.play();playAudioButton.title="⏸ Пауза";audioTimer?.invalidate();audioTimer=Timer.scheduledTimer(withTimeInterval:0.25,repeats:true){[weak self,weak player] timer in guard let self=self,let player=player else{timer.invalidate();return};self.audioSeekSlider.doubleValue=player.currentTime;self.audioTimeLabel.stringValue="\(self.clockString(player.currentTime)) / \(self.clockString(player.duration))";if !player.isPlaying{timer.invalidate();self.audioTimer=nil;self.playAudioButton.title="▶ Слушать"}}}
    }
    @objc func stopAudio(){audioPlayer?.stop();audioPlayer?.currentTime=0;audioTimer?.invalidate();audioTimer=nil;audioSeekSlider.doubleValue=0;playAudioButton?.title="▶ Слушать";audioTimeLabel.stringValue="00:00 / \(clockString(audioPlayer?.duration ?? 0))"}
    @objc func seekAudio(){guard let player=audioPlayer else{return};player.currentTime=audioSeekSlider.doubleValue;audioTimeLabel.stringValue="\(clockString(player.currentTime)) / \(clockString(player.duration))"}
    func audioPlayerDidFinishPlaying(_ player:AVAudioPlayer,successfully flag:Bool){audioTimer?.invalidate();audioTimer=nil;playAudioButton.title="▶ Слушать";audioSeekSlider.doubleValue=player.duration;audioTimeLabel.stringValue="\(clockString(player.duration)) / \(clockString(player.duration))"}
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
