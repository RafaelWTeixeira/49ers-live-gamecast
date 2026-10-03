import { renderField } from "./field.js";
import { renderScoreboard } from "./scoreboard.js";

// Até o WebSocket chegar (v0.5), o overlay consulta o backend periodicamente.
const POLL_INTERVAL_MS = 1000;

const root = document.querySelector(".overlay");

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
  root.style.setProperty("--opp-primary", state.opponent.primary_color);
  root.style.setProperty("--opp-secondary", state.opponent.secondary_color);

  renderScoreboard(root, state);
  renderField(root.querySelector(".field"), state);
  renderSituation(state);
  renderLastPlay(state);
}

async function loadGame() {
  const response = await fetch("/api/game");
  if (!response.ok) {
    throw new Error(`GET /api/game respondeu ${response.status}`);
  }
  return response.json();
}

async function refresh() {
  try {
    render(await loadGame());
  } catch (error) {
    console.error("Falha ao carregar o Game State:", error);
  }
}

refresh();
setInterval(refresh, POLL_INTERVAL_MS);
