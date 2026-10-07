// Game Events animados. Cada tipo tem um estilo (events.css); os eventos entram numa fila e
// aparecem um de cada vez, para um não atropelar o outro.
const EVENTS = {
  TOUCHDOWN: { title: "Touchdown", points: 6, style: "takeover", ms: 5600 },
  FIELD_GOAL: { title: "Field Goal", points: 3, style: "score", ms: 4000 },
  SAFETY: { title: "Safety", points: 2, style: "score", ms: 4000 },
  EXTRA_POINT: { title: "Extra Point", points: 1, style: "score", ms: 3000 },
  TWO_POINT_CONVERSION: { title: "Conversão de 2", points: 2, style: "score", ms: 3600 },
  TURNOVER: { title: "Turnover", style: "turnover", ms: 3800 },
  FLAG: { title: "Flag", style: "flag", ms: 3400 },
  TIMEOUT: { title: "Timeout", style: "timeout", ms: 2800 },
};

// Tempo da animação de saída (classe .is-leaving), descontado da duração de cada evento.
const EXIT_MS = 450;
// Numa enxurrada de eventos (ex.: reconexão), a fila não cresce além disso.
const MAX_QUEUE = 4;

function bind(el, name) {
  return el.querySelector(`[data-bind="${name}"]`);
}

function pointsText(points) {
  return points ? `+${points} ${points === 1 ? "ponto" : "pontos"}` : "";
}

function teamLine(definition, team) {
  if (definition.style === "turnover") return team ? `Posse: ${team.name}` : "";
  if (definition.style === "flag") return team ? `Falta: ${team.name}` : "Falta na jogada";
  return team ? team.name : "";
}

// Cada letra num span, para caírem uma de cada vez (--i é a ordem).
function letters(text) {
  return [...text.toUpperCase()].map((char, index) => {
    const span = document.createElement("span");
    span.textContent = char;
    span.style.setProperty("--i", index);
    return span;
  });
}

function fillTakeover(el, { definition, team }) {
  bind(el, "takeover-title").replaceChildren(...letters(definition.title));
  bind(el, "takeover-team").textContent = team ? team.name : "";
  bind(el, "takeover-points").textContent = definition.points ? `+${definition.points}` : "";
}

function fillCallout(el, { definition, team }) {
  bind(el, "event-title").textContent = definition.title;
  bind(el, "event-team").textContent = teamLine(definition, team);
  bind(el, "event-points").textContent = pointsText(definition.points);
}

export function createEventPresenter(root) {
  const callout = root.querySelector(".event-callout");
  const takeover = root.querySelector(".event-takeover");
  const queue = [];
  let playing = false;

  function playNext() {
    const item = queue.shift();
    playing = Boolean(item);
    if (!item) return;

    const isTakeover = item.definition.style === "takeover";
    const el = isTakeover ? takeover : callout;
    (isTakeover ? fillTakeover : fillCallout)(el, item);
    el.dataset.style = item.definition.style;
    el.dataset.side = item.side ?? "";
    el.hidden = false;

    setTimeout(() => el.classList.add("is-leaving"), item.definition.ms - EXIT_MS);
    setTimeout(() => {
      el.hidden = true;
      el.classList.remove("is-leaving");
      // Força o navegador a registrar o "escondido", para as animações recomeçarem no próximo.
      void el.offsetWidth;
      playNext();
    }, item.definition.ms);
  }

  function show(event, state) {
    const definition = EVENTS[event.kind];
    if (!definition) return;
    queue.push({ definition, side: event.side, team: event.side ? state?.[event.side] : null });
    // Se a fila encher, saem primeiro os eventos sem pontos: pontuação nunca se perde.
    while (queue.length > MAX_QUEUE) {
      const minor = queue.findIndex((item) => !item.definition.points);
      queue.splice(minor >= 0 ? minor : 0, 1);
    }
    if (!playing) playNext();
  }

  return { show };
}

export const EVENT_KINDS = Object.keys(EVENTS);

export function eventPoints(kind) {
  return EVENTS[kind]?.points ?? 0;
}
