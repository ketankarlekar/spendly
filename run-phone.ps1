# Run Spendly so a phone on the same Wi-Fi (or Tailscale) can open it.
# Usage:  .\run-phone.ps1
# Debug mode is deliberately OFF: Flask's debugger allows code execution
# for anyone who can reach the server.

Set-Location $PSScriptRoot

$activate = Join-Path $PSScriptRoot "..\venv\Scripts\Activate.ps1"
if (Test-Path $activate) { & $activate }

# Keep one secret key across restarts so you stay signed in. The file is gitignored.
if (-not $env:SECRET_KEY) {
    $keyFile = Join-Path $PSScriptRoot ".secret_key"
    if (-not (Test-Path $keyFile)) {
        $bytes = New-Object byte[] 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        [Convert]::ToBase64String($bytes) | Set-Content -Path $keyFile -Encoding ascii
    }
    $env:SECRET_KEY = (Get-Content $keyFile -Raw).Trim()
}

$ip = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -First 1 -ExpandProperty IPAddress

Write-Host ""
Write-Host "Open on your phone:  http://${ip}:5001" -ForegroundColor Green
Write-Host "Phone must be on the same Wi-Fi (or Tailscale). Ctrl+C to stop."
Write-Host ""

python -m flask --app app run --host 0.0.0.0 --port 5001
