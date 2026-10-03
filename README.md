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
- `http://localhost:8000/overlay` — overlay (usar no OBS como Browser Source 1920×1080)
  - `?preview` — fundo xadrez para enxergar as áreas transparentes

## Dados

- O jogo vem do `MockProvider`, que reproduz `mock/plays.json` em loop a partir de `mock/game.json`.
  O intervalo entre jogadas é `GAMECAST_SYNC_INTERVAL` (segundos, padrão 3).
- Cada mudança grava um snapshot em `data/game_state.json`, recarregado ao reiniciar o servidor.

## Desenvolvimento

```sh
uv run pytest
uv run ruff check .
uv run ruff format .
```
