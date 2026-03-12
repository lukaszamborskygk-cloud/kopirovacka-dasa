# 📋 Kopírovačka

Správca histórie schránky pre Windows. Ukladá posledných 20 skopírovaných položiek (text, obrázky, súbory) a umožňuje rýchle prepínanie medzi nimi.

---

## 🚀 Inštalácia (pre kolegov)

1. Choď na záložku **[Releases](../../releases/latest)**
2. Stiahni **`Kopirovacka_Setup.zip`**
3. Rozbaľ ZIP a spusti **`Kopirovacka_Installer.exe`**
4. Klikni **Inštalovať** → počkaj na 100% → **Dokončiť**
5. Aplikácia sa spustí automaticky ✅

---

## ⌨️ Klávesové skratky

| Skratka | Funkcia |
|---------|---------|
| `Ctrl+;` | Otvoriť / zatvoriť okno |
| `Ctrl+V` | Vložiť aktuálne vybranú položku |
| `Delete` | Vymazať vybranú položku |
| `Escape` | Skryť okno |

---

## 🛠️ Funkcie

- **História 20 položiek** – text, obrázky, súbory
- **Zelený banner** – vždy vidno čo sa práve vkladá
- **Pripnutie** – dôležité položky nevypadnú z histórie
- **Vyhľadávanie** – rýchle filtrovanie histórie
- **System tray** – beží na pozadí, ikona v lište
- **Vždy navrchu** – voliteľné, okno ostáva nad ostatnými
- **Export histórie** – uloženie do JSON súboru
- **Automatický štart** – spúšťa sa s Windowsom

---

## 🔄 Aktualizácia (pre kolegov)

1. Choď na [Releases](../../releases/latest)
2. Stiahni nový **`Kopirovacka_Setup.zip`**
3. Spusti inštalátor — **automaticky prepíše starú verziu**
4. História sa zachová ✅

---

## 🏗️ Pre vývojárov – build

### Požiadavky
- Python 3.11+
- Windows 10/11

### Lokálny vývoj
```bash
git clone https://github.com/YOUR_USERNAME/kopirovacka
cd kopirovacka
pip install -r app/requirements.txt
python app/main.py
```

### Build EXE
```bash
pip install pyinstaller
python build.py
# → dist/Kopirovacka.exe
```

### Build inštalátora
```bash
pyinstaller --onefile --windowed --name=Kopirovacka_Installer \
  --add-binary="dist/Kopirovacka.exe;." \
  installer/installer_gui.py
# → dist/Kopirovacka_Installer.exe
```

### Vydanie novej verzie
1. Zmeň verziu v `app/main.py` (riadok `VERSION = "..."`)
2. Zmeň verziu v `version.json`
3. Vytvor git tag: `git tag v1.1.0 && git push --tags`
4. GitHub Actions automaticky zbuilduje a vytvorí Release 🚀

---

## 📁 Štruktúra projektu

```
kopirovacka/
├── app/
│   ├── main.py              # Hlavná aplikácia
│   ├── database.py          # SQLite história
│   ├── clipboard_monitor.py # Sledovanie schránky
│   ├── hotkeys.py           # Globálne skratky
│   └── requirements.txt
├── installer/
│   ├── installer_gui.py     # Python inštalátor (tkinter)
│   └── installer.nsi        # NSIS inštalátor (alternatíva)
├── assets/
│   └── icon.ico
├── .github/workflows/
│   └── build.yml            # GitHub Actions CI/CD
├── build.py                 # PyInstaller build skript
├── version.json             # Aktuálna verzia (pre auto-update)
└── README.md
```

---

## 🗑️ Odinštalácia

**Možnosť 1:** Nastavenia Windows → Aplikácie → Kopírovačka → Odinštalovať

**Možnosť 2:** Spustiť `%LOCALAPPDATA%\Kopirovacka\Uninstall_Kopirovacka.cmd`

---

## 📊 Technické detaily

- **Jazyk:** Python 3.11
- **GUI:** tkinter (štandardná knižnica)
- **Databáza:** SQLite (uložená v `%APPDATA%\Kopirovacka\history.db`)
- **Balíky:** pyperclip, keyboard, Pillow, pywin32, pystray
