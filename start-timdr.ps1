# TIMDR Research AI launcher for Windows PowerShell.
# Restores the Cloudflare Worker token from Windows DPAPI; never prints the token.
param(
    [switch]$Test,
    [string]$Question = "Czym jest chronoproces TIMDR?",
    [switch]$Answer
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$tokenFile = Join-Path $HOME ".timdr\worker-token.dpapi"
$python = Join-Path $repo ".venv312\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $tokenFile)) {
    Write-Error "Brak zaszyfrowanego tokenu: $tokenFile. Przywroc go na tym samym koncie Windows lub odnow sekret Workera."
    exit 1
}
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Brak srodowiska Python: $python. Utworz .venv312 i zainstaluj requirements."
    exit 1
}
try {
    $secure = (Get-Content -LiteralPath $tokenFile -Raw).Trim() | ConvertTo-SecureString
    $env:TIMDR_SEARCH_TOKEN = [System.Net.NetworkCredential]::new("", $secure).Password
    if ([string]::IsNullOrWhiteSpace($env:TIMDR_SEARCH_TOKEN)) {
        throw "Odzyskany token jest pusty."
    }
} catch {
    Write-Error "Nie mozna odszyfrowac tokenu. Uzyj tego samego konta Windows, na ktorym zapisano plik."
    exit 1
}
$env:TIMDR_SEARCH_URL = "https://timdr-vector-search.jbackk.workers.dev/search"
Write-Host "TIMDR: token odzyskany, adres Cloudflare ustawiony." -ForegroundColor Green
if ($Test) {
    & $python -m timdr_kb.research_ai $Question --sources-only
    exit $LASTEXITCODE
}
if ($Answer) {
    if (-not $env:OPENAI_API_KEY) {
        Write-Error "Brak OPENAI_API_KEY. Uzyj -Test bez kosztow API lub ustaw klucz OpenAI lokalnie."
        exit 1
    }
    & $python -m timdr_kb.research_ai $Question
    exit $LASTEXITCODE
}
Write-Host "Dostep skonfigurowany w tym procesie PowerShell."
Write-Host "Aby uruchomic wyszukiwanie, wykonaj: .\start-timdr.ps1 -Test"
Write-Host "Aby wygenerowac odpowiedz: .\start-timdr.ps1 -Answer -Question 'Twoje pytanie'"
