"""Prosta dokumentacja tekstowa z wyszukiwarką."""

from __future__ import annotations


DOCUMENTS = [
    {
        "title": "Nośniki",
        "body": "Lista dysków korzysta z WinAPI. Profesjonalny raport PDF ma osobne sekcje nośników, osadzony font Unicode i polskie znaki. Otwarty podgląd aktualizuje się na bieżąco przy zmianie wybranych dysków, pozwala powiększać tekst, zapisać TXT, otworzyć katalog i bieżący PDF.",
    },
    {
        "title": "Network",
        "body": "Network zawiera skaner portów TCP, kontrolę TShark i czytelny status zależności. Gdy TShark jest niedostępny, przycisk instalacji uruchamia oficjalny pakiet Wireshark przez winget.",
    },
    {
        "title": "Pamięć",
        "body": "Manager pamięci obsługuje zrzuty A/B, SHA-256, porównanie, akwizycję WinPmem i pluginy Volatility 3. Status pokazuje GOTOWY albo BRAK oraz udostępnia instalację Volatility i pobranie lub wskazanie WinPmem.",
    },
    {
        "title": "Zabezpieczenie danych",
        "body": "Dostępne są SHA-256 z raportem w raporty/suma-kontrolna, manifest JSON, archiwizacja ZIP AES-256 i 7z AES-256, kopia 1:1 i porównanie A/B. Hasła szyfrowania mają minimum 8 znaków.",
    },
    {
        "title": "One-click",
        "body": "Workflow One-click przyjmuje pliki i katalogi, ustawia read-only, liczy SHA-256 każdego pliku, tworzy tabelaryczny raport PDF oraz szyfrowane archiwum ZIP albo 7z. Wyniki znajdują się w raporty/One-click.",
    },
    {
        "title": "Zrzut ekranu",
        "body": "Panel pozwala wybrać jedno, kilka albo wszystkie widoczne okna EvidLock Light. Tryb pulpitu minimalizuje aplikację i pokazuje zewnętrzny panel. Przechwytywanie korzysta z User32/GDI i zapisuje PNG w raporty/zrzuty-ekranu.",
    },
    {
        "title": "Bezpieczne zamykanie okien",
        "body": "Okna robocze są podnoszone nad aplikację. Nie można zamknąć okna ani całego programu podczas aktywnej operacji. Główne okno przed zakończeniem zawsze prosi o potwierdzenie.",
    },
    {
        "title": "Dziennik operacji",
        "body": "Dziennik można odświeżyć i wyeksportować jednocześnie do TXT oraz JSON. Po zakończeniu program pokazuje liczbę wpisów, obie ścieżki wynikowe i link Otwórz katalog.",
    },
    {
        "title": "Narzędzia PDF",
        "body": "Tworzenie PDF bez nagłówka obsługuje tekst, DOCX, obrazy i istniejące PDF. Opcjonalne szyfrowanie oraz funkcja Szyfruj PDF używają AES-256 i wymagają hasła minimum 8 znaków. Pliki trafiają do raporty/PDF.",
    },
    {
        "title": "Dashboard i menu narzędzi",
        "body": "Dashboard zawiera zintegrowaną strefę przeciągania i narzędzia podręczne. Lewe menu ma rozwijane Narzędzia z kategoriami Dane i integralność, Nośniki i raporty, Sieć i pamięć oraz Windows i system. Kolejność odpowiada zakładkom Dashboardu.",
    },
    {
        "title": "Ochrona read-only",
        "body": "Jeden panel pozwala sprawdzić liczbę plików chronionych i zapisywalnych, ustawić atrybut read-only albo go usunąć dla pliku lub zawartości katalogu.",
    },
    {
        "title": "Jedna instancja",
        "body": "Mutex Windows blokuje uruchomienie drugiej instancji EvidLock Light. Kolejne uruchomienie przywraca aktywne główne okno i kończy drugi proces.",
    },
    {
        "title": "Build i kopie programu",
        "body": "Build tworzy aktualny EvidLockLight.exe, zachowuje poprzedni oryginał jako backup z datą oraz zapisuje kopię bieżącego wydania w katalogu releases. Każdy artefakt ma plik SHA-256.",
    },
    {
        "title": "Drag and Drop",
        "body": "Pliki i katalogi można przeciągać do centralnej strefy Szybkich akcji. Ponowne dodanie tej samej ścieżki wyświetla komunikat i nie tworzy duplikatu. Dodane elementy wypełniają źródła narzędzi danych.",
    },
    {
        "title": "Eksport rejestru Windows",
        "body": "Okno rejestru pozwala wybrać hive i pełne fizyczne gałęzie. Generuje HIVE, REG, CSV, XLSX, TXT, PDF i JSON, plik sum SHA-256 oraz ustawia read-only.",
    },
    {
        "title": "Logi systemowe Windows",
        "body": "Okno logów udostępnia tryb szybki i pełny, zakres czasu, własne daty, limit, sortowanie i wybór dzienników. Bogaty raport PDF zawiera parametry, status EVTX, SHA-256 oraz próbkę najnowszych zdarzeń z komunikatami.",
    },
]


def search_docs(query: str = "") -> list[dict]:
    needle = str(query or "").casefold()
    if not needle:
        return DOCUMENTS
    return [doc for doc in DOCUMENTS if needle in doc["title"].casefold() or needle in doc["body"].casefold()]
