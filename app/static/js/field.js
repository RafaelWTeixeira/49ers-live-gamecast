// Converte a Yardline (0 = goal line do Featured Team) em % da largura do campo na tela.
export function toScreenPercent(yardline, fieldDirection) {
  return fieldDirection === "left" ? yardline : 100 - yardline;
}

// O Featured Team sempre ataca rumo à Yardline 100; o Opponent, rumo à 0.
export function isAttackingRight(possession, fieldDirection) {
  return (possession === "featured") === (fieldDirection === "left");
}

function placeAt(el, yardline, fieldDirection) {
  const visible = yardline !== null && yardline !== undefined;
  el.hidden = !visible;
  if (visible) {
    el.style.setProperty("--y", toScreenPercent(yardline, fieldDirection));
  }
}

function renderEndzone(el, team, side) {
  el.textContent = team.name;
  el.classList.toggle("endzone--featured", side === "featured");
  el.classList.toggle("endzone--opponent", side === "opponent");
}

export function renderField(fieldEl, state) {
  const direction = state.field_direction;
  const [leftSide, rightSide] =
    direction === "left" ? ["featured", "opponent"] : ["opponent", "featured"];

  renderEndzone(fieldEl.querySelector('[data-endzone="left"]'), state[leftSide], leftSide);
  renderEndzone(fieldEl.querySelector('[data-endzone="right"]'), state[rightSide], rightSide);

  const hasPossession = state.possession !== null;
  const ball = fieldEl.querySelector('[data-marker="ball"]');

  placeAt(ball, hasPossession ? state.yardline : null, direction);
  placeAt(fieldEl.querySelector('[data-marker="los"]'), hasPossession ? state.yardline : null, direction);
  placeAt(
    fieldEl.querySelector('[data-marker="first-down"]'),
    hasPossession ? state.line_to_gain : null,
    direction,
  );

  const attackingRight = isAttackingRight(state.possession, direction);
  ball.classList.toggle("ball--attacking-right", hasPossession && attackingRight);
  ball.classList.toggle("ball--attacking-left", hasPossession && !attackingRight);
}
