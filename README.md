# EvidLock Light

EvidLock Light to **młodsza, lżejsza i bardziej modułowa wersja EvidLock**, przygotowana do codziennej pracy technicznej na systemie Windows. Zachowuje sposób pracy, układ interfejsu i najważniejsze rozwiązania znane z EvidLockV2, ale działa jako całkowicie osobne repozytorium i nie wymaga prowadzenia pełnej sprawy dowodowej.

Light jest narzędziem roboczym dla pracownika, administratora i technika. Ma ułatwiać szybkie zabezpieczanie danych, tworzenie raportów, kontrolę integralności, diagnostykę systemu oraz podstawową analizę sieci. Nie jest uproszczonym, spartańskim interfejsem: korzysta z odpinanych okien, panelu Szybkich akcji, pasków postępu, raportów PDF i pełnego menu tematycznego.

**Wersja:** `0.2.0-dev`

**Platforma:** Windows 10/11

**Interfejs:** język polski

**Repozytorium:** niezależne od EvidLock i EvidLockV2

## Relacja do EvidLockV2

EvidLock Light jest młodszą wersją programu EvidLock, a nie jego gałęzią ani dodatkiem. Został wydzielony do osobnego repozytorium, aby rozwijać lżejszy wariant bez obciążania pełnego środowiska EvidLockV2.

Z EvidLockV2 zachowuje między innymi:

- układ głównego okna z menu po lewej i panelem roboczym,
- wizualny styl trzech skórek: `Green`, `System` i `Black`,
- logo oraz lekkie ikony konturowe,
- centralny panel Szybkich akcji,
- odpinane okna narzędzi i podnoszenie ich nad główne okno,
- paski postępu i pojedyncze okna wyników,
- profesjonalne raporty PDF, eksporty i dziennik operacji,
- tryb administratora, blokadę drugiej instancji i ochronę przed zamknięciem podczas operacji,
- dokumentację tekstową z wyszukiwarką i panel diagnostyczny.

Light celowo nie zawiera:

- numeru sprawy i zarządzania pełną sprawą dowodową,
- modułu OCR,
- wielojęzycznych wersji interfejsu,
- rozbudowanego dashboardu sprawy z pełnej wersji EvidLock.

## Najważniejsze założenia

- **Modułowość:** logika jest podzielona na usługi, interfejsy okien i warstwę WinAPI.
- **Windows first:** program korzysta bezpośrednio z WinAPI tam, gdzie system udostępnia potrzebne dane.
- **Bezpieczna praca:** narzędzia nie zamykają się w czasie aktywnej operacji, a główne okno pokazuje własne potwierdzenie zamknięcia z logo EvidLock.
- **Jedna instancja:** uruchomienie kolejnego programu przywraca istniejące okno zamiast otwierać drugi proces roboczy.
- **Czytelne wyniki:** raporty mają osobne sekcje, polskie znaki, sumy SHA-256, ścieżki plików i informacje o statusie.
- **Wspólne źródła danych:** pliki przeciągnięte do głównej strefy są dostępne dla narzędzi kopiowania, hashowania, ochrony i archiwizacji.
- **GUI i CLI:** konsola jest częścią programu, a nie oddzielnym produktem.

## Moduły programu

### Dane i integralność

- **SHA-256 pliku** oblicza sumę kontrolną wskazanego pliku i tworzy raport PDF w `raporty/suma-kontrolna`.
- **Manifest katalogu** tworzy manifest JSON/CSV dla plików i katalogów.
- **Weryfikacja manifestu** porównuje aktualny stan z zapisanymi sumami.
- **Kopia 1:1** kopiuje pliki lub katalogi, weryfikuje wynik przez SHA-256 i zapisuje raport.
- **Porównanie A/B** porównuje dwa pliki albo dwa katalogi, pokazując różnice i podsumowanie.
- **Ochrona read-only** sprawdza status, ustawia atrybut tylko do odczytu oraz usuwa go dla pliku lub zawartości katalogu.
- **One-click** prowadzi przez cały workflow:
  1. wybór plików i katalogów,
  2. ustawienie read-only,
  3. obliczenie SHA-256 każdego pliku,
  4. profesjonalny raport PDF z nazwami, ścieżkami i hashami,
  5. szyfrowane archiwum ZIP albo 7z.

### Archiwizacja i zabezpieczenie danych

- **Archiwizuj** pakuje pliki i katalogi do ZIP albo 7z.
- Szyfrowane archiwa używają AES-256, a hasło musi mieć minimum 8 znaków.
- **One-click** zapisuje wyniki w `raporty/One-click`.
- Raporty sum kontrolnych trafiają do `raporty/suma-kontrolna`.
- Moduł kopii i archiwizacji pokazuje pasek postępu oraz katalog wynikowy po zakończeniu.

### Nośniki i raporty

- **Informacje o nośnikach** pobierają dane dysków przez WinAPI.
- Lista zawiera między innymi litery dysków, typ nośnika, system plików, pojemność i wolne miejsce.
- Ikony dysków odpowiadają wariantom używanym w EvidLockV2: lokalny, USB, sieciowy, optyczny i zewnętrzny.
- Okno danych nośników odświeża się na bieżąco po zmianie zaznaczenia lub ponownym wykryciu dysków.
- Podgląd raportu ma powiększanie tekstu, zapis TXT, otwieranie katalogu i przycisk `Przeglądaj PDF`.
- **Bieżący raport** jest jednym współdzielonym oknem, które aktualizuje treść po kolejnych operacjach zamiast tworzyć wiele podglądów.

### Narzędzia PDF

- Tworzenie PDF z pliku tekstowego, DOCX, obrazu albo istniejącego PDF.
- Tworzenie dokumentu bez dodatkowego nagłówka programu.
- Szyfrowanie gotowego PDF hasłem minimum 8 znaków.
- Wyniki trafiają do `raporty/PDF`.
- Przycisk `Przeglądaj PDF` otwiera aktualny dokument w domyślnej aplikacji Windows.

### Sieć

Moduł Network zawiera lekki, ale zaawansowany skaner TCP dla uprawnionych sieci:

- skanowanie pojedynczego adresu IP albo podsieci CIDR,
- pola adresu podsieci w osobnych oktetach z kropkami i maską,
- opcjonalne skanowanie otwartych portów,
- profile portów, timeout i liczba równoległych wątków,
- ICMP, TCP, reverse DNS/FQDN, nazwa komputera i MAC,
- heurystyczne rozpoznanie komputera Windows, drukarki, routera, kamery, NAS lub innego urządzenia,
- wyniki dopisywane do tabeli natychmiast po wykryciu hosta,
- szczegółowy panel hosta,
- eksport JSON, CSV i PDF,
- menu prawokliku z kopiowaniem danych, RDP i pomocą zdalną OfferRA.

RDP jest dostępny dla wykrytych komputerów Windows. Pomoc techniczna korzysta wyłącznie z trybu `msra.exe /offerRA` i wymaga ręcznie podanego adresu IP.

Moduł zawiera również podstawową analizę PCAP przez TShark. Status TShark jest widoczny w programie, a instalacja Wireshark/TShark może zostać uruchomiona przez `winget`.

### Pamięć

Manager pamięci obsługuje:

- status WinPmem i Volatility 3,
- pobranie albo wskazanie WinPmem,
- instalację Volatility 3,
- akwizycję obrazu pamięci,
- porównanie obrazów A/B,
- SHA-256 obrazów,
- uruchamianie pluginów Volatility 3.

Przy braku dodatkowego narzędzia program pokazuje jasny status `BRAK` i przyciski instalacji albo wskazania pliku.

### Windows i system

- **Eksport rejestru Windows:** wybór hive i gałęzi, formaty HIVE/REG/CSV/XLSX/TXT/PDF/JSON, SHA-256 i read-only.
- **Logi Windows:** tryb szybki i pełny, zakres 24h/7d/30d/cały lub własny, limit, sortowanie, wybór dzienników Application/Security/Setup/System, EVTX, CSV, XLSX, TXT, PDF, JSON i sumy SHA-256.
- **Dziennik programu:** podgląd zdarzeń, eksport TXT i JSON oraz przycisk otwarcia katalogu z wynikami.
- **Zrzut ekranu:** przechwytywanie jednego, kilku albo wszystkich widocznych okien EvidLock Light oraz całego pulpitu z zewnętrznego panelu. Mechanizm używa User32/GDI (`PrintWindow`, `BitBlt`, `GetDIBits`).
- **Diagnostyka:** wersja, tryb administratora, stan zależności, katalogi robocze, dostępne nośniki i dane środowiska z możliwością skopiowania.

## Interfejs użytkownika

### Dashboard

Dashboard jest głównym ekranem roboczym. W górnej części znajduje się duża strefa przeciągania plików i katalogów. Niżej działa panel Szybkich akcji z zakładkami:

1. `Dane i integralność`,
2. `Nośniki i raporty`,
3. `Sieć i pamięć`,
4. `Windows i system`.

Panel pokazuje tylko aktywne narzędzia. Ikona koła zębatego otwiera konfigurator, w którym można dodawać, usuwać, przesuwać i przywracać narzędzia. Limit wynosi 32 aktywne funkcje.

### Menu boczne

Lewe menu zawiera:

- `Dashboard`,
- rozwijane `Narzędzia` z tymi samymi kategoriami co Szybkie akcje,
- `Raporty`,
- `Konsola`,
- `O programie` z dokumentacją i diagnostyką.

### Okna robocze

Narzędzia otwierają się w osobnych, odpinanych oknach podnoszonych nad aplikację. Okna raportów, porównań, nośników, rejestru, logów, pamięci, archiwizacji, PDF i sieci mają własne paski postępu oraz blokadę zamknięcia w czasie pracy.

## Wbudowana konsola

CLI jest silnikiem komend wbudowanym w aplikację. Można go otworzyć przyciskiem `Konsola` i wykonywać polecenia bez uruchamiania oddzielnego programu.

Dostępne grupy poleceń:

- `media` - lista nośników i raport PDF,
- `hash` - SHA-256, manifesty i weryfikacja,
- `copy` - kopia 1:1 i porównanie A/B,
- `archive` - ZIP/7z,
- `pdf` - tworzenie i szyfrowanie PDF,
- `one-click` - pełne zabezpieczenie danych,
- `readonly` - ustawianie, usuwanie i sprawdzanie atrybutu,
- `network` - skan hosta/podsieci, PCAP, status i instalacja TShark,
- `memory` - WinPmem, Volatility 3, akwizycja i porównanie,
- `system` - rejestr, logi, dziennik i diagnostyka,
- `docs` - wyszukiwanie w dokumentacji tekstowej.

Przykłady:

```powershell
--json media list
media report
hash file C:\dane\plik.bin
hash manifest C:\dane --out C:\wyniki\manifest.json
copy one-to-one --src C:\A --dst D:\B
copy compare --a C:\A --b D:\B
readonly check C:\dane
network scan --host 192.168.1.1 --ports 22,80,443
network scan --subnet 192.168.1.0/24 --ports 80,443,445,3389 --include-offline
memory deps
memory compare --a C:\ram-a.raw --b D:\ram-b.raw
pdf create --src C:\dane.txt --password Tajne123
pdf encrypt --src C:\raport.pdf --password Tajne123
archive --src C:\dane --out D:\pakiet.7z --format 7z --password Tajne123
one-click --src C:\dane --password Tajne123 --format zip
--json system journal-export
--json system logs-export
--json system diagnostics
docs --search read-only
```

Każde polecenie może korzystać z globalnej opcji `--json`, a operacje wymagające podwyższonych uprawnień mogą zostać uruchomione z `--admin`.

## Raporty i katalogi wynikowe

Program tworzy katalogi robocze automatycznie przy uruchomieniu:

| Katalog | Zawartość |
| --- | --- |
| `raporty/PDF` | PDF tworzone i szyfrowane przez moduł PDF |
| `raporty/suma-kontrolna` | raporty SHA-256 i manifestów |
| `raporty/One-click` | raporty i archiwa workflow One-click |
| `raporty/zrzuty-ekranu` | PNG z okien i pulpitu |
| `raporty` | raporty modułów, kopii i nośników |
| `eksport` | eksporty rejestru, logów i innych danych |
| `logi` | dziennik operacji programu |
| `docs` | dokumentacja tekstowa dostępna w aplikacji |

Raporty PDF używają fontu Unicode, dzięki czemu poprawnie zapisują polskie znaki. Wyniki zawierają parametry operacji, status, ścieżki, rozmiary, sumy kontrolne i podsumowanie.

## Uruchomienie z kodu

Wymagany jest Windows oraz Python z obsługą `venv`.

```powershell
cd D:\Projekty\EvidenceLocker\EvidLock-Light
.\setup_dev.ps1
.\Uruchom_EvidLock_Light.cmd
```

Można również uruchomić aplikację bezpośrednio:

```powershell
.\.venv\Scripts\python.exe run_gui.py
```

Podstawowe zależności to CustomTkinter, Pillow, ReportLab, OpenPyXL, tkinterdnd2, PyInstaller, pypdf, cryptography, pyzipper i py7zr.

## Drugie stanowisko

Pełna instrukcja przygotowania drugiego komputera znajduje się w [docs/SECOND_WORKSTATION.md](docs/SECOND_WORKSTATION.md). W skrócie: gotowy `EvidLockLight.exe` można uruchomić bez Pythona, a do pracy z kodem należy skopiować snapshot lokalnie, uruchomić `setup_dev.ps1`, a następnie `Uruchom_EvidLock_Light.cmd`. Build wykonuje `Build_EvidLock_Light.cmd`, natomiast backup Google Drive wykonuje `backup_google_drive_light.ps1`.

## Build

Build tworzy aktualny plik EXE, zachowuje poprzedni oryginał i zapisuje kopię wydania w `releases`:

```powershell
.\build_exe.ps1 -Clean
```

Do uruchomienia z Eksploratora Windows można użyć `Build_EvidLock_Light.cmd`. Wrapper zatrzymuje okno po zakończeniu, dzięki czemu wynik builda jest widoczny. Samo `Uruchom za pomocą PowerShell` zamyka okno po zakończeniu; w przypadku błędu skrypt pokazuje komunikat w osobnym oknie.

Powstają:

- `EvidLockLight.exe` - aktualny oryginał,
- `EvidLockLight_backup_DATA.exe` - kopia poprzedniego oryginału,
- `releases/EvidLockLight_DATA.exe` - kopia aktualnego wydania,
- pliki `.sha256` dla artefaktów.

Skrypt sprawdza zależności, wynik PyInstallera, obecność pliku EXE i nie rozpoczyna pracy, jeśli EvidLock Light jest uruchomiony.

## Kopia na Google Drive

`backup_google_drive_light.ps1` automatycznie wykrywa zamontowany dysk Google Drive dla komputerów i zapisuje kopię do `EvidLockLight_Backup`. Sprawdzane są dyski z folderem `My Drive`/`Mój dysk`, etykieta woluminu DriveFS oraz typowe foldery profilu użytkownika. Skrypt nie używa bezpośrednio API Google ani osobnego logowania.

```powershell
.\backup_google_drive_light.ps1
```

Automatyczne wykrywanie można wymusić również jawnie:

```powershell
.\backup_google_drive_light.ps1 -AutoDetect
```

Samą wykrytą ścieżkę można sprawdzić bez wykonywania kopii:

```powershell
.\backup_google_drive_light.ps1 -DetectOnly
```

Tryb kopii:

- pierwsze uruchomienie dla danego katalogu docelowego tworzy pełny snapshot 1:1 całego projektu,
- kolejne uruchomienia kopiują tylko kod, dokumentację, konfigurację, skrypty oraz artefakty wersji/buildów,
- stan jest zapisywany w `.evidlock_light_backup_state.json`,
- każda kopia trafia do osobnego katalogu z datą i milisekundami,
- pełną kopię można wymusić przez `-ForceFull`.

Jeżeli Google Drive nie jest zamontowany albo korzysta z innej ścieżki, skrypt zatrzyma się z komunikatem. Wtedy podaj ścieżkę jawnie:

```powershell
.\backup_google_drive_light.ps1 -DestinationRoot "G:\My Drive\EvidLockLight_Backup"
```

## Struktura projektu

```text
EvidLock-Light/
├── evidlock_light/
│   ├── app.py              # główna powłoka GUI
│   ├── cli.py              # parser i wykonanie komend CLI
│   ├── winapi.py           # cienka warstwa Windows API
│   ├── reports.py          # wspólne generowanie raportów
│   ├── themes.py           # skórki i palety
│   ├── services/           # logika modułów programu
│   ├── ui/                 # okna i komponenty GUI
│   └── assets/              # logo i lekkie ikony PNG
├── docs/                   # dokumentacja tekstowa
├── raporty/                # raporty i PDF
├── eksport/                # eksport rejestru i logów
├── logi/                   # dziennik programu
├── build_exe.ps1           # build PyInstaller
├── backup_google_drive_light.ps1
├── setup_dev.ps1
├── run_gui.py
└── requirements.txt
```

## Moduły techniczne

Warstwa `services` zawiera osobne moduły dla archiwizacji, przechwytywania obrazu, kopii, dokumentacji, hashy, dziennika, nośników, pamięci, sieci, One-click, PDF, read-only, rejestru i logów Windows. Warstwa `ui` udostępnia odpinane okna, strefę Drag and Drop, postęp operacji, raporty, logo i menu.

WinAPI jest używane do danych nośników, informacji o systemie, atrybutów plików, przechwytywania okien, pulpitu, ICMP, MAC, RDP, OfferRA i kontroli instancji. PowerShell lub `winget` są używane tylko tam, gdzie wymagane jest uruchomienie instalatora albo narzędzia systemowego.

## Ograniczenia i odpowiedzialna praca

- Network należy uruchamiać wyłącznie w sieciach, do których użytkownik ma uprawnienia.
- Eksport rejestru, logów, pamięci i niektóre operacje ochrony danych mogą wymagać trybu administratora.
- WinPmem, Volatility 3 i TShark są opcjonalnymi narzędziami zewnętrznymi. Program pokazuje ich brak i nie udaje, że analiza została wykonana bez wymaganej zależności.
- Szyfrowanie archiwów i PDF wymaga hasła minimum 8 znaków. Hasło nie jest zapisywane w raporcie.
- Repozytorium nie zawiera numeru sprawy, OCR ani systemu zarządzania pełną dokumentacją sprawy. Te obszary pozostają poza zakresem młodszej wersji Light.

## Dokumentacja w programie

Zakładka `O programie` zawiera prostą dokumentację tekstową z wyszukiwarką, informacje o twórcy, diagnostykę oraz opis modułów. Dokumentacja jest dostępna również przez CLI:

```powershell
docs --search network
```

## Stan projektu

EvidLock Light jest aktywnie rozwijaną wersją `0.2.0-dev`. Interfejs, moduły i raporty są przygotowane do dalszego rozbudowywania bez zmiany głównej powłoki programu. Każdy nowy moduł może zostać dodany do usługi, okna tematycznego, panelu Szybkich akcji i konsoli.
