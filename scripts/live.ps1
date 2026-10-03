# Sobe o Gamecast para uma live: dados da ESPN, sem --reload (docs/STREAMYARD.md).
# Sem GAMECAST_ESPN_EVENT, usa o jogo do 49ers em andamento ou o próximo.
$env:GAMECAST_PROVIDER = "espn"
$env:GAMECAST_SYNC_INTERVAL = "4"
uv run uvicorn app.main:app
