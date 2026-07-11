"""Prosta dokumentacja tekstowa z wyszukiwarką."""

from __future__ import annotations


DOCUMENTS = [
    {
        "title": "Nośniki",
        "body": "Lista dysków korzysta z WinAPI. Raport PDF opisuje literę, etykietę, system plików, rozmiar, wolne miejsce i typ nośnika.",
    },
    {
        "title": "Network",
        "body": "Network zawiera skaner portów TCP oraz kontrolę TShark. Analizator PCAP będzie rozbudowywany jako osobny moduł.",
    },
    {
        "title": "Pamięć",
        "body": "Moduł pamięci sprawdza obecność WinPmem i Volatility 3 oraz uruchamia analizę Volatility dla wskazanego obrazu.",
    },
    {
        "title": "Zabezpieczenie danych",
        "body": "Dostępne są SHA-256, manifest JSON, weryfikacja manifestu, archiwizacja ZIP, kopia 1:1 i porównanie A/B. Długie operacje pokazują pasek postępu i log. Kopia jest po zapisie weryfikowana przez SHA-256 i tworzy raport PDF, TXT oraz JSON.",
    },
    {
        "title": "Szybkie akcje",
        "body": "Szybkie akcje zajmują centralny panel aplikacji. Kafle można dodawać z biblioteki tematycznej, usuwać, przeciągać oraz przesuwać przyciskami góra/dół. Kolejność jest zapisywana w profilu użytkownika.",
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
        "body": "Okno logów udostępnia tryb szybki i pełny, zakres czasu, własne daty, limit, sortowanie i wybór dzienników. Tryb pełny eksportuje EVTX; raporty obejmują CSV, XLSX, TXT, PDF i JSON z SHA-256.",
    },
]


def search_docs(query: str = "") -> list[dict]:
    needle = str(query or "").casefold()
    if not needle:
        return DOCUMENTS
    return [doc for doc in DOCUMENTS if needle in doc["title"].casefold() or needle in doc["body"].casefold()]
