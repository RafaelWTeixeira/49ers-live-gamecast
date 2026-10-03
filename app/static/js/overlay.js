import { showEvent } from "./events.js";
import { renderField } from "./field.js";
import { renderQuarterbacks } from "./quarterbacks.js";
import { renderScoreboard } from "./scoreboard.js";
import { connectGameUpdates } from "./websocket.js";

const root = document.querySelector(".overlay");
let currentState = null;

function bind(name) {
  return root.querySelector(`[data-bind="${name}"]`);
}

function ordinal(n) {
  return { 1: "1st", 2: "2nd", 3: "3rd", 4: "4th" }[n];
}

function renderSituation(state) {
  const team = state[state.possession];
  root.classList.toggle("no-possession", !team);
  if (!team) return;

  bind("possession").textContent = `${team.abbr} com a bola`;
  bind("down").textContent = `${ordinal(state.down)} & ${state.goal_to_go ? "Goal" : state.distance}`;
  bind("spot").textContent = state.field_position_label;
}

function renderLastPlay(state) {
  const play = state.last_play;
  bind("last-play").textContent = play ? play.description : "—";

  const yards = play?.yards;
  bind("last-play-yards").textContent =
    yards === null || yards === undefined ? "" : `${yards > 0 ? "+" : ""}${yards} jardas`;
}

export function render(state) {
  currentState = state;
  root.style.setProperty("--opp-primary", state.opponent.primary_color);
  root.style.setProperty("--opp-secondary", state.opponent.secondary_color);

  renderScoreboard(root, state);
  renderQuarterbacks(root, state);
  renderField(root.querySelector(".field"), state);
  renderSituation(state);
  renderLastPlay(state);
}

// Sem conexão, o overlay mantém o último estado na tela: nada de aviso de erro na live.
connectGameUpdates({
  onState: render,
  onEvent: (event) => showEvent(root.querySelector(".event-callout"), event, currentState),
  onStatus: (status) => {
    if (status === "disconnected") console.warn("Gamecast desconectado; tentando reconectar…");
  },
});
