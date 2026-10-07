"""Ponto de entrada do Gamecast.exe: sobe o servidor com os padrões de uma live e abre o painel.

Padrões (cada um pode ser trocado pela variável de ambiente correspondente, ver README):
- dados da ESPN, consultados a cada 4s;
- snapshot e gravações numa pasta "dados" ao lado do .exe;
- a primeira porta livre a partir da 8000;
- o painel abre sozinho no navegador (GAMECAST_OPEN_BROWSER=0 desliga).

Também roda pelo código-fonte: `uv run python -m app.launcher` (dados em data/).
"""

import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
FIRST_PORT = 8000
PORT_ATTEMPTS = 20
READY_TIMEOUT_SECONDS = 20


def is_executable() -> bool:
    return getattr(sys, "frozen", False)


def data_dir() -> Path:
    if is_executable():
        return Path(sys.executable).parent / "dados"
    return Path(__file__).parent.parent / "data"


def configure_defaults() -> None:
    os.environ.setdefault("GAMECAST_PROVIDER", "espn")
    os.environ.setdefault("GAMECAST_SYNC_INTERVAL", "4")
    os.environ.setdefault("GAMECAST_DATA_DIR", str(data_dir()))


def free_port() -> int:
    for port in range(FIRST_PORT, FIRST_PORT + PORT_ATTEMPTS):
        with socket.socket() as probe:
            try:
                probe.bind((HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"nenhuma porta livre entre {FIRST_PORT} e {FIRST_PORT + PORT_ATTEMPTS - 1}")


def open_panel_when_ready(base_url: str) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{base_url}/", timeout=1)
        except OSError:
            time.sleep(0.2)
            continue
        webbrowser.open(f"{base_url}/control")
        return


def main() -> None:
    configure_defaults()
    # Só depois de configurar: app.dependencies lê o ambiente ao ser importado.
    import uvicorn

    from app.main import app

    port = free_port()
    base_url = f"http://localhost:{port}"
    print(
        "\n  49ers Live Gamecast\n"
        f"\n  Painel de controle:  {base_url}/control"
        f"\n  Gamecast (overlay):  {base_url}/overlay"
        f"\n  Dados:               {os.environ['GAMECAST_DATA_DIR']}"
        "\n\n  O painel abre sozinho no navegador. Feche esta janela para encerrar.\n",
        flush=True,
    )
    if os.getenv("GAMECAST_OPEN_BROWSER", "1") != "0":
        threading.Thread(target=open_panel_when_ready, args=(base_url,), daemon=True).start()
    uvicorn.run(app, host=HOST, port=port, log_level="warning", access_log=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        # No executável, a janela fecharia na hora: deixa o erro na tela para ser lido.
        traceback.print_exc()
        input("\nO Gamecast não conseguiu iniciar. Pressione Enter para fechar.")
