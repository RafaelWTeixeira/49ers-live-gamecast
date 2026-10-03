import { connectGameUpdates } from "./websocket.js";

const STATUS_POLL_MS = 3000;
const TOAST_MS = 3500;

const EVENT_NAMES = {
  TOUCHDOWN: "Touchdown",
  FIELD_GOAL: "Field goal",
  EXTRA_POINT: "Extra point",
  TWO_POINT_CONVERSION: "Conversão de 2",
  SAFETY: "Safety",
  TURNOVER: "Turnover",
  TIMEOUT: "Timeout",
  FLAG: "Flag",
};

const form = document.querySelector('[data-form="game"]');
const fields = form.elements;

let currentState = null;
let mode = null;
let dirty = false;

function bindAll(name) {
  return document.querySelectorAll(`[data-bind="${name}"]`);
}

function bindOne(name) {
  return document.querySelector(`[data-bind="${name}"]`);
}

// ---------- Comunicação com o backend ----------

function errorMessage(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc.slice(1).join(".") || "jogo"}: ${d.msg}`).join("; ");
  }
  return `Erro ${status}`;
}

async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(data, response.status));
  return data;
}

let toastTimer = null;

function toast(message, kind = "ok") {
  const el = bindOne("toast");
  el.textContent = message;
  el.dataset.kind = kind;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), TOAST_MS);
}

async function run(action, successMessage) {
  try {
    await action();
    if (successMessage) toast(successMessage);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    refreshControl();
  }
}

// ---------- Posição da bola: Yardline <-> "campo de X, jarda N" ----------

function toSpot(yardline) {
  if (yardline === null) return { side: "featured", yard: "" };
  return yardline <= 50
    ? { side: "featured", yard: yardline }
    : { side: "opponent", yard: 100 - yardline };
}

function toYardline(side, yard) {
  return side === "featured" ? yard : 100 - yard;
}

// ---------- Formulário ----------

function setDirty(value) {
  dirty = value;
  bindOne("dirty-note").hidden = !value;
}

function renderTeams(state) {
  for (const side of ["featured", "opponent"]) {
    const abbr = state[side].abbr;
    bindAll(`${side}-abbr`).forEach((el) => (el.textContent = abbr));
    bindAll(`${side}-option`).forEach((el) => (el.textContent = abbr));
  }
  const where = state.field_direction === "left" ? "à esquerda" : "à direita";
  bindOne("field-direction").textContent = `${state.featured.abbr} defende ${where}`;
}

function fillForm(state) {
  fields.featured_score.value = state.featured.score;
  fields.opponent_score.value = state.opponent.score;
  fields.phase.value = state.phase;
  fields.quarter.value = String(state.quarter);
  fields.clock.value = state.clock;
  fields.possession.value = state.possession ?? "";
  fields.down.value = state.down ?? "";
  fields.distance.value = state.distance ?? "";

  const spot = toSpot(state.yardline);
  fields.spot_side.value = spot.side;
  fields.spot_yard.value = spot.yard;

  fields.last_play_description.value = state.last_play?.description ?? "";
  fields.last_play_yards.value = state.last_play?.yards ?? "";
  setDirty(false);
}

function numberOrNull(value) {
  return value === "" ? null : Number(value);
}

// Monta os campos de entrada do Game State (sem os derivados, que o backend calcula).
function readForm() {
  const yard = numberOrNull(fields.spot_yard.value);
  const description = fields.last_play_description.value.trim();
  return {
    phase: fields.phase.value,
    quarter: Number(fields.quarter.value),
    clock: fields.clock.value.trim(),
    featured: { ...currentState.featured, score: Number(fields.featured_score.value) },
    opponent: { ...currentState.opponent, score: Number(fields.opponent_score.value) },
    possession: fields.possession.value || null,
    yardline: yard === null ? null : toYardline(fields.spot_side.value, yard),
    down: numberOrNull(fields.down.value),
    distance: numberOrNull(fields.distance.value),
    opening_field_direction: currentState.opening_field_direction,
    last_play: description
      ? { description, yards: numberOrNull(fields.last_play_yards.value) }
      : null,
  };
}

function onState(state) {
  currentState = state;
  renderTeams(state);
  // Não atropela o que o operador está digitando.
  if (!dirty) fillForm(state);
}

// ---------- Control Mode e status ----------

function renderControl(status) {
  mode = status.mode;
  document.body.dataset.mode = mode;
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  });
  document.querySelectorAll("[data-manual-only]").forEach((el) => {
    el.disabled = mode !== "MANUAL";
  });
  document.querySelector('[data-action="undo"]').disabled = mode !== "MANUAL" || !status.can_undo;

  bindOne("mode-hint").textContent =
    mode === "MANUAL"
      ? "Modo MANUAL: você controla o jogo. O Provider está sendo ignorado."
      : "Modo AUTO: o Provider controla o jogo. Mude para MANUAL para editar.";

  const pill = document.querySelector('[data-status="provider"]');
  const { name, healthy, last_error: lastError, last_success_at: lastSuccess } = status.provider;
  pill.dataset.state = healthy ? "ok" : lastError ? "error" : "";
  pill.textContent = `${name}: ${healthy ? "OK" : lastError ? "falhando" : "aguardando"}`;
  pill.title = lastError ?? (lastSuccess ? `Última resposta: ${lastSuccess}` : "");

  if (mode !== "MANUAL" && dirty && currentState) fillForm(currentState);
}

async function refreshControl() {
  try {
    renderControl(await api("GET", "/api/control"));
  } catch (error) {
    console.error("Falha ao ler o status do controle:", error);
  }
}

function requireCleanForm() {
  if (!dirty) return true;
  toast("Envie ou descarte as alterações do formulário antes.", "error");
  return false;
}

// ---------- Ações ----------

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.mode;
    if (target === mode) return;
    if (target === "AUTO" && dirty && !confirm("Descartar as alterações não enviadas?")) return;
    run(
      () => api("PUT", "/api/control/mode", { mode: target }),
      target === "MANUAL" ? "Modo MANUAL: você controla o jogo." : "Modo AUTO: o Provider assumiu.",
    );
  });
});

form.addEventListener("input", () => setDirty(true));

form.addEventListener("submit", (submit) => {
  submit.preventDefault();
  if (!currentState || !form.reportValidity()) return;
  run(async () => {
    await api("PUT", "/api/control/game", readForm());
    setDirty(false);
  }, "Jogo atualizado.");
});

document.querySelector('[data-action="discard"]').addEventListener("click", () => {
  if (currentState) fillForm(currentState);
});

document.querySelectorAll("[data-event]").forEach((button) => {
  button.addEventListener("click", () => {
    if (!requireCleanForm()) return;
    const side = button.closest("[data-side]").dataset.side;
    const kind = button.dataset.event;
    const team = currentState?.[side]?.abbr ?? side;
    run(
      () => api("POST", "/api/control/events", { kind, side }),
      `${EVENT_NAMES[kind]} ${team} registrado.`,
    );
  });
});

document.querySelector('[data-action="undo"]').addEventListener("click", () => {
  if (!requireCleanForm()) return;
  run(() => api("POST", "/api/control/undo"), "Última alteração desfeita.");
});

document.querySelector('[data-action="flip-field"]').addEventListener("click", () => {
  if (mode === "MANUAL" && !requireCleanForm()) return;
  run(() => api("POST", "/api/control/flip-field"), "Lado do campo invertido.");
});

// ---------- Início ----------

const connectionPill = document.querySelector('[data-status="connection"]');

connectGameUpdates({
  onState,
  onEvent: () => {},
  onStatus: (status) => {
    connectionPill.dataset.state = status === "connected" ? "ok" : "error";
    connectionPill.textContent = status === "connected" ? "Conectado" : "Sem conexão";
  },
});

refreshControl();
setInterval(refreshControl, STATUS_POLL_MS);
