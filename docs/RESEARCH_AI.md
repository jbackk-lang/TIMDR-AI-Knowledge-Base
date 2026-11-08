# TIMDR Research AI — lokalny RAG z cytowaniami

To prototyp uruchamiany lokalnie w PowerShell. Wykorzystuje istniejący indeks
Cloudflare Vectorize `timdr-unified-v1` przez zabezpieczony Worker
`https://timdr-vector-search.jbackk.workers.dev/search`.

## Instalacja

```powershell
git pull
.\.venv312\Scripts\python.exe -m pip install "openai>=1.0"
$env:TIMDR_SEARCH_URL = "https://timdr-vector-search.jbackk.workers.dev/search"
```

`TIMDR_SEARCH_TOKEN` musi odpowiadać sekretowi Workera. Jeśli poprzednia sesja
PowerShell jest nadal otwarta, zmienna jest już ustawiona. Nie publikuj sekretu.

## Test bez płatnego modelu

```powershell
.\.venv312\Scripts\python.exe -m timdr_kb.research_ai "Czym jest chronoproces TIMDR?" --sources-only
```

## Odpowiedzi generowane z cytowaniami

Ustaw własny klucz API OpenAI **lokalnie**, nie w repozytorium i nie w czacie:

```powershell
$env:OPENAI_API_KEY = Read-Host "Wklej klucz OpenAI API"
.\.venv312\Scripts\python.exe -m timdr_kb.research_ai "Czym jest chronoproces TIMDR?"
```

Opcjonalnie: `--branch G`, `--limit 5`, `--model gpt-4.1-mini`.
OpenAI API jest rozliczane osobno od subskrypcji ChatGPT; nie uruchamiaj
generowania, jeśli nie chcesz ponosić kosztów. Tryb `--sources-only` nie
wywołuje modelu generującego.

## Zasady i ograniczenia

- Używany jest ten sam model embeddingów 384D co przy indeksowaniu.
- Pobierane jest maksymalnie 10 wyników z Workera, następnie wykonywane jest
  lokalne ponowne rankingowanie i deduplikacja po URL.
- Kontekst to fragmenty `excerpt` zapisane w metadanych Vectorize, a nie
  pełna zawartość dokumentów. Długie dokumenty mogą wymagać rozszerzenia
  indeksu o magazyn tekstów.
- Cytowania [S1], [S2] wskazują na zwrócone adresy GitHub. Kod odrzuca
  nieistniejące identyfikatory cytowań, ale nie potwierdza automatycznie,
  czy każde twierdzenie jest prawdziwie poparte źródłem.
- Dokumentacja TIMDR nie stanowi automatycznie niezależnej walidacji naukowej.
- Prototyp nie udostępnia publicznego endpointu generowania; klucz OpenAI
  pozostaje po stronie użytkownika. Nie zmienia DNS ani sklepu.
