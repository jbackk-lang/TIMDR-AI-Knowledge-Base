# Odkrywanie i integracja TIMDR Knowledge Hub

## Dla ludzi
- Repozytorium wiedzy: https://github.com/jbackk-lang/TIMDR-AI-Knowledge-Base
- Dokumenty formalne: https://github.com/jbackk-lang/GIA-TIMDR
- Strona statyczna do publikacji: `docs/index.html`

## Dla wyszukiwarek
`docs/index.html` ma tytuł, opis, semantyczny HTML i linki do źródeł.
Aby indeksowały ją wyszukiwarki, strona **musi zostać opublikowana**
(np. przez GitHub Pages). Sam commit nie oznacza uruchomionej strony.
Nie podajemy fikcyjnego adresu Pages ani sitemap przed publikacją.

## Dla asystentów AI
`docs/llms.txt` to pomocniczy katalog źródeł, a nie gwarancja indeksowania
przez ChatGPT lub inne modele. MCP wymaga osobnego serwera i świadomej
konfiguracji klienta. Obecny Worker `/search` jest chroniony tokenem i
nie należy go wystawiać publicznie bez kontroli dostępu, limitów i audytu.

## Publikacja na GitHub Pages (opcjonalnie)
W ustawieniach repozytorium GitHub: Settings > Pages > Build and deployment >
Deploy from a branch, wybierz gałąź główną i folder `/docs` (jeśli
ta opcja jest dostępna). GitHub wyświetli faktyczny adres strony.
Nie trzeba zmieniać Cloudflare DNS ani istniejącego sklepu.
Przed publikacją sprawdź, czy repozytorium i plan pozwalają na Pages.

## Zasady bezpieczeństwa
Nigdy nie publikuj `TIMDR_SEARCH_TOKEN`, `OPENAI_API_KEY`,
pliku `worker-token.dpapi` ani surowych wektorów z prywatnych źródeł.
Publiczny katalog zawiera wyłącznie linki do publicznych repozytoriów.
Wiedza źródłowa może zawierać niezweryfikowane twierdzenia badawcze.
