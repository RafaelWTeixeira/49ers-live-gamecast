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
uv run uvicorn app.main:app --reload
```

- `http://localhost:8000/` — health check
- `http://localhost:8000/api/game` — Game State atual (JSON); `/docs` lista a API
- `http://localhost:8000/control` — painel do operador: Control Mode (AUTO/MANUAL), edição do jogo, eventos, desfazer
- `ws://localhost:8000/ws/game` — envia o Game State ao conectar e, depois, cada mudança (`GAME_STATE`) e cada Game Event (`GAME_EVENT`)
- `http://localhost:8000/overlay` — o Gamecast (16:9, se ajusta à janela), compartilhado como tela no StreamYard

## Dados

- O jogo vem do `MockProvider`, que reproduz `mock/plays.json` em loop a partir de `mock/game.json`.
  O intervalo entre jogadas é `GAMECAST_SYNC_INTERVAL` (segundos, padrão 3).
- Cada mudança grava um snapshot em `data/game_state.json` (Game State + Control Mode), recarregado ao reiniciar o servidor.
- Em AUTO o Provider controla o jogo; em MANUAL, só o painel (ver `docs/adr/0002`). Sem snapshot, o modo inicial é
  `GAMECAST_CONTROL_MODE` (`AUTO` por padrão). Para uma live só com placar manual, use `GAMECAST_CONTROL_MODE=MANUAL`.
- As estatísticas dos QBs vêm só do Provider: em MANUAL elas saem do Gamecast (ver `docs/adr/0004`).

## Desenvolvimento

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```
