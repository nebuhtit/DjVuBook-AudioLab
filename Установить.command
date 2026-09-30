#!/bin/zsh
# 2026-09-28. Однократная установка из Homebrew и официального репозитория Tesseract.
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd -- "${0:A:h}"
if ! command -v brew >/dev/null; then
  print 'Нужен Homebrew. Инструкция: https://brew.sh/ . После установки запустите этот файл снова.'
  read -k 1 '?Нажмите любую клавишу…'
  exit 1
fi
brew install djvulibre tesseract python
mkdir -p models
for lang in rus eng; do
  if [[ ! -s "models/$lang.traineddata" ]]; then
    curl --fail --location --retry 2 "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/$lang.traineddata" --output "models/$lang.traineddata.part"
    mv "models/$lang.traineddata.part" "models/$lang.traineddata"
  fi
done
print 'Готово. Теперь запустите Открыть.command. Дальнейшая работа — офлайн.'
read -k 1 '?Нажмите любую клавишу…'
