function bind(root, name) {
  return root.querySelector(`[data-bind="${name}"]`);
}

function renderQuarterback(el, qb) {
  // Sem QB informado, o card some mas guarda o lugar, para o outro não mudar de posição.
  el.classList.toggle("is-empty", !qb);
  if (!qb) return;

  bind(el, "name").textContent = qb.name;
  bind(el, "comp-att").textContent = `${qb.completions}/${qb.attempts}`;
  bind(el, "yards").textContent = qb.yards;
  bind(el, "touchdowns").textContent = qb.touchdowns;
  bind(el, "interceptions").textContent = qb.interceptions;
  bind(el, "rating").textContent = qb.passer_rating === null ? "—" : qb.passer_rating.toFixed(1);
}

export function renderQuarterbacks(root, state) {
  const row = root.querySelector(".quarterbacks");
  // Sem nenhum QB, a faixa inteira sai e o campo ocupa o espaço.
  row.hidden = !state.featured.quarterback && !state.opponent.quarterback;

  for (const side of ["featured", "opponent"]) {
    renderQuarterback(row.querySelector(`[data-qb="${side}"]`), state[side].quarterback);
  }
}
