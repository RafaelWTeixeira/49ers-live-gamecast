# Gera o executável para Windows e o .zip para distribuir (dist\Gamecast-<versão>.zip).
# Uso, na raiz do projeto: .\scripts\build.ps1   (opcional: -Out <pasta de build>)
#
# O build acontece fora do OneDrive (%LOCALAPPDATA%\gamecast-build): o OneDrive trava os milhares
# de arquivos gerados enquanto sincroniza. Só o .zip final vem para a pasta do projeto.
#
# Sem $ErrorActionPreference = "Stop": no PowerShell 5.1 ele trata os logs do PyInstaller (stderr)
# como erro. O resultado é checado pelo $LASTEXITCODE.
param([string]$out = (Join-Path $env:LOCALAPPDATA "gamecast-build"))

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$version = (Select-String -Path pyproject.toml -Pattern '^version = "(.+)"').Matches[0].Groups[1].Value
$app = Join-Path $out "dist\Gamecast"

# Caminhos absolutos: com --specpath, os relativos seriam resolvidos a partir da pasta de build.
# O uvicorn e o anyio carregam módulos por nome em tempo de execução: o PyInstaller não os
# encontra sozinho, por isso o --collect-submodules.
uv run --group build pyinstaller "$root\app\launcher.py" `
    --name Gamecast `
    --console `
    --noconfirm `
    --clean `
    --paths "$root" `
    --workpath "$out\build" `
    --distpath "$out\dist" `
    --specpath "$out" `
    --add-data "$root\app\static;app/static" `
    --add-data "$root\mock;mock" `
    --collect-submodules uvicorn `
    --collect-submodules anyio `
    --collect-submodules websockets
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

Copy-Item packaging\LEIA-ME.txt (Join-Path $app "LEIA-ME.txt")
New-Item -ItemType Directory -Force dist | Out-Null
$zip = "dist\Gamecast-$version.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $app -DestinationPath $zip
Write-Host "`nPronto: $zip"
