// Stone Age AI — browser client.
// The server sends the full game state plus the list of legal actions for the
// human seat; every click maps to one of those action indices.

const RESOURCES = ["food", "wood", "stone", "clay", "gold"];
const SPEND = ["wood", "stone", "clay", "gold"];
const SPECTATE_DELAY_MS = 350;

let state = null;
let selectedLocation = null; // placement: location index chosen, waiting for worker count
let busy = false;
let spectateTimer = null;
let spectatePaused = false;

// ---------- helpers ----------

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

const $ = (id) => document.getElementById(id);

// Replace an element's children, flattening nested arrays and dropping false/null.
function fill(el, ...children) {
  el.replaceChildren(...children.flat(Infinity).filter((c) => c != null && c !== false)
    .map((c) => (c instanceof Node ? c : document.createTextNode(String(c)))));
}
const playerName = (i) => (state && i === state.human_seat ? "You" : `Player ${i + 1}`);
const swatch = (res) => h("span", { class: `swatch sw-${res}`, "aria-hidden": "true" });

async function api(path, body) {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

// ---------- actions ----------

async function newGame(seatValue) {
  stopSpectating();
  const human_seat = seatValue === "spectate" ? null : Number(seatValue);
  selectedLocation = null;
  setState(await api("/api/games", { human_seat }));
  if (human_seat === null) startSpectating();
}

async function play(actionIndex) {
  if (busy) return;
  busy = true;
  selectedLocation = null;
  try {
    setState(await api(`/api/games/${state.id}/move`, { action_index: actionIndex }));
  } catch (err) {
    alert(err.message);
  } finally {
    busy = false;
  }
}

function startSpectating() {
  spectatePaused = false;
  const tick = async () => {
    if (!state || state.finished || spectatePaused) return;
    setState(await api(`/api/games/${state.id}/advance`, { max_steps: 1 }));
    spectateTimer = setTimeout(tick, SPECTATE_DELAY_MS);
  };
  spectateTimer = setTimeout(tick, SPECTATE_DELAY_MS);
}

function stopSpectating() {
  clearTimeout(spectateTimer);
  spectateTimer = null;
}

function setState(next) {
  state = next;
  render();
}

// ---------- rendering ----------

function render() {
  $("empty").hidden = true;
  $("app").hidden = false;
  $("meta").textContent = `AI model: ${state.ai_model}`;
  renderStatus();
  renderBoard();
  renderPlayers();
  renderDecision();
  renderLog();
}

function renderStatus() {
  const turn = state.finished ? "Game over" : `${playerName(state.current_player)} to act`;
  fill($("status"), 
    h("span", {}, h("strong", {}, `Round ${state.round}`)),
    h("span", {}, turn),
    !state.finished && h("span", { class: "muted" }, `Phase: ${state.decision.phase}`),
    h("span", { class: "muted" }, `Starting player: ${playerName(state.first_player)}`),
  );
}

function legalFor(phase) {
  return state.decision.phase === phase ? state.legal_actions : [];
}

function placementsAt(locIndex) {
  return legalFor("placement").filter((a) => a.args.location === locIndex);
}

function pips(loc) {
  const out = [];
  loc.occupants.forEach((n, p) => {
    for (let i = 0; i < n; i++) out.push(h("span", { class: `pip pc-${p}`, title: playerName(p) }));
  });
  return h("div", { class: "pips" }, out);
}

function tile(loc, content) {
  if (!loc) return h("div", { class: "tile empty-slot" }, "Empty");
  const legal = placementsAt(loc.index).length > 0;
  const deciding = state.decision.location && state.decision.location.index === loc.index;
  const classes = ["tile", legal && "legal", selectedLocation === loc.index && "selected", deciding && "deciding"]
    .filter(Boolean).join(" ");
  const used = loc.occupants.reduce((a, b) => a + b, 0);
  const body = [
    h("div", { class: "title" }, content.title, h("span", { class: "cap" }, `${used}/${loc.capacity}`)),
    content.lines.map((l) => h("div", { class: "sub" }, l)),
    pips(loc),
  ];
  if (!legal) return h("div", { class: classes }, body);
  return h("button", {
    class: classes,
    type: "button",
    "aria-label": `Place workers on ${loc.label}`,
    onclick: () => { selectedLocation = loc.index; render(); },
  }, body);
}

function renderBoard() {
  const L = state.locations;
  fill($("gathering"), ...L.slice(3, 8).map((loc) => tile(loc, {
    title: [swatch(loc.resource), loc.label],
    lines: [`Supply ${loc.supply}`, `Dice total ÷ ${loc.divisor}`],
  })));

  const villageText = { Field: "+1 field (feeds 1/round)", Hut: "+1 person (needs 2)", "Tool Maker": "+1 tool" };
  fill($("village"), ...L.slice(0, 3).map((loc) => tile(loc, {
    title: [loc.label], lines: [villageText[loc.label] || ""],
  })));

  $("deck-count").textContent = `(${state.cards_in_deck} left in deck)`;
  fill($("cards"), ...L.slice(8, 12).map((loc) => tile(loc, loc && {
    title: [loc.label, h("span", { class: "tag" }, `cost ${loc.cost}`)],
    lines: [loc.effect, loc.scoring.text],
  })));

  fill($("buildings"), ...L.slice(12, 16).map((loc) => tile(loc, loc && {
    title: [loc.label, h("span", { class: "tag" }, `${loc.stack} below`)],
    lines: [loc.price.text, loc.price.vp != null ? `${loc.price.vp} VP` : "VP = resource values"],
  })));
}

function renderPlayers() {
  fill($("players"), ...state.players.map((p) => {
    const active = !state.finished && p.index === state.current_player;
    const tools = p.tools.map((t) => (t.ready ? `${t.value}` : `(${t.value})`)).join(" ");
    const culture = p.culture[0].length + p.culture[1].length;
    const toolText = p.tools.some((t) => t.value) ? tools : "none";
    const mult = Object.entries(p.multipliers).filter(([, v]) => v).map(([k, v]) => `${v}×${k}`).join(", ");
    return h("article", { class: `player${active ? " active" : ""}`, style: `--pcolor: var(--p${p.index})` },
      h("header", {},
        h("span", { class: "name" }, playerName(p.index), p.is_human ? "" : h("span", { class: "muted" }, " · AI")),
        h("span", { class: "vp", title: "Victory points" }, `${p.vp} VP`)),
      h("div", { class: "res-line" }, RESOURCES.map((r) =>
        h("span", { title: r }, swatch(r), p.resources[r]))),
      h("dl", {},
        h("dt", {}, "People"), h("dd", {}, `${p.available_workers} free / ${p.workers}`),
        h("dt", {}, "Fields"), h("dd", {}, p.fields),
        h("dt", {}, "Tools"), h("dd", { title: "Tools in brackets are used this round" },
          toolText + (p.one_use_tools.length ? ` · one-use ${p.one_use_tools.join(", ")}` : "")),
        h("dt", {}, "Buildings"), h("dd", {}, p.buildings),
        h("dt", {}, "Culture"), h("dd", {}, culture),
        h("dt", {}, "Bonuses"), h("dd", { title: "End-game VP multipliers from cards" }, mult || "none")));
  }));
}

function renderLog() {
  const items = state.log.slice().reverse().map((e) => e.player == null
    ? h("li", { class: "system" }, e.text)
    : h("li", {}, h("span", { class: "who", style: `color: var(--p${e.player})` }, playerName(e.player)), e.text));
  fill($("log"), ...items);
}

// ---------- decision panel ----------

function renderDecision() {
  const panel = $("decision");
  if (state.finished) return fill(panel, ...gameOverView());
  if (state.human_seat == null) return fill(panel, ...spectateView());
  if (!state.legal_actions.length) {
    return fill(panel, h("h3", {}, "Waiting…"), h("p", { class: "muted" }, `${playerName(state.current_player)} is thinking.`));
  }
  const views = { placement: placementView, tools: toolsView, buy: buyView, pay: payView, dice: diceView, choose2: choose2View };
  fill(panel, ...(views[state.decision.phase] || unknownView)());
}

function gameOverView() {
  if (state.error) return [h("h3", {}, "Game stopped"), h("p", { class: "error" }, state.error)];
  const names = (state.winners || []).map(playerName).join(" & ");
  const ranked = state.players.slice().sort((a, b) => b.vp - a.vp);
  return [
    h("h3", {}, "Game over"),
    h("p", { class: "winner" }, `${names} ${state.winners.length > 1 ? "win" : names === "You" ? "win" : "wins"}!`),
    state.end_reason && h("p", { class: "muted" }, state.end_reason),
    h("ol", {}, ranked.map((p) => h("li", {}, `${playerName(p.index)}: ${p.vp} VP`))),
    h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => newGame($("seat").value) }, "Play again")),
  ];
}

function spectateView() {
  return [
    h("h3", {}, "Spectating"),
    h("p", { class: "muted" }, "Four copies of the agent are playing each other."),
    h("div", { class: "row" },
      h("button", {
        class: "btn", onclick: () => {
          spectatePaused = !spectatePaused;
          if (spectatePaused) stopSpectating(); else startSpectating();
          renderDecision();
        },
      }, spectatePaused ? "Resume" : "Pause"),
      h("button", {
        class: "btn", disabled: !spectatePaused, onclick: async () => {
          setState(await api(`/api/games/${state.id}/advance`, { max_steps: 1 }));
        },
      }, "Step")),
  ];
}

function placementView() {
  const me = state.players[state.human_seat];
  const intro = h("p", {}, `Place your people. You have ${me.available_workers} left. Highlighted spaces are open.`);
  if (selectedLocation == null || !placementsAt(selectedLocation).length) {
    return [h("h3", {}, "Your turn: place people"), intro];
  }
  const loc = state.locations[selectedLocation];
  const options = placementsAt(selectedLocation).sort((a, b) => a.args.workers - b.args.workers);
  return [
    h("h3", {}, `Place on ${loc.label}`),
    h("p", { class: "muted" }, "How many people?"),
    h("div", { class: "row" },
      options.map((a) => h("button", { class: "btn primary", onclick: () => play(a.index) }, String(a.args.workers))),
      h("button", { class: "btn", onclick: () => { selectedLocation = null; render(); } }, "Cancel")),
  ];
}

function toolsView() {
  const d = state.decision;
  const me = state.players[state.human_seat];
  const legal = state.legal_actions;
  // A slot is usable if some legal combo sets it to 1.
  const usable = [0, 1, 2, 3, 4, 5, 6].filter((i) => legal.some((a) => a.args.tools[i]));
  const chosen = new Set();
  const value = (i) => (i < 4 ? me.tools[i].value : me.one_use_tools[i - 4]);

  const preview = h("p", {});
  const update = () => {
    const bonus = [...chosen].reduce((s, i) => s + value(i), 0);
    const total = d.dice_total + bonus;
    fill(preview, 
      `Dice ${d.dice_total}${bonus ? ` + tools ${bonus}` : ""} = ${total} → `,
      h("strong", {}, `${Math.floor(total / d.divisor)} ${d.resource}`));
  };
  update();

  const confirm = () => {
    const flags = [0, 1, 2, 3, 4, 5, 6].map((i) => (chosen.has(i) ? 1 : 0));
    const match = legal.find((a) => a.args.tools.every((f, i) => f === flags[i]));
    if (match) play(match.index);
  };

  return [
    h("h3", {}, `Gathering ${d.resource}`),
    preview,
    usable.length
      ? usable.map((i) => h("label", { class: "check" },
          h("input", { type: "checkbox", onchange: (e) => { e.target.checked ? chosen.add(i) : chosen.delete(i); update(); } }),
          i < 4 ? `Tool ${i + 1} (+${value(i)})` : `One-use tool (+${value(i)})`))
      : h("p", { class: "muted" }, "No tools available."),
    h("div", { class: "row" }, h("button", { class: "btn primary", onclick: confirm }, "Collect")),
  ];
}

function buyView() {
  const loc = state.decision.location;
  const buy = state.legal_actions.find((a) => a.args.buy);
  const skip = state.legal_actions.find((a) => !a.args.buy);
  const details = loc.kind === "card"
    ? [`Costs any ${loc.cost} resource${loc.cost > 1 ? "s" : ""}.`, loc.effect, loc.scoring.text]
    : [loc.price.text, loc.price.vp != null ? `Worth ${loc.price.vp} VP` : "Worth the value of resources paid"];
  return [
    h("h3", {}, `Buy ${loc.label}?`),
    details.filter(Boolean).map((t) => h("p", {}, t)),
    !buy && h("p", { class: "muted" }, "You can't afford it."),
    h("div", { class: "row" },
      h("button", { class: "btn primary", disabled: !buy, onclick: () => play(buy.index) }, "Buy"),
      h("button", { class: "btn", onclick: () => play(skip.index) }, "Pass")),
  ];
}

function payView() {
  const loc = state.decision.location;
  const me = state.players[state.human_seat];
  const legal = state.legal_actions;
  // Start from the first legal payment so "Pay" works immediately.
  const counts = Object.fromEntries(SPEND.map((r) => [r, legal[0].args.pay[r] || 0]));
  const key = (pay) => SPEND.map((r) => pay[r] || 0).join(",");
  const byKey = new Map(legal.map((a) => [key(a.args.pay), a]));

  const payBtn = h("button", { class: "btn primary", disabled: true }, "Pay");
  const summary = h("p", { class: "muted" });
  const outputs = {};
  const update = () => {
    SPEND.forEach((r) => { outputs[r].value = counts[r]; });
    const match = byKey.get(key(counts));
    payBtn.disabled = !match;
    payBtn.onclick = match ? () => play(match.index) : null;
    const total = SPEND.reduce((s, r) => s + counts[r], 0);
    summary.textContent = match ? `Valid payment (${total} resources).` : `${total} selected. Not a valid payment yet.`;
  };

  const steppers = SPEND.map((r) => {
    outputs[r] = h("output", {}, "0");
    const step = (delta) => () => {
      counts[r] = Math.max(0, Math.min(me.resources[r], counts[r] + delta));
      update();
    };
    return h("div", { class: "stepper" },
      h("span", {}, swatch(r), ` ${r} (have ${me.resources[r]})`),
      h("button", { class: "btn small", "aria-label": `Less ${r}`, onclick: step(-1) }, "−"),
      outputs[r],
      h("button", { class: "btn small", "aria-label": `More ${r}`, onclick: step(1) }, "+"));
  });

  const quick = legal.slice(0, 6).map((a) => h("button", {
    class: "btn small",
    onclick: () => play(a.index),
  }, SPEND.filter((r) => a.args.pay[r]).map((r) => `${a.args.pay[r]} ${r}`).join(" + ")));

  const rule = loc.kind === "card" ? `any ${loc.cost} resource${loc.cost > 1 ? "s" : ""}` : loc.price.text;
  queueMicrotask(update);
  return [
    h("h3", {}, `Pay for ${loc.label}`),
    h("p", {}, `Required: ${rule}.`),
    steppers,
    summary,
    h("div", { class: "row" }, payBtn),
    legal.length > 1 && h("p", { class: "muted" }, "Or pick a suggestion:"),
    legal.length > 1 && h("div", { class: "row" }, quick),
  ];
}

function diceView() {
  return [
    h("h3", {}, "Pick a die"),
    h("p", { class: "muted" }, "Each player takes one die and gets its reward."),
    h("div", { class: "row" }, state.legal_actions.map((a) =>
      h("button", { class: "btn primary", onclick: () => play(a.index) }, `${a.args.die}: ${a.args.reward}`))),
  ];
}

function choose2View() {
  const select = () => h("select", {}, RESOURCES.map((r) => h("option", { value: r }, r)));
  const a = select();
  const b = select();
  a.value = "gold"; b.value = "gold";
  const take = () => {
    const match = state.legal_actions.find((x) => x.args.resources[0] === a.value && x.args.resources[1] === b.value);
    if (match) play(match.index);
  };
  return [
    h("h3", {}, "Take any 2 resources"),
    h("div", { class: "row" }, a, b, h("button", { class: "btn primary", onclick: take }, "Take")),
  ];
}

function unknownView() {
  return [
    h("h3", {}, `Phase: ${state.decision.phase}`),
    h("div", { class: "row" }, state.legal_actions.slice(0, 20).map((a) =>
      h("button", { class: "btn", onclick: () => play(a.index) }, `#${a.index}`))),
  ];
}

// ---------- boot ----------

$("new-game-form").addEventListener("submit", (e) => {
  e.preventDefault();
  newGame($("seat").value).catch((err) => alert(err.message));
});
