# EvidLock Light na drugim stanowisku

Instrukcja przygotowania drugiego komputera z systemem Windows. Zalecane jest pracowanie na lokalnej kopii projektu, a Google Drive traktowanie jako źródła synchronizacji i backupu.

## Wariant A: tylko gotowy program

Jeżeli na drugim stanowisku ma działać wyłącznie gotowa aplikacja:

1. Zainstaluj i uruchom Google Drive dla komputerów.
2. Zaloguj się na konto zawierające backup EvidLock Light.
3. Poczekaj na zakończenie synchronizacji.
4. Otwórz najnowszy katalog `EvidLockLight_Backup\evidlock_light_DATA`.
5. Uruchom `EvidLockLight.exe`.

Do uruchomienia gotowego EXE nie trzeba instalować Pythona ani zależności projektu.

## Wariant B: stanowisko deweloperskie

### 1. Przygotowanie katalogu

Nie rozwijaj programu bezpośrednio w katalogu synchronizowanym przez Google Drive. Skopiuj najnowszy snapshot do lokalnego katalogu, na przykład:

```text
D:\Projekty\EvidenceLocker\EvidLock-Light
```

Kopia 1:1 powinna zawierać między innymi `evidlock_light`, `docs`, `requirements.txt`, `run_gui.py`, skrypty PowerShell oraz pliki builda.

### 2. Instalacja środowiska

Otwórz PowerShell w katalogu projektu i wykonaj:

```powershell
Set-Location D:\Projekty\EvidenceLocker\EvidLock-Light
Set-ExecutionPolicy -Scope Process Bypass
.\setup_dev.ps1
```

`setup_dev.ps1` tworzy `.venv` i instaluje zależności z `requirements.txt`. Środowisko `.venv` jest lokalne dla stanowiska i nie powinno być kopiowane między komputerami.

### 3. Uruchomienie GUI

```powershell
.\Uruchom_EvidLock_Light.cmd
```

Alternatywnie:

```powershell
.\.venv\Scripts\python.exe run_gui.py
```

### 4. Sprawdzenie działania

Na pierwszym uruchomieniu sprawdź:

- Dashboard i strefę Drag and Drop,
- skórki `Green`, `System`, `Black`,
- `O programie` i diagnostykę,
- `Konsola` oraz `docs --search network`,
- dostęp do katalogów `raporty`, `eksport` i `logi`.

WinPmem, Volatility 3 i TShark są opcjonalne. Ich brak jest pokazywany w diagnostyce i odpowiednich panelach; można je doinstalować z poziomu programu.

## Build na drugim stanowisku

Przed buildem zamknij wszystkie procesy `EvidLockLight.exe`. Następnie uruchom:

```powershell
.\Build_EvidLock_Light.cmd
```

Skrypt:

- sprawdza zależności w `.venv`,
- uruchamia PyInstaller,
- tworzy `dist\EvidLockLight.exe`,
- podmienia główny `EvidLockLight.exe`,
- zapisuje poprzedni plik jako `EvidLockLight_backup_DATA.exe`,
- tworzy kopię wydania w `releases`,
- zapisuje pliki `.sha256`.

Jeżeli wolisz terminal:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean
```

Nie uruchamiaj builda przez dwukrotne kliknięcie starego pliku EXE. Plik EXE uruchamia aplikację, a build wykonują `Build_EvidLock_Light.cmd` albo `build_exe.ps1`.

## Backup na drugim stanowisku

Najpierw sprawdź wykrytą ścieżkę Google Drive:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backup_google_drive_light.ps1 -DetectOnly
```

Jeżeli ścieżka jest poprawna, wykonaj backup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backup_google_drive_light.ps1
```

Tryb backupu:

- pierwsze uruchomienie dla danej lokalizacji tworzy pełny snapshot 1:1,
- kolejne uruchomienia zapisują kod, dokumentację, konfigurację, skrypty i wersje/buildy,
- `-ForceFull` wymusza nową kopię pełną,
- `-DestinationRoot` pozwala podać ścieżkę ręcznie, np. `G:\Mój dysk\EvidLockLight_Backup`.

## Najczęstsze problemy

### Skrypt nie uruchamia się

Uruchom go jawnie z PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_dev.ps1
```

### Build nie tworzy nowego EXE

Zamknij aplikację i sprawdź, czy nie działa proces:

```powershell
Get-Process -Name EvidLockLight -ErrorAction SilentlyContinue
```

### Google Drive nie zostaje wykryty

Uruchom Google Drive dla komputerów, poczekaj na zamontowanie dysku i ponów:

```powershell
.\backup_google_drive_light.ps1 -DetectOnly
```

Jeśli używasz innej ścieżki, podaj ją przez `-DestinationRoot`.

### Brak zależności

Usuń lokalny `.venv` tylko wtedy, gdy środowisko jest uszkodzone, a następnie ponownie wykonaj `setup_dev.ps1`. Nie usuwaj `requirements.txt` ani katalogu `evidlock_light`.
