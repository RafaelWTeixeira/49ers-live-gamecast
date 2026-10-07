# 49ers Live Gamecast

Painel gráfico ao vivo para lives de jogos do San Francisco 49ers. A página roda no navegador e entra no StreamYard como compartilhamento de tela, ao lado das câmeras; o StreamYard transmite para o YouTube.

- Plano e roadmap: [docs/PLANO.md](docs/PLANO.md)
- Linguagem do domínio: [GLOSSARY.md](GLOSSARY.md)
- Decisões de arquitetura: [docs/adr/](docs/adr/)
- Operação na live: [docs/STREAMYARD.md](docs/STREAMYARD.md)

## Rodando

Requer [uv](https://docs.astral.sh/uv/).

> **OneDrive:** com o projeto dentro do OneDrive, os executáveis do `.venv` quebram
> (`uv trampoline failed to canonicalize script path`). Aqui o `.venv` é uma junction para uma pasta fora do OneDrive:
>
> ```powershell
> New-Item -ItemType Directory -Force "$HOME\.venvs\49ers-live-gamecast"
> New-Item -ItemType Junction -Path .venv -Target "$HOME\.venvs\49ers-live-gamecast"
> uv sync
> ```

```sh
uv sync
uv run uvicorn app.main:app --reload       # desenvolvimento, com o jogo simulado
```

Numa live, com o jogo real da ESPN (ver [docs/STREAMYARD.md](docs/STREAMYARD.md)):

```powershell
.\scripts\live.ps1
```

- `http://localhost:8000/` — health check
- `http://localhost:8000/api/game` — Game State atual (JSON); `/docs` lista a API
- `http://localhost:8000/control` — painel do operador: Control Mode (AUTO/MANUAL), edição do jogo, eventos, desfazer
- `ws://localhost:8000/ws/game` — envia o Game State ao conectar e, depois, cada mudança (`GAME_STATE`) e cada Game Event (`GAME_EVENT`)
- `http://localhost:8000/overlay` — o Gamecast (16:9, se ajusta à janela), compartilhado como tela no StreamYard
  - `?demo` — repete as animações de todos os Game Events (`?demo=touchdown`, só uma); só para conferir

## Dados

O Provider é escolhido por `GAMECAST_PROVIDER`:

- `mock` (padrão): o `MockProvider` reproduz `mock/plays.json` em loop a partir de `mock/game.json`.
- `espn`: o jogo real, pela API pública da ESPN (ver `docs/adr/0005`). Opções:
  - `GAMECAST_FEATURED_TEAM`: sigla do Featured Team na ESPN (padrão `SF`).
  - `GAMECAST_ESPN_EVENT`: id do jogo na ESPN. Sem ele, vale o jogo do Featured Team em andamento ou o próximo.
  - `GAMECAST_ESPN_LEAGUE`: `nfl` (padrão). `college-football` serve para testar com jogos ao vivo de sábado,
    desde que as siglas tenham até 3 letras.
  - Cada resposta da ESPN que muda é gravada em `data/recordings/<evento>/` (gzip).

`GAMECAST_SYNC_INTERVAL` é o intervalo entre consultas ao Provider (segundos, padrão 3; `scripts/live.ps1` usa 4).

- Cada mudança grava um snapshot em `data/game_state.json` (Game State + Control Mode), recarregado ao reiniciar o servidor.
- Em AUTO o Provider controla o jogo; em MANUAL, só o painel (ver `docs/adr/0002`). Sem snapshot, o modo inicial é
  `GAMECAST_CONTROL_MODE` (`AUTO` por padrão). Para uma live só com placar manual, use `GAMECAST_CONTROL_MODE=MANUAL`.
- As estatísticas dos QBs vêm só do Provider: em MANUAL elas saem do Gamecast (ver `docs/adr/0004`).
- O lado do campo (Field Direction) é do operador nos dois modos: "Inverter lado do campo" funciona também em AUTO
  (ver `docs/adr/0006`).

## Executável para Windows

Para quem vai operar a live sem o código: um `Gamecast.exe` que sobe o servidor com ESPN em AUTO e abre o painel
no navegador. O snapshot e as gravações ficam numa pasta `dados` ao lado do `.exe`.

```powershell
.\scripts\build.ps1
```

Gera `dist\Gamecast-<versão>.zip` (executável + `LEIA-ME.txt`, o guia do operador). O build acontece fora do
OneDrive (`%LOCALAPPDATA%\gamecast-build`), que trava os arquivos gerados. Para rodar o mesmo lançador pelo código:
`uv run python -m app.launcher`. Com `GAMECAST_OPEN_BROWSER=0` o painel não abre sozinho.

No primeiro uso, o Windows SmartScreen avisa que o executável não é assinado: "Mais informações" → "Executar assim
mesmo".

## Desenvolvimento

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```
