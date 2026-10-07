import { createEventPresenter, EVENT_KINDS, eventPoints } from "./events.js";
import { renderField } from "./field.js";
import { renderQuarterbacks } from "./quarterbacks.js";
import { renderScoreboard } from "./scoreboard.js";
import { connectGameUpdates } from "./websocket.js";

const root = document.querySelector(".overlay");
const events = createEventPresenter(root);
let currentState = null;

const CANVAS_WIDTH = 1920;
const CANVAS_HEIGHT = 1080;

// Encaixa o canvas de 1920×1080 na janela compartilhada, mantendo 16:9.
function fitToWindow() {
  const scale = Math.min(innerWidth / CANVAS_WIDTH, innerHeight / CANVAS_HEIGHT);
  root.style.setProperty("--scale", scale);
}

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

// /overlay?demo repete as animações de todos os Game Events (ou ?demo=TOUCHDOWN, só uma),
// alternando os times, para conferir no StreamYard antes da live. Pontos sobem só na tela.
const DEMO_GAP_MS = 1200;

function startDemo(only) {
  const kinds = only ? [only] : EVENT_KINDS;
  let step = 0;

  function next() {
    if (!currentState) return setTimeout(next, 500);
    const kind = kinds[step % kinds.length];
    const side = step % 2 === 0 ? "featured" : "opponent";
    step += 1;
    const points = eventPoints(kind);
    if (points) {
      const team = currentState[side];
      render({ ...currentState, [side]: { ...team, score: team.score + points } });
    }
    events.show({ kind, side }, currentState);
    setTimeout(next, DEMO_GAP_MS + (kind === "TOUCHDOWN" ? 5600 : 4000));
  }

  next();
}

fitToWindow();
addEventListener("resize", fitToWindow);

const demo = new URLSearchParams(location.search).get("demo");
if (demo !== null) startDemo(demo.toUpperCase() || null);

// Sem conexão, o overlay mantém o último estado na tela: nada de aviso de erro na live.
connectGameUpdates({
  onState: render,
  onEvent: (event) => events.show(event, currentState),
  onStatus: (status) => {
    if (status === "disconnected") console.warn("Gamecast desconectado; tentando reconectar…");
  },
});
