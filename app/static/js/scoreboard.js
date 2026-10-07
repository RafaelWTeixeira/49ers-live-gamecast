const PHASE_LABELS = {
  PRE_GAME: "Pré-jogo",
  LIVE: "Ao vivo",
  HALFTIME: "Intervalo",
  FINAL: "Final",
};

export function quarterLabel(quarter) {
  return quarter >= 5 ? "OT" : `Q${quarter}`;
}

// Placar anterior de cada lado: quando sobe, o número salta e a caixa do time pisca.
const lastScores = {};

function bind(root, name) {
  return root.querySelector(`[data-bind="${name}"]`);
}

// Recomeça a animação da classe, mesmo que ela já esteja aplicada.
function replay(el, className) {
  el.classList.remove(className);
  void el.offsetWidth;
  el.classList.add(className);
}

function renderTeam(el, team, side, hasPossession) {
  bind(el, "abbr").textContent = team.abbr;
  bind(el, "name").textContent = team.name;
  bind(el, "score").textContent = team.score;
  el.classList.toggle("has-possession", hasPossession);

  if (lastScores[side] !== undefined && team.score > lastScores[side]) {
    replay(bind(el, "score"), "score-pop");
    replay(el, "is-scoring");
  }
  lastScores[side] = team.score;
}

export function renderScoreboard(root, state) {
  for (const side of ["featured", "opponent"]) {
    const el = root.querySelector(`[data-team="${side}"]`);
    renderTeam(el, state[side], side, state.possession === side);
  }

  const phase = bind(root, "phase");
  phase.textContent = PHASE_LABELS[state.phase];
  phase.dataset.phase = state.phase;

  bind(root, "quarter").textContent = quarterLabel(state.quarter);
  bind(root, "clock").textContent = state.clock;
}
