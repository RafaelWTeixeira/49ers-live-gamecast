const RETRY_START_MS = 1000;
const RETRY_MAX_MS = 5000;

// Conecta ao backend e reconecta sozinho se a conexão cair (ex.: servidor reiniciado).
// Ao (re)conectar, o backend envia o Game State atual, então nada se perde.
export function connectGameUpdates({ onState, onEvent, onStatus = () => {} }) {
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/game`;
  let retryMs = RETRY_START_MS;

  function connect() {
    const socket = new WebSocket(url);

    socket.addEventListener("open", () => {
      retryMs = RETRY_START_MS;
      onStatus("connected");
    });

    socket.addEventListener("message", (message) => {
      const data = JSON.parse(message.data);
      if (data.type === "GAME_STATE") onState(data.game);
      else if (data.type === "GAME_EVENT") onEvent(data.event);
    });

    socket.addEventListener("close", () => {
      onStatus("disconnected");
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, RETRY_MAX_MS);
    });
  }

  connect();
}
