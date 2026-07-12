# EvidLock Light - changelog

## 2026-07-12 - samodzielne repo i pełne moduły Windows

- Rozbudowano Network do zaawansowanego skanera TCP dla pojedynczego adresu i podsieci CIDR.
- Dodano profile portów, timeout, równoległość, ICMP, DNS/FQDN, nazwę komputera, MAC i heurystyczne rozpoznawanie typu urządzenia.
- Dodano szczegółowy panel hosta oraz eksport skanu do JSON, CSV i profesjonalnego PDF.
- Dodano kontrolowany RDP dla wykrytych komputerów Windows oraz pomoc techniczną wyłącznie przez `msra.exe /offerRA`; adres IP pomocy można wpisać ręcznie.
- Wyniki skanowania podsieci są teraz dopisywane do tabeli na bieżąco po zakończeniu każdego hosta.
- Dodano przełącznik skanowania otwartych portów oraz pola oktetów z kropkami i maską CIDR dla podsieci.
- Dodano menu prawokliku hosta z RDP, OfferRA, kopiowaniem IP/nazwy/szczegółów JSON i eksportem JSON/CSV/PDF.
- Podgląd informacji o nośnikach aktualizuje to samo okno natychmiast po zaznaczeniu, odznaczeniu lub odświeżeniu dysków.
- Zmiana zestawu nośników unieważnia linki do poprzedniego PDF, aby nie otwierać raportu dla nieaktualnego wyboru.
- Eksport dziennika TXT/JSON pokazuje potwierdzenie, liczbę wpisów, ścieżki plików i link `Otwórz katalog`.
- Dodano panel zrzutów jak w EvidLockV2: wybrane okna, wszystkie widoczne okna i cały pulpit z zewnętrznego kontrolera.
- Zrzuty korzystają bezpośrednio z User32/GDI (`PrintWindow`, `BitBlt`, `GetDIBits`) i trafiają do `raporty/zrzuty-ekranu`.
- Wszystkie okna robocze są podnoszone nad aplikację i blokują zamknięcie podczas aktywnej operacji.
- Główne okno blokuje zamknięcie w czasie pracy narzędzi, a w stanie bezczynności wymaga potwierdzenia zakończenia programu.
- Zastąpiono ciężką ikonę One-click delikatną, przezroczystą ikoną konturowej tarczy dopasowaną do skórki.
- Otwieranie plików i katalogów przeniesiono z `os.startfile` na `ShellExecuteW` w warstwie WinAPI.
- Zastąpiono prosty generator PDF profesjonalnym silnikiem Unicode z sekcjami, tabelami, stopką i numeracją stron.
- Naprawiono polskie znaki w raportach nośników, logów, SHA-256 i One-click.
- Rozbudowano raport nośników oraz raport PDF logów Windows o parametry, EVTX, SHA-256 i próbkę zdarzeń.
- Podgląd raportu ma A-/A+, zapis TXT, zapis PDF i przeglądanie bieżącego PDF.
- Okno nośników po wygenerowaniu aktywuje linki Otwórz katalog i Przeglądaj PDF.
- Dodano Narzędzia PDF: tworzenie bez nagłówka oraz szyfrowanie AES-256 z hasłem minimum 8 znaków.
- Pliki narzędzi PDF są zapisywane w osobnym katalogu `raporty/PDF`.
- Zmieniono Archiwizacja ZIP na Archiwizuj z ZIP AES-256 i 7z AES-256.
- SHA-256 automatycznie tworzy i otwiera raport w `raporty/suma-kontrolna`.
- Dodano One-click z ikoną V2: read-only, SHA-256, profesjonalny PDF, szyfrowane archiwum i pasek postępu.
- One-click jest dostępny w nagłówku, Narzędziach i domyślnych narzędziach podręcznych.
- Górny pasek pokazuje wersję zamiast przycisku O programie; O programie zawiera twórcę jak V2.
- Diagnostyka pokazuje więcej danych systemowych, ścieżek i bibliotek oraz umożliwia kopiowanie.
- Uporządkowano lewe menu: Dashboard, rozwijane Narzędzia w czterech kategoriach, Raporty, Konsola i O programie.
- Usunięto z menu osobną pozycję Szybkie akcje oraz oddzielne pozycje modułów; kategorie odpowiadają zakładkom Dashboardu.
- Zintegrowano nagłówek narzędzi podręcznych z panelem zakładek i poprawiono wykorzystanie wysokości Dashboardu.
- Widoki Narzędzi korzystają z małych, dwukolumnowych kafli z wyraźnymi tytułami.
- Dodano wspólny panel read-only: sprawdzenie statusu, ustawienie i usunięcie atrybutu.
- Dodano manager pamięci: zrzuty A/B, SHA-256, porównanie, WinPmem i pluginy Volatility 3.
- Dodano statusy GOTOWY/BRAK oraz instalację Volatility 3, Wireshark/TShark i pobieranie lub wskazanie WinPmem.
- Dodano mutex Windows blokujący kolejne instancje i przywracający istniejące okno.
- Dodano `Przeglądaj PDF` do bieżącego raportu, nośników, rejestru, logów oraz kopii/porównania.
- Dla wyniku bez własnego PDF przycisk automatycznie generuje raport i otwiera go w domyślnej przeglądarce systemowej.
- Zastąpiono przerysowane logo dokładnym algorytmem EvidLockV2: przezroczyste RGBA, cienki kontur i antyaliasing PIL.
- Skopiowano bez zmian pięć oryginalnych ikon PNG nośników z EvidLockV2 i dołączono je do buildu PyInstaller.
- Okna nośników, rejestru i logów są pojedynczymi instancjami; ponowne uruchomienie odświeża lub podnosi istniejące okno.
- Dodano jedno współdzielone okno bieżącego raportu, które odświeża treść zamiast mnożyć podglądy.
- Bieżący wynik każdego modułu można zapisać jako raport PDF z obsługą polskich znaków.
- Dodano logo tarczy i kłódki o geometrii zgodnej z EvidLockV2.
- Skórka `Black` korzysta z żółto-czarnej palety EvidLockV2, włącznie z wyglądem bocznego menu i neutralnych przycisków.
- Przebudowano główny panel Szybkich akcji na cztery zakładki tematyczne z limitem 32 aktywnych narzędzi.
- Główny panel pokazuje wyłącznie bieżące narzędzia; biblioteka, dodawanie, usuwanie i przesuwanie są dostępne pod ikoną koła zębatego.
- Dodano dużą strefę przeciągania plików i katalogów nad Szybkimi akcjami.
- Przeniesiono EvidLock Light do całkowicie osobnego repozytorium z własnym `.venv`, `requirements.txt`, buildem i backupem.
- Dodano Drag and Drop plików i katalogów przez `tkinterdnd2`.
- Powtórne dodanie tego samego pliku lub katalogu pokazuje komunikat i nie tworzy duplikatu.
- Przeciągnięte elementy zasilają kopiowanie, porównanie, SHA-256, manifest i archiwizację.
- Dodano pełne okno eksportu rejestru: hive, gałęzie danych, REG/CSV/XLSX/TXT/PDF/JSON, SHA-256 i read-only.
- Dodano pełne okno logów Windows: tryb szybki/pełny, zakres czasu, limit, sortowanie, wybór dzienników, EVTX i raporty.
- Dodano pełne okno informacji o nośnikach z lekkimi ikonami dysków odpowiadającymi wariantom EvidLockV2.
- Build dołącza runtime `tkinterdnd2` i działa bez zależności od repo EvidLock.

## 2026-07-12 - centralne Szybkie akcje, postęp i narzędzie kopii

- `Szybkie akcje` są pełnym centralnym panelem aplikacji, a nie małym panelem bocznym.
- Dodano tematyczną bibliotekę narzędzi: dane i integralność, nośniki i raporty, network i pamięć oraz system Windows.
- Kafle można dodawać, usuwać, przeciągać i przesuwać przyciskami; układ jest zapisywany w profilu użytkownika.
- Dodano osobne okno `Kopia 1:1 i porównanie A/B` z wyborem pliku lub katalogu, paskiem postępu i logiem.
- Kopia 1:1 automatycznie wykonuje weryfikację SHA-256 oraz zapisuje raport PDF, TXT i JSON.
- Paski postępu dodano również do SHA-256, manifestu, archiwizacji, raportu nośników, rejestru i logów Windows.
- Narzędzia w widoku `Narzędzia` są uporządkowane w tych samych kategoriach co biblioteka Szybkich akcji.
- Build zapisuje aktualny oryginał, backup poprzedniego EXE i kopię wydania z datą jak EvidLockV2.

## 2026-07-11 - trzy skórki i kontrolowany build

- Dodano trzy skórki interfejsu Light: `Green`, `System` i `Black`.
- Dodano wybór skórki w górnej belce, zgodnie z układem EvidLockV2.
- Wybrana skórka jest zapisywana w profilu użytkownika i przywracana przy starcie.
- Skórka `System` rozpoznaje jasny lub ciemny tryb aplikacji Windows.
- Diagnostyka pokazuje aktywną skórkę.
- Skrypt build sprawdza zależności, kod zakończenia PyInstallera i obecność EXE.
- Naprawiono otwieranie stron z odpinanymi panelami po zmianie układu menu.

## 2026-07-11 - start wersji Light

- Utworzono osobną gałąź `evidlock-light`.
- Dodano katalog `evidlock_light`.
- Przygotowano założenia wersji Light: bez numeru sprawy, bez OCR, bez wielojęzyczności.
- Zaplanowano GUI CTk i CLI jako równorzędne interfejsy do tych samych modułów usługowych.
- Dodano modułowy podział na nośniki, hash, kopię/porównanie, archiwizację, read-only, network, pamięć, rejestr, logi, raporty, diagnostykę i dokumentację tekstową.

## 2026-07-11 - interfejs jak EvidLockV2 i konsola w aplikacji

- Przebudowano GUI Light z prostych zakładek na układ z bocznym menu, nagłówkiem, kaflami akcji i panelem wyników.
- Dodano stronę `Konsola`, która uruchamia wewnętrzny silnik CLI bez osobnego programu użytkowego.
- Usunięto osobny build i launcher CLI; konsola jest dostępna z poziomu GUI.
- Poprawiono raport PDF nośników: polskie znaki, font Unicode z Windows i czytelne formatowanie rozmiarów.
- Dodano lokalny `.gitignore` dla katalogów roboczych Light: `build`, `dist`, `logi`, `raporty`, `eksport` i cache Pythona.

## 2026-07-11 - O programie jak w EvidLockV2

- Zastąpiono osobne pozycje `Dokumentacja` i `Diagnostyka` jedną sekcją `O programie`.
- `O programie` ma zakładki: `O programie`, `Funkcje`, `Dokumentacja techniczna` i `Diagnostyka`.
- Dokumentacja techniczna wróciła do `O programie` i ma wyszukiwarkę.
- Diagnostyka wróciła do `O programie` i pokazuje m.in. tryb administratora, liczbę nośników, WinPmem/Volatility 3 oraz TShark.

## 2026-07-11 - odpinane panele i dziennik

- Dodano panele `Szybkie akcje`, `Narzędzia`, `Raporty` i `Dziennik`.
- Panele można odpinać do osobnych okien roboczych jak w EvidLockV2.
- Dodano dziennik operacji Light z zapisem JSONL oraz eksportem TXT/JSON.
- `System` i `Raporty` mają eksport dziennika Light.
- Eksport logów Windows zapisuje teraz EVTX oraz tekstowy podgląd TXT dla kanałów `System`, `Application` i `Security`.
- Wbudowana konsola zapisuje wykonane komendy do dziennika.
