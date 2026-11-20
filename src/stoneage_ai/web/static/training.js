// Stone Age AI — training page.
// Starts/stops training through /api/training and polls it for progress.

const POLL_MS = 3000;
const METRICS = [
  ["vp", "VP (average)"], ["vp_record", "VP record (best game)"],
  ["cards", "Cards bought"], ["buildings", "Buildings bought"], ["tools", "Tools"],
  ["people", "People"], ["wheat", "Wheat"],
  ["food", "Food collected"], ["wood", "Wood collected"], ["stone", "Stone collected"],
  ["clay", "Clay collected"], ["gold", "Gold collected"],
  ["rounds", "Rounds per game"], ["epsilon", "Exploration (ε)"], ["loss", "Loss"],
  ["games_per_sec", "Games per second"],
];
const OPPONENT_LABELS = { self: "Itself (the model being trained)", random: "Random moves" };

let checkpoints = [];       // compatible checkpoints from /api/models
let selectedRun = null;     // null = follow the active/newest run
let lastData = null;

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
const fill = (el, ...kids) => el.replaceChildren(...kids.flat(Infinity)
  .filter((c) => c != null && c !== false)
  .map((c) => (c instanceof Node ? c : document.createTextNode(String(c)))));

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

const fmt = (v, digits = 1) => (v == null || Number.isNaN(v) ? "–" : Number(v).toFixed(digits));
const fmtInt = (v) => (v == null ? "–" : Math.round(v).toLocaleString());
const fmtGames = (v) => (v >= 1000 ? `${+(v / 1000).toFixed(v % 1000 ? 1 : 0)}k` : String(v));
const runLabel = (name) => {
  const m = /^(\d{4})-(\d\d)-(\d\d)_(\d\d)-(\d\d)/.exec(name || "");
  return m ? `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}` : name;
};
function checkpointLabel(id) {
  if (id == null) return "new model";
  const c = checkpoints.find((x) => x.id === id);
  return c ? c.label : id;
}
const opponentLabel = (o) => OPPONENT_LABELS[o] || checkpointLabel(o);

// ---------- form ----------

function checkpointOptions(selected, short = false) {
  const byRun = new Map();
  for (const c of checkpoints) {
    const key = c.run ? `Run ${runLabel(c.run)}` : "Other";
    if (!byRun.has(key)) byRun.set(key, []);
    byRun.get(key).push(c);
  }
  return [...byRun].map(([group, items]) => h("optgroup", { label: group },
    items.map((c) => h("option", { value: c.id, selected: c.id === selected, title: c.id },
      short ? c.label.replace(/^Run [^·]+· /, "") : c.label))));
}

function renderForm() {
  const resume = $("resume");
  const prevResume = resume.value;
  if (checkpoints.length) fill(resume, checkpointOptions(prevResume || checkpoints[0].id));
  else fill(resume, h("option", { value: "" }, "No saved models yet"));
  const resumeRadio = document.querySelector('input[name="mode"][value="resume"]');
  resumeRadio.disabled = !checkpoints.length;
  if (!checkpoints.length) document.querySelector('input[name="mode"][value="new"]').checked = true;
  resume.disabled = !resumeRadio.checked;

  const box = $("opponents");
  const prev = [...box.querySelectorAll("select")].map((s) => s.value);
  const defaults = ["self", "self", "random"];
  fill(box, [0, 1, 2].map((i) => {
    const value = prev[i] || defaults[i];
    return h("label", { class: "opponent" }, h("span", {}, `Opponent ${i + 1}`),
      h("select", { id: `opp${i}` },
        h("option", { value: "self", selected: value === "self" }, OPPONENT_LABELS.self),
        h("option", { value: "random", selected: value === "random" }, OPPONENT_LABELS.random),
        checkpoints.length ? h("optgroup", { label: "Saved models (frozen)" }, checkpointOptions(value, true)
          .flatMap((g) => [...g.children].map((o) => {
            o.textContent = `${g.label.replace(/^Run /, "")} · ${o.textContent}`;
            return o;
          }))) : null));
  }));
}

async function loadCheckpoints() {
  try {
    const { models } = await api("/api/models");
    const next = models.filter((m) => m.kind !== "random" && m.compatible);
    const key = (list) => list.map((c) => c.id).join("|");
    if (key(next) === key(checkpoints) && $("opponents").children.length) return; // keep open menus
    checkpoints = next;
    renderForm();
  } catch (err) {
    $("form-error").textContent = `Couldn't load saved models: ${err.message}`;
  }
}

async function startTraining(event) {
  event.preventDefault();
  $("form-error").textContent = "";
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const body = {
    resume: mode === "resume" ? $("resume").value || null : null,
    opponents: [0, 1, 2].map((i) => $(`opp${i}`).value),
    tensorboard: $("tensorboard").checked,
  };
  $("start-btn").disabled = true;
  try {
    const data = await api("/api/training", body);
    selectedRun = null; // follow the new run
    render(data);
  } catch (err) {
    $("form-error").textContent = err.message;
  } finally {
    updateStartButton();
  }
}

function updateStartButton() {
  const active = lastData && lastData.active;
  $("start-btn").disabled = Boolean(active);
  $("start-btn").textContent = active ? "Training is running…" : "Start training";
}

// ---------- status ----------

function render(data) {
  lastData = data;
  const run = data.run;
  updateStartButton();

  fill($("run"), data.runs.length
    ? data.runs.map((r) => h("option", { value: r.name, selected: run && r.name === run.name },
      `${runLabel(r.name)}${r.running ? " · running" : ""}`))
    : h("option", { value: "" }, "No runs yet"));

  const badge = $("badge");
  const stopBtn = $("stop-btn");
  if (!run) {
    badge.textContent = "";
    stopBtn.hidden = true;
    fill($("run-meta"), "Start a run on the left. Runs started with python train.py show up here too.");
    fill($("tiles")); fill($("details")); fill($("console"));
    drawChart([]);
    return;
  }
  const state = run.stopping && run.running ? "Stopping…" : run.running ? "Running"
    : run.finished_at ? "Finished" : "Not running";
  badge.textContent = state;
  badge.className = `badge ${run.running ? "live" : ""}`;
  stopBtn.hidden = !run.running || run.stopping;

  const cfg = run.config || {};
  const meta = [];
  if (cfg.started_at) meta.push(`Started ${cfg.started_at.replace("T", " ")}`);
  if (cfg.resume !== undefined) meta.push(cfg.resume ? `continued from ${checkpointLabel(cfg.resume)}` : "new model");
  if (cfg.opponents) meta.push(`vs ${cfg.opponents.map(opponentLabel).join(", ")}`);
  if (!run.config) meta.push("started before the training page existed");
  if (run.exit_code != null && run.exit_code !== 0) meta.push(`exited with code ${run.exit_code} (see console)`);
  fill($("run-meta"), meta.join(" · "));

  const points = run.progress.points;
  const last = points[points.length - 1] || {};
  const games = last.game ?? last.games;
  const tile = (label, value, sub) => h("div", { class: "stat-tile" },
    h("span", { class: "label" }, label), h("span", { class: "value" }, value),
    sub ? h("span", { class: "sub" }, sub) : null);
  fill($("tiles"),
    tile("Games", fmtInt(games)),
    tile("VP", fmt(last.vp), "average, last 100 games"),
    tile("VP record", fmtInt(last.vp_record), "best game, last 100"),
    tile("Exploration", fmt(last.epsilon, 2), "ε"),
    tile("Speed", fmt(last.games_per_sec, 2), "games / s"));

  const detail = (k, v) => [h("dt", {}, k), h("dd", {}, v)];
  fill($("details"),
    detail("Cards", fmt(last.cards)), detail("Buildings", fmt(last.buildings)),
    detail("Tools", fmt(last.tools)), detail("People", fmt(last.people)),
    detail("Wheat", fmt(last.wheat)), detail("Rounds", fmt(last.rounds)),
    detail("Food", fmt(last.food)), detail("Wood", fmt(last.wood)),
    detail("Stone", fmt(last.stone)), detail("Clay", fmt(last.clay)),
    detail("Gold", fmt(last.gold)), detail("Loss", fmt(last.loss, 4)));

  $("chart-note").textContent = run.progress.source === "checkpoints"
    ? "one point per checkpoint (this run has no progress log)" : "one point per 100 games";
  drawChart(points);

  const pre = $("console");
  const atBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 4;
  pre.textContent = run.log.length ? run.log.join("\n")
    : run.managed ? "Starting…" : "No console log (only runs started from this page keep one).";
  if (atBottom) pre.scrollTop = pre.scrollHeight;
}

async function refresh() {
  try {
    const q = selectedRun ? `?run=${encodeURIComponent(selectedRun)}` : "";
    render(await api(`/api/training${q}`));
  } catch (err) {
    $("run-meta").textContent = `Couldn't load training status: ${err.message}`;
  }
}

async function stopTraining() {
  if (!lastData || !lastData.run) return;
  $("stop-btn").disabled = true;
  try {
    render(await api("/api/training/stop", { run: lastData.run.name }));
  } catch (err) {
    $("run-meta").textContent = err.message;
  } finally {
    $("stop-btn").disabled = false;
  }
}

// ---------- chart ----------

function niceTicks(min, max, count = 5) {
  if (min === max) { min -= 1; max += 1; }
  const step0 = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0);
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(10));
  return ticks;
}

let chartPoints = [];

function drawChart(points) {
  const metric = $("metric").value;
  const svg = $("chart-svg");
  const width = $("chart").clientWidth || 600;
  const height = 260;
  const m = { top: 12, right: 14, bottom: 26, left: 48 };
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", width);
  svg.setAttribute("height", height);

  chartPoints = points
    .map((p) => ({ x: p.game ?? p.games, y: p[metric] }))
    .filter((p) => p.x != null && p.y != null && !Number.isNaN(p.y));
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    return e;
  };
  svg.replaceChildren();
  $("chart-tip").hidden = true;
  if (!chartPoints.length) {
    const t = el("text", { x: width / 2, y: height / 2, "text-anchor": "middle", class: "chart-empty" });
    t.textContent = "No data yet: the first point appears after 100 games.";
    svg.append(t);
    return;
  }

  const xs = chartPoints.map((p) => p.x);
  const ys = chartPoints.map((p) => p.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yTicks = niceTicks(Math.min(...ys), Math.max(...ys));
  const yMin = yTicks[0], yMax = yTicks[yTicks.length - 1];
  const sx = (x) => m.left + (xMax === xMin ? (width - m.left - m.right) / 2
    : (x - xMin) / (xMax - xMin) * (width - m.left - m.right));
  const sy = (y) => m.top + (1 - (y - yMin) / (yMax - yMin)) * (height - m.top - m.bottom);

  for (const t of yTicks) {
    svg.append(el("line", { x1: m.left, x2: width - m.right, y1: sy(t), y2: sy(t),
      class: t === 0 && yMin < 0 ? "grid zero" : "grid" }));
    const label = el("text", { x: m.left - 8, y: sy(t) + 4, "text-anchor": "end", class: "axis" });
    label.textContent = Math.abs(t) >= 1000 ? fmtGames(t) : +t.toFixed(3);
    svg.append(label);
  }
  const xTicks = xMax > xMin ? niceTicks(xMin, xMax, Math.max(2, Math.floor(width / 110)))
    .filter((t) => t >= xMin && t <= xMax) : [xMin];
  for (const t of xTicks) {
    const label = el("text", { x: sx(t), y: height - 6, "text-anchor": "middle", class: "axis" });
    label.textContent = fmtGames(t);
    svg.append(label);
  }

  const d = chartPoints.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("");
  svg.append(el("path", { d, class: "series" }));
  if (chartPoints.length === 1) {
    svg.append(el("circle", { cx: sx(chartPoints[0].x), cy: sy(chartPoints[0].y), r: 4, class: "dot" }));
  }

  // Hover layer: crosshair + dot + tooltip on the nearest point.
  const cross = el("line", { y1: m.top, y2: height - m.bottom, class: "crosshair", visibility: "hidden" });
  const dot = el("circle", { r: 4.5, class: "dot", visibility: "hidden" });
  svg.append(cross, dot);
  const hit = el("rect", { x: m.left, y: m.top, width: width - m.left - m.right,
    height: height - m.top - m.bottom, fill: "transparent" });
  svg.append(hit);
  const tip = $("chart-tip");
  const label = METRICS.find(([k]) => k === metric)[1];
  const show = (evt) => {
    const box = svg.getBoundingClientRect();
    const px = (evt.clientX - box.left) * (width / box.width);
    let best = 0;
    for (let i = 1; i < chartPoints.length; i++) {
      if (Math.abs(sx(chartPoints[i].x) - px) < Math.abs(sx(chartPoints[best].x) - px)) best = i;
    }
    const p = chartPoints[best];
    const cx = sx(p.x), cy = sy(p.y);
    cross.setAttribute("x1", cx); cross.setAttribute("x2", cx);
    dot.setAttribute("cx", cx); dot.setAttribute("cy", cy);
    cross.setAttribute("visibility", "visible"); dot.setAttribute("visibility", "visible");
    fill(tip, h("strong", {}, `${p.y.toFixed(Math.abs(p.y) < 10 ? 3 : 1)}`), " ", label,
      h("br"), h("span", { class: "muted" }, `game ${p.x.toLocaleString()}`));
    tip.hidden = false;
    const left = cx * (box.width / width);
    tip.style.left = `${Math.min(left + 12, box.width - tip.offsetWidth - 4)}px`;
    tip.style.top = `${Math.max(0, cy * (box.height / height) - tip.offsetHeight - 10)}px`;
  };
  const hide = () => {
    cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden");
    tip.hidden = true;
  };
  hit.addEventListener("pointermove", show);
  hit.addEventListener("pointerdown", show);
  hit.addEventListener("pointerleave", hide);
  svg.setAttribute("aria-label", `${label}: ${chartPoints.length} points, latest ${p0(chartPoints)}`);
}
const p0 = (pts) => { const p = pts[pts.length - 1]; return `${p.y.toFixed(2)} at game ${p.x}`; };

// ---------- wiring ----------

fill($("metric"), METRICS.map(([k, label]) => h("option", { value: k }, label)));
$("metric").addEventListener("change", () => lastData && drawChart(lastData.run ? lastData.run.progress.points : []));
$("run").addEventListener("change", (e) => { selectedRun = e.target.value || null; refresh(); });
$("stop-btn").addEventListener("click", stopTraining);
$("start-form").addEventListener("submit", startTraining);
document.querySelectorAll('input[name="mode"]').forEach((r) =>
  r.addEventListener("change", () => { $("resume").disabled = !document.querySelector('input[name="mode"][value="resume"]').checked; }));
window.addEventListener("resize", () => lastData && lastData.run && drawChart(lastData.run.progress.points));

loadCheckpoints();
refresh();
setInterval(refresh, POLL_MS);
setInterval(loadCheckpoints, 30000); // new checkpoints appear as training saves them
