# EvidLock Light

EvidLock Light to samodzielna, modułowa aplikacja do codziennej pracy technicznej na Windows. Projekt ma własne repozytorium, środowisko, zależności i build. Nie prowadzi spraw, nie wymaga numeru sprawy i nie zawiera OCR.

## Założenia

- jeden język interfejsu: polski,
- GUI oparte o CustomTkinter,
- trzy skórki interfejsu: `Green`, `System` i `Black`,
- CLI jako konsola wbudowana w główne okno,
- logika w małych modułach usługowych,
- WinAPI tam, gdzie Windows udostępnia dane systemowe,
- odpinane panele robocze jak w EvidLockV2,
- centralny panel Szybkich akcji z przezroczystym, konturowym logo generowanym dokładnie jak w EvidLockV2, zakładkami tematycznymi i konfiguracją pod ikoną koła zębatego,
- do 32 aktywnych narzędzi, z przeciąganiem i zmianą kolejności wewnątrz kategorii,
- przeciąganie plików i katalogów z kontrolą duplikatów,
- bez dashboardu sprawy, kółka integralności, numeru sprawy i OCR,
- prosta dokumentacja tekstowa z wyszukiwarką,
- tryb administratora dostępny z GUI i CLI.

## Moduły

Główny ekran pokazuje tylko aktywne narzędzia w czterech zakładkach: `Dane i integralność`, `Nośniki i raporty`, `Sieć i pamięć` oraz `Windows i system`. Dodawanie, usuwanie i kolejność narzędzi są dostępne w osobnym konfiguratorze otwieranym ikoną koła zębatego. Nad panelem znajduje się duża strefa przeciągania plików i katalogów.

- Nośniki: jedno odświeżane okno dysków, oryginalne ikony PNG USB/lokalny/sieciowy/optyczny z EvidLockV2, zajętość oraz raport PDF/JSON.
- Hash SHA-256: pliki, katalogi, manifest JSON/CSV, weryfikacja manifestu.
- Zabezpieczenie danych: archiwizacja ZIP, kopia 1:1, porównanie A/B.
- Kopia i porównanie: osobne okno, pasek postępu, automatyczna weryfikacja SHA-256 oraz raport PDF/TXT/JSON.
- Atrybut tylko do odczytu: ustawianie i zdejmowanie atrybutu dla plików/katalogów.
- Network: skaner portów TCP, podstawowa diagnostyka hosta, kontrola zależności TShark dla analiz PCAP.
- Pamięć: kontrola WinPmem i Volatility 3, punkty startowe do akwizycji i analizy.
- Rejestr Windows: wybór hive i fizycznych gałęzi, `.hiv`, `.reg`, CSV, XLSX, TXT, PDF, JSON, SHA-256 i read-only.
- Logi Windows: tryb szybki/pełny, zakres 24h/7d/30d/cały/własny, limit, sortowanie, Application/Security/Setup/System, EVTX, CSV, XLSX, TXT, PDF, JSON, SHA-256 i read-only.
- Raporty: PDF, JSON, TXT, CSV i XLSX zależnie od modułu.
- Bieżący raport: jedno współdzielone okno, które zastępuje treść po kolejnej operacji i zapisuje wynik dowolnego modułu do PDF.
- Dziennik: wpisy operacji programu, podgląd i eksport TXT/JSON.
- Zrzut ekranu/nagrywanie: planowany moduł lekki, ograniczony do głównego okna.

## Uruchomienie

```powershell
.\setup_dev.ps1
.\Uruchom_EvidLock_Light.cmd
```

## Wbudowana konsola

CLI nie jest osobnym programem użytkowym. Jest silnikiem komend wbudowanym w aplikację i dostępny z przycisku `Konsola` w GUI.

Przykładowe komendy w konsoli aplikacji:

- `media list --json`
- `media report`
- `hash file C:\plik.bin`
- `hash manifest C:\folder --out C:\manifest.json`
- `copy compare --a C:\A --b D:\B`
- `readonly set C:\folder`
- `readonly clear C:\folder`
- `network scan --host 192.168.1.1 --ports 22,80,443`
- `system journal-export --json`
- `system logs-export --json`
- `system diagnostics --json`

## Budowanie

```powershell
.\build_exe.ps1 -Clean
```

Skrypt buduje główny artefakt:

- `EvidLockLight.exe` - aplikacja graficzna,
- konsola CLI jest dostępna wewnątrz aplikacji przez przycisk `Konsola`.

Po buildzie, tak jak w EvidLockV2, powstają:

- `EvidLockLight.exe` - aktualny oryginał,
- `EvidLockLight_backup_DATA.exe` - kopia poprzedniego oryginału,
- `releases/EvidLockLight_DATA.exe` - kopia aktualnego wydania,
- pliki `.sha256` dla każdego artefaktu.

Skrypt sprawdza zależności, wynik PyInstallera i obecność pliku EXE. Po każdym
buildzie tworzy również plik kontrolny SHA-256.

## Repozytorium

Repozytorium jest całkowicie niezależne od EvidLock i EvidLockV2. Katalog `.venv`, buildy, raporty oraz eksporty są lokalnymi danymi roboczymi i nie trafiają do Git.
