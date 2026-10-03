// Aviso simples de Game Event. As animações entram numa versão própria.
const CALLOUT_DURATION_MS = 4000;

const EVENT_LABELS = {
  TOUCHDOWN: { title: "Touchdown", points: 6 },
  FIELD_GOAL: { title: "Field Goal", points: 3 },
  SAFETY: { title: "Safety", points: 2 },
  EXTRA_POINT: { title: "Extra Point", points: 1 },
  TWO_POINT_CONVERSION: { title: "Conversão de 2", points: 2 },
  TURNOVER: { title: "Turnover" },
  FLAG: { title: "Flag on the play" },
  TIMEOUT: { title: "Timeout" },
};

let hideTimer = null;

export function showEvent(calloutEl, event, state) {
  const label = EVENT_LABELS[event.kind];
  if (!label) return;

  const team = event.side ? state?.[event.side] : null;
  calloutEl.querySelector('[data-bind="event-title"]').textContent = label.title;
  calloutEl.querySelector('[data-bind="event-team"]').textContent = team ? team.name : "";
  calloutEl.querySelector('[data-bind="event-points"]').textContent = label.points
    ? `+${label.points} ${label.points === 1 ? "ponto" : "pontos"}`
    : "";
  calloutEl.dataset.side = event.side ?? "";
  calloutEl.hidden = false;

  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    calloutEl.hidden = true;
  }, CALLOUT_DURATION_MS);
}
