# 49ers Live Gamecast

Overlay gráfico 1920×1080 para lives de jogos do San Francisco 49ers. A página é renderizada no OBS (Browser Source) e enviada ao StreamYard/YouTube.

- Plano e roadmap: [docs/PLANO.md](docs/PLANO.md)
- Linguagem do domínio: [GLOSSARY.md](GLOSSARY.md)
- Decisões de arquitetura: [docs/adr/](docs/adr/)

## Rodando

Requer [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run uvicorn app.main:app --reload
```

- `http://localhost:8000/` — health check
- `http://localhost:8000/api/game` — Game State atual (JSON); `/docs` lista a API
- `http://localhost:8000/control` — painel do operador: Control Mode (AUTO/MANUAL), edição do jogo, eventos, desfazer
- `ws://localhost:8000/ws/game` — envia o Game State ao conectar e, depois, cada mudança (`GAME_STATE`) e cada Game Event (`GAME_EVENT`)
- `http://localhost:8000/overlay` — overlay (usar no OBS como Browser Source 1920×1080)
  - `?preview` — fundo xadrez para enxergar as áreas transparentes

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
