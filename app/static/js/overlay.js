import { DEMO_STATES, SAMPLE_STATE } from "./demo.js";
import { renderField } from "./field.js";
import { renderScoreboard } from "./scoreboard.js";

const DEMO_INTERVAL_MS = 3000;

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
  const goalToGo = state.line_to_gain >= 100 || state.line_to_gain <= 0;
  bind("down").textContent = `${ordinal(state.down)} & ${goalToGo ? "Goal" : state.distance}`;
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

// ?demo percorre os estados de exemplo; ?demo=N fixa o estado N.
const demo = new URLSearchParams(location.search).get("demo");

if (demo === null) {
  render(SAMPLE_STATE);
} else if (demo !== "") {
  render(DEMO_STATES[Number(demo)]);
} else {
  let index = 0;
  render(DEMO_STATES[index]);
  setInterval(() => {
    index = (index + 1) % DEMO_STATES.length;
    render(DEMO_STATES[index]);
  }, DEMO_INTERVAL_MS);
}
