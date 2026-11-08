# Zero-cost local embedding -> protected Cloudflare Vectorize integration test.
# Compatible with Windows PowerShell 5.1. Does not expose any public ports.
param([string]$Question = "Czym jest chronoproces TIMDR?")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv312\Scripts\python.exe"
$tokenFile = Join-Path $HOME ".timdr\worker-token.dpapi"
if (-not (Test-Path $python)) { throw "Brak Pythona .venv312. Uruchom z repozytorium z zainstalowanymi zaleznosciami." }
if (-not (Test-Path $tokenFile)) { throw "Brak pliku DPAPI: $tokenFile" }
# Do not hijack an existing server; its token may differ.
$tcp = New-Object Net.Sockets.TcpClient
try {
    $pending = $tcp.BeginConnect("127.0.0.1", 8789, $null, $null)
    if ($pending.AsyncWaitHandle.WaitOne(500, $false)) {
        try { $tcp.EndConnect($pending); throw "Port 8789 jest zajety. Zatrzymaj wczesniejszy serwer przez Ctrl+C i uruchom test ponownie." }
        catch [System.Net.Sockets.SocketException] {}
    }
} finally { $tcp.Close() }
$secure = (Get-Content -LiteralPath $tokenFile -Raw).Trim() | ConvertTo-SecureString
$env:TIMDR_SEARCH_TOKEN = [System.Net.NetworkCredential]::new("", $secure).Password
if ([string]::IsNullOrWhiteSpace($env:TIMDR_SEARCH_TOKEN)) { throw "Nie udalo sie odzyskac tokenu Workera." }
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
$env:TIMDR_EMBEDDING_TOKEN = [BitConverter]::ToString($bytes).Replace("-", "")
$job = Start-Job -ArgumentList $root, $env:TIMDR_EMBEDDING_TOKEN -ScriptBlock {
    param($folder, $token)
    Set-Location $folder
    $env:TIMDR_EMBEDDING_TOKEN = $token
    & ".\.venv312\Scripts\python.exe" -m timdr_kb.embedding_server
}
try {
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 300
        $probe = New-Object Net.Sockets.TcpClient
        try {
            $ar = $probe.BeginConnect("127.0.0.1", 8789, $null, $null)
            if ($ar.AsyncWaitHandle.WaitOne(250, $false)) {
                try { $probe.EndConnect($ar); $ready = $true; break }
                catch [System.Net.Sockets.SocketException] {}
            }
        } finally { $probe.Close() }
        if ($job.State -ne "Running") { break }
    }
    if (-not $ready) {
        Receive-Job $job
        throw "Lokalny serwer nie wystartowal."
    }
    Write-Host "TIMDR: lokalny model 384D -> prywatny Cloudflare Vectorize" -ForegroundColor Cyan
    & $python -m timdr_kb.local_bridge $Question
    if ($LASTEXITCODE -ne 0) { throw "Wyszukiwanie nie powiodlo sie (kod $LASTEXITCODE)." }
} finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    Remove-Item Env:TIMDR_EMBEDDING_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:TIMDR_SEARCH_TOKEN -ErrorAction SilentlyContinue
}
