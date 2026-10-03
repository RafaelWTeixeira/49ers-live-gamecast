const PHASE_LABELS = {
  PRE_GAME: "Pré-jogo",
  LIVE: "Ao vivo",
  HALFTIME: "Intervalo",
  FINAL: "Final",
};

export function quarterLabel(quarter) {
  return quarter >= 5 ? "OT" : `Q${quarter}`;
}

function bind(root, name) {
  return root.querySelector(`[data-bind="${name}"]`);
}

function renderTeam(el, team, hasPossession) {
  bind(el, "abbr").textContent = team.abbr;
  bind(el, "name").textContent = team.name;
  bind(el, "score").textContent = team.score;
  el.classList.toggle("has-possession", hasPossession);
}

export function renderScoreboard(root, state) {
  for (const side of ["featured", "opponent"]) {
    renderTeam(root.querySelector(`[data-team="${side}"]`), state[side], state.possession === side);
  }

  const phase = bind(root, "phase");
  phase.textContent = PHASE_LABELS[state.phase];
  phase.dataset.phase = state.phase;

  bind(root, "quarter").textContent = quarterLabel(state.quarter);
  bind(root, "clock").textContent = state.clock;
}
