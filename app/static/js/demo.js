// Estados de exemplo já serializados (com os campos derivados). Saem quando o MockProvider chegar (v0.4).

const SF = { abbr: "SF", name: "49ers" };
const DEN = { abbr: "DEN", name: "Broncos", primary_color: "#FB4F14", secondary_color: "#0A2343" };

function state({ sf = 0, den = 0, ...rest }) {
  return {
    phase: "LIVE",
    quarter: 1,
    clock: "15:00",
    featured: { ...SF, score: sf },
    opponent: { ...DEN, score: den },
    possession: null,
    field_direction: "left",
    yardline: null,
    line_to_gain: null,
    field_position_label: null,
    goal_to_go: false,
    down: null,
    distance: null,
    last_play: null,
    ...rest,
  };
}

function drive(possession, down, distance, yardline, label) {
  const lineToGain = possession === "featured" ? yardline + distance : yardline - distance;
  const goalToGo = lineToGain === 0 || lineToGain === 100;
  return {
    possession, down, distance, yardline,
    line_to_gain: lineToGain, goal_to_go: goalToGo, field_position_label: label,
  };
}

export const DEMO_STATES = [
  state({ phase: "PRE_GAME" }),
  state({
    ...drive("featured", 1, 10, 25, "SF 25"),
    last_play: { description: "Kickoff — touchback", yards: null },
  }),
  state({
    clock: "14:22",
    ...drive("featured", 2, 4, 31, "SF 31"),
    last_play: { description: "McCaffrey rush up the middle for 6 yards", yards: 6 },
  }),
  state({
    clock: "13:51",
    ...drive("featured", 1, 10, 49, "SF 49"),
    last_play: { description: "Purdy pass to Kittle for 18 yards", yards: 18 },
  }),
  state({
    quarter: 2, clock: "06:10", sf: 7, den: 3, field_direction: "right",
    ...drive("opponent", 1, 10, 80, "DEN 20"),
    last_play: { description: "Kickoff — touchback", yards: null },
  }),
  state({
    quarter: 2, clock: "05:31", sf: 7, den: 3, field_direction: "right",
    ...drive("opponent", 3, 2, 72, "DEN 28"),
    last_play: { description: "Nix pass to Sutton for 8 yards", yards: 8 },
  }),
  state({ phase: "HALFTIME", quarter: 2, clock: "00:00", sf: 10, den: 10, field_direction: "right" }),
  state({
    quarter: 3, clock: "08:42", sf: 17, den: 10,
    ...drive("featured", 2, 6, 66, "DEN 34"),
    last_play: { description: "Purdy pass to Kittle for 8 yards", yards: 8 },
  }),
  state({
    quarter: 4, clock: "02:10", sf: 20, den: 13, field_direction: "right",
    ...drive("featured", 1, 8, 92, "DEN 8"),
    last_play: { description: "Aiyuk 31-yard catch along the sideline", yards: 31 },
  }),
  state({ phase: "FINAL", quarter: 4, clock: "00:00", sf: 27, den: 13, field_direction: "right" }),
];

