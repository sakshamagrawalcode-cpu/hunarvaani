// HunarVaani officer console. Four views, picked by the address: #live, #people, #person/<id>, #policy.
// Everything comes from the API after login (a session cookie); nothing personal is kept in the browser.
"use strict";

// ---- small helpers -------------------------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const pretty = (id) => id && id.length === 9 ? `${id.slice(0, 4)}-${id.slice(4, 8)}-${id.slice(8)}` : (id || "");
const day = (ts) => (ts || "").slice(0, 10);
const when = (ts) => (ts || "").replace("T", " ").slice(0, 16);
const store = {  // per-browser conveniences only (the line PIN, sound on/off); works if storage is blocked
  get(k, d = "") { try { return localStorage.getItem(k) ?? d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { } },
};

const ICON = {
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.9.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
  phoneOff: '<path d="M10.7 13.3a16 16 0 0 0 3.4 2.6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.9.6 2.8.7a2 2 0 0 1 1.7 2v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.4 19.4 0 0 1-3.3-2.7m-2.7-3.3a19.8 19.8 0 0 1-3.1-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9"/><path d="M22 2 2 22"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
  user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M2 14h4M10 8h4M18 16h4"/>',
  filter: '<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4zM15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8-6.2-3.2L5.8 21 7 14.2 2 9.3l6.9-1z"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
  edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  trash: '<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  print: '<path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  alert: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3ZM12 9v4M12 17h.01"/>',
  keypad: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 8h.01M12 8h.01M16 8h.01M8 12h.01M12 12h.01M16 12h.01M8 16h.01M12 16h.01M16 16h.01"/>',
  quote: '<path d="M3 21c3 0 7-1 7-8V5c0-1.3-.8-2-2-2H4c-1.3 0-2 .8-2 2v6c0 1.3.8 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 0-1 1v3c0 1 0 1 1 1zM15 21c3 0 7-1 7-8V5c0-1.3-.8-2-2-2h-4c-1.3 0-2 .8-2 2v6c0 1.3.8 2 2 2h.8c0 2.3.2 4-2.8 4v3c0 1 0 1 1 1z"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  scale: '<path d="m16 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1ZM2 16l3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1ZM7 21h10M12 3v18M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
  idcard: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M16 10h2M16 14h2"/><circle cx="9" cy="11" r="2"/><path d="M6 16c.5-1.5 1.7-2 3-2s2.5.5 3 2"/>',
  send: '<path d="m22 2-7 20-4-9-9-4ZM22 2 11 13"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  back: '<path d="m15 18-6-6 6-6"/>',
};
const icon = (name) => `<i data-icon="${name}"></i>`;
function paintIcons(root = document) {
  $$("i[data-icon]", root).forEach((el) => {
    if (el.firstChild) return;
    el.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[el.dataset.icon] || ""}</svg>`;
  });
}

function toast(text, kind = "") {
  const el = document.createElement("div");
  el.className = "toast " + kind; el.textContent = text;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), kind === "err" ? 6000 : 3200);
}

class LoginNeeded extends Error {}
async function api(url, {method = "GET", body} = {}) {
  const r = await fetch(url, {method, credentials: "same-origin",
    headers: body !== undefined ? {"Content-Type": "application/json"} : {},
    body: body !== undefined ? JSON.stringify(body) : undefined});
  let data = null;
  try { data = await r.json(); } catch (e) { }
  if (r.status === 401 && !url.startsWith("/api/login")) { showLogin(); throw new LoginNeeded("Please log in again"); }
  if (!r.ok) throw new Error((data && data.error) || `Request failed (${r.status})`);
  return data;
}
const fail = (err) => { if (!(err instanceof LoginNeeded)) toast(err.message, "err"); };

// ---- login and the frame ---------------------------------------------------------------------------
let me = null, cat = null;

function showLogin() {
  hangUp(true);
  me = null;
  $("#app").classList.add("hidden"); $("#login").classList.remove("hidden");
  setTimeout(() => $("#loginPw").focus(), 50);
}

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#loginErr").textContent = "";
  try {
    await api("/api/login", {method: "POST", body: {user: $("#loginUser").value.trim(), password: $("#loginPw").value}});
    $("#loginPw").value = "";
    boot();
  } catch (err) { $("#loginErr").textContent = err.message; }
});

$("#logout").onclick = async () => { hangUp(true); try { await api("/api/logout", {method: "POST"}); } catch (e) { } showLogin(); };

async function boot() {
  try { me = await api("/api/me"); } catch (e) {
    if (!(e instanceof LoginNeeded)) { showLogin(); $("#loginErr").textContent = `The server did not answer: ${e.message}`; }
    return;
  }
  try { cat = await api("/api/catalog"); } catch (e) { fail(e); return; }
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  $("#whoName").textContent = me.user;
  $("#modePill").textContent = me.models === "real" ? `models: ${me.llm}` : "fake mode (no models)";
  $("#modePill").className = "pill " + (me.models === "real" ? "real" : "fake");
  $("#pwWarn").classList.toggle("hidden", !me.default_password);
  paintIcons();
  route();
}

window.addEventListener("hashchange", route);
function route() {
  if (!me) return;
  const [tab, arg] = (location.hash.slice(1) || "live").split("/");
  $$("#tabs a").forEach((a) => a.classList.toggle("on", a.dataset.tab === (tab === "person" ? "people" : tab)));
  if (tab !== "live" && call.ws) toast("The live call goes on in the Live call tab.");
  if (tab === "people") showPeople();
  else if (tab === "person" && arg) showPerson(arg);
  else if (tab === "policy") showPolicy();
  else showLive();
}

// ================================================================================================
// Live call: a phone call played in this browser. The officer is the caller: keys answer menus, the
// box under the phone types what the caller says (or "Speak" uses the microphone). Every decision the
// system makes arrives as a step on the right: heard, labelled, why this question, why these options.
// ================================================================================================
const call = {ws: null, state: "idle", started: 0, ask: null, entry: "", reason: "", timer: null,
  steps: [], profile: null, shortlist: [], audioQ: [], playing: false, audio: null, gen: 0, mic: null, micStarting: false};
let liveEl = null;  // the live view stays built while other tabs are open, so a call is never lost

function showLive() {
  const view = $("#view");
  if (liveEl) { view.replaceChildren(liveEl); return; }
  liveEl = document.createElement("div");
  liveEl.className = "live";
  liveEl.innerHTML = `
    <section class="stage">
      <div class="stage-h"><b>Phone line demo</b><span class="cstate" id="cstate">Idle</span></div>
      <div class="line-set"><span>Line PIN code</span><input id="linePin" inputmode="numeric" maxlength="6" placeholder="411001">
        <button class="btn sm" id="lineSet">Set</button><span class="where" id="lineWhere"></span></div>
      <div class="phone">
        <div class="ear"></div><div class="plogo">HUNARVAANI</div>
        <div class="screen"><div class="sb"><span class="bars"><i></i><i></i><i></i><i></i></span><span id="clock"></span><span class="batt"><i></i></span></div>
          <div class="scr" id="scr"></div><div class="softs"><span id="softL">Speak</span><span id="softR">Clear</span></div></div>
        <div class="pnav">
          <button class="pk soft" data-k="softL" aria-label="Left soft key"></button>
          <div class="dpad"><button class="pk" data-k="ok">OK</button></div>
          <button class="pk soft" data-k="softR" aria-label="Right soft key"></button>
          <button class="pk call" data-k="call" aria-label="Call">${icon("phone")}</button>
          <button class="pk end" data-k="end" aria-label="Hang up">${icon("phoneOff")}</button>
        </div>
        <div class="keys">${[["1", ""], ["2", "ABC"], ["3", "DEF"], ["4", "GHI"], ["5", "JKL"], ["6", "MNO"], ["7", "PQRS"], ["8", "TUV"], ["9", "WXYZ"], ["*", ""], ["0", "+"], ["#", ""]]
          .map(([k, s]) => `<button class="pk" data-k="${k}"><b>${k}</b><small>${s || "&nbsp;"}</small></button>`).join("")}</div>
      </div>
      <div class="say-row"><input id="sayIn" placeholder="Type what the caller says…" autocomplete="off">
        <button class="btn sm" id="sayBtn" aria-label="Send">${icon("send")}</button>
        <button class="btn sm" id="micBtn">${icon("mic")}Speak</button></div>
      <div class="stage-opts"><label><input type="checkbox" id="soundOn"> Sound</label>
        <label><input type="checkbox" id="autoMic"> Listen after each question</label></div>
      <p class="tiny">Green key calls. Number keys answer the menus; 0 asks for an officer, 9 twice erases. The PIN is typed on the keypad.</p>
    </section>
    <section class="live-side">
      <div class="now">
        <section class="card"><header><span class="ic">${icon("user")}</span><h3>Understood so far</h3></header><div class="body" id="nowProfile"></div></section>
        <section class="card"><header><span class="ic green">${icon("list")}</span><h3>Shortlist now</h3><span class="aside" id="slNote"></span></header><div class="body" id="nowList"></div></section>
      </div>
      <section class="card"><div class="body">
        <div class="steps-h"><span class="ic violet">${icon("route")}</span><h3>Step by step</h3>
          <label class="check"><input type="checkbox" id="onlyDecisions"> Decisions only</label></div>
        <div class="steps" id="steps" style="margin-top:12px"></div></div></section>
    </section>`;
  view.replaceChildren(liveEl);
  paintIcons(liveEl);

  $("#linePin").value = store.get("hv_line_pin", cat.line_pin || "");
  $("#lineSet").onclick = setLine;
  $("#linePin").onkeydown = (e) => { if (e.key === "Enter") setLine(); };
  showLine();
  $("#soundOn").checked = store.get("hv_console_sound", "on") === "on";
  $("#soundOn").onchange = () => { store.set("hv_console_sound", $("#soundOn").checked ? "on" : "off"); if (!$("#soundOn").checked) stopAudio(); };
  $("#autoMic").checked = store.get("hv_console_automic", "off") === "on";
  $("#autoMic").onchange = () => store.set("hv_console_automic", $("#autoMic").checked ? "on" : "off");
  $("#onlyDecisions").onchange = () => renderSteps();
  $$(".pk", liveEl).forEach((b) => b.onclick = () => press(b.dataset.k));
  $("#sayBtn").onclick = sayTyped;
  $("#sayIn").onkeydown = (e) => { if (e.key === "Enter") sayTyped(); };
  $("#micBtn").onclick = () => call.mic ? stopMic(true) : startMic();
  renderScreen(); renderNow(); renderSteps();
  setInterval(tick, 1000); tick();
}

// keyboard: number keys on the computer press the phone's keys (unless typing in a box)
document.addEventListener("keydown", (e) => {
  if (!liveEl || !liveEl.isConnected || e.ctrlKey || e.metaKey || e.altKey) return;
  if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName) || $("#dlg").open) return;
  if (/^[0-9*#]$/.test(e.key)) { press(e.key); e.preventDefault(); }
  else if (e.key === "Backspace") { press("softR"); e.preventDefault(); }
  else if (e.key === "Enter") { press(call.ws ? "ok" : "call"); e.preventDefault(); }
  else if (e.key === "Escape" && call.ws) { press("end"); }
});

async function setLine() {
  const pin = $("#linePin").value.trim();
  if (pin && !/^\d{6}$/.test(pin)) { toast("A PIN code has 6 digits.", "err"); return; }
  if (pin) {
    const r = await fetch("/api/pincode/" + pin).catch(() => null);
    if (!r || !r.ok) { toast("This PIN code is not in our district list.", "err"); return; }
  }
  store.set("hv_line_pin", pin); showLine();
  toast(pin ? "Line PIN code set: callers get this district." : "No line PIN code: callers will be asked for theirs.");
}
async function showLine() {
  const pin = store.get("hv_line_pin", cat.line_pin || "");
  $("#lineWhere").textContent = pin ? "…" : "Not set: the caller will be asked for their PIN code.";
  if (!pin) return;
  const r = await fetch("/api/pincode/" + pin).catch(() => null);
  const d = r && r.ok ? await r.json() : null;
  $("#lineWhere").textContent = d ? `Calls to this line are from ${d.district}, ${d.state}.` : "PIN code not in the list.";
}

function tick() {
  if (!liveEl) return;
  const now = new Date();
  $("#clock", liveEl).textContent = now.toTimeString().slice(0, 5);
  const t = $("#tmr", liveEl);
  if (t && call.started) t.textContent = dur(Date.now() - call.started);
}
const dur = (ms) => { const s = Math.max(0, Math.floor(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

function setState(state, label) {
  call.state = state;
  const el = $("#cstate");
  if (el) { el.textContent = label; el.classList.toggle("on", state === "on"); }
}

// ---- the phone's screen ------------------------------------------------------------------------
function renderScreen() {
  const scr = $("#scr");
  if (!scr) return;
  const a = call.ask;
  let softL = "Speak", softR = "Clear", html = "";
  if (call.state === "idle" || call.state === "ended") {
    softL = ""; softR = "";
    html = call.state === "ended"
      ? `<div class="big">Call ended</div><div class="dim">${esc(call.reason)}</div><div class="tmr">${esc(call.duration || "")}</div><div class="small">Press the green key to call again</div>`
      : `<div class="big">HunarVaani</div><div class="dim">Skills helpline · demo</div><div class="small">Press the green key to call</div>`;
  } else if (call.state === "dialing") {
    softL = ""; softR = "";
    html = `<div class="ct"><b>HunarVaani</b><span class="dim">Calling…</span></div><div class="dots3"><i></i><i></i><i></i></div>`;
  } else {
    const head = `<div class="ct"><b>HunarVaani</b><span class="tmr" id="tmr">${dur(Date.now() - call.started)}</span></div>`;
    let body;
    if (call.mic) body = `<span class="st listen">${icon("mic")}Listening</span><div class="mlevel" id="mlevel">${"<i></i>".repeat(9)}</div>`;
    else if (call.playing) body = `<span class="st speak">${icon("volume")}Speaking</span><div class="wave">${"<i></i>".repeat(7)}</div>`;
    else if (a && a.mode === "digits") body = `<span class="st keys">${icon("keypad")}Type ${a.count} digits</span><div class="entry">${esc((a.secret ? "•".repeat(call.entry.length) : call.entry) + "_".repeat(Math.max(0, a.count - call.entry.length)))}</div>`;
    else if (a && a.mode === "keys") body = `<span class="st keys">${icon("keypad")}Press a key</span>${menu(a)}`;
    else if (a && a.mode === "talk") body = `<span class="st">${icon("message")}Your answer</span>${menu(a) || `<div class="small">Type it below, or Speak</div>`}`;
    else body = `<div class="dots3"><i></i><i></i><i></i></div>`;
    html = head + body;
    if (a && a.mode === "digits") softL = "";
    else softR = "End";
  }
  $("#softL").textContent = softL; $("#softR").textContent = softR;
  scr.innerHTML = html; paintIcons(scr);
}
function menu(a) {
  const keys = (a.allowed || "").split("").filter((k) => k !== "0" && k !== "9");
  let labels = a.labels || [];
  if (a.keys.includes("lang_hi")) labels = ["हिंदी", "मराठी", "English"];
  const rows = keys.map((k, i) => labels[i] ? `<span><b>${k}</b>${esc(labels[i])}</span>` : "").filter(Boolean).slice(0, 5);
  return rows.length ? `<div class="menu">${rows.join("")}</div>` : "";
}

// ---- keys -------------------------------------------------------------------------------------------
function flash(k) { const b = $(`.pk[data-k="${CSS.escape(k)}"]`); if (b) { b.classList.add("hit"); setTimeout(() => b.classList.remove("hit"), 120); } }
function press(k) {
  flash(k);
  if (k === "call") { if (!call.ws) dial(); else if (call.ask?.mode === "digits") submitEntry(); return; }
  if (k === "end") { if (call.ws) hangUp(); return; }
  if (!call.ws || call.state !== "on") return;
  const a = call.ask;
  if (k === "softL") { if (a?.mode !== "digits") call.mic ? stopMic(true) : startMic(); return; }
  if (k === "softR") {
    if (a?.mode === "digits") { call.entry = call.entry.slice(0, -1); renderScreen(); } else hangUp();
    return;
  }
  if (k === "ok") { if (a?.mode === "digits") submitEntry(); else if (a?.mode === "talk" && !call.mic) startMic(); return; }
  if (!a) return;
  if (a.mode === "digits") {
    if (!/\d/.test(k) || call.entry.length >= a.count) return;
    call.entry += k; renderScreen();
    if (call.entry.length === a.count) setTimeout(submitEntry, 250);
    return;
  }
  if ((a.allowed || "").includes(k)) answer(k, a.mode === "keys" || a.mode === "talk" ? keyLabel(a, k) : "");
}
function keyLabel(a, k) {
  const keys = (a.allowed || "").split("").filter((x) => x !== "0" && x !== "9");
  if (k === "0") return "talk to an officer";
  if (k === "9") return "erase my data";
  return (a.keys.includes("lang_hi") ? ["हिंदी", "मराठी", "English"] : a.labels || [])[keys.indexOf(k)] || "";
}
function submitEntry() {
  const a = call.ask;
  if (!a || a.mode !== "digits" || call.entry.length !== a.count) return;
  const v = call.entry;
  answer(v, a.secret ? "••••" : v, true);
}
function sayTyped() {
  const v = $("#sayIn").value.trim();
  if (!v) return;
  if (!call.ws || !call.ask) { toast(call.ws ? "Wait for the question first." : "Call first: press the green key.", "err"); return; }
  const a = call.ask;
  if (a.mode === "digits" && !/^\d+$/.test(v)) { toast(`This one is typed on the keypad: ${a.count} digits.`, "err"); return; }
  if (a.mode === "keys" && !(v.length === 1 && a.allowed.includes(v))) { toast("This menu takes a key press.", "err"); return; }
  $("#sayIn").value = "";
  answer(v);
}
function answer(value, shown, isEntry) {
  if (!call.ws || call.ws.readyState !== 1) return;
  stopMic(false); stopAudio();
  call.ws.send(JSON.stringify({type: "answer", value: String(value)}));
  if (isEntry) addBubble("me", `Typed ${shown}`);  // keys and speech come back as steps; typed digits are shown here
  call.ask = null; call.entry = "";
  renderScreen();
}

// ---- the call itself ---------------------------------------------------------------------------
function dial() {
  call.steps = []; call.profile = null; call.shortlist = []; call.ask = null; call.entry = ""; call.reason = "";
  renderNow(); renderSteps();
  setState("dialing", "Calling…"); renderScreen();
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/console`);
  ws.binaryType = "arraybuffer";
  call.ws = ws;
  ws.onopen = () => {
    ws.send(JSON.stringify({type: "hello", device_pin: store.get("hv_line_pin", cat.line_pin || "")}));
    call.started = Date.now();
    setState("on", "On call"); renderScreen();
  };
  ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  ws.onclose = () => {
    if (call.ws !== ws) return;
    const opened = call.started;
    call.ws = null; call.ask = null; stopMic(false);
    call.duration = opened ? dur(Date.now() - opened) : "";
    if (!call.reason) call.reason = opened ? "Line closed" : "Could not connect (log in again?)";
    call.started = 0;
    setState("ended", "Ended"); renderScreen();
  };
}
function hangUp(quiet) {
  if (!call.ws) return;
  if (!quiet) call.reason = "You hung up";
  stopAudio(); stopMic(false);
  try { call.ws.close(); } catch (e) { }
}

function onMessage(msg) {
  if (msg.type === "say" || msg.type === "ask") {
    if (msg.text) addBubble("sys", msg.text);
    enqueue(msg);
    if (msg.type === "ask") { call.ask = msg; call.entry = ""; }
    renderScreen();
  } else if (msg.type === "show") {
    onShow(msg.kind, msg.data || {});
  } else if (msg.type === "trace") {
    onTrace(msg);
  } else if (msg.type === "end") {
    call.reason = {completed: "Completed", "no answer": "No answer", "caller deleted their data": "Caller erased their data"}[msg.reason] || msg.reason;
    addStep({step: "end", title: `Call ended: ${call.reason}`, lines: []});
  }
}
function onShow(kind, d) {
  if (kind === "profile" || kind === "review") { call.profile = {...(call.profile || {}), ...d, _kind: kind}; renderNow(); }
  else if (kind === "options") { call.shortlist = (d.items || []).map((o, i) => ({rank: i + 1, course: o.course, centre: o.centre, distance_km: o.distance_km, score: o.score})); renderNow("Offered to the caller"); }
  else if (kind === "skills") addStep({step: "skills", title: "Skills worth learning", lines: (d.items || []).map((a) => `${a.skills.join(", ")}: for ${a.course}, about ${a.weeks} weeks (${a.gap} gap)`)});
  else if (kind === "card") addStep({step: "card", title: `Card ready: ${d.hv_id}`, lines: [`${d.name || ""} · ${d.district || ""}`], data: {hv_id: (d.raw_id || "")}});
  else if (kind === "person") addStep({step: "card", title: `Returning caller: ${d.hv_id}`, lines: (d.options || []).map((o) => `${o.rank}. ${o.course}`), data: {hv_id: d.hv_id.replace(/-/g, "")}});
}
function onTrace(t) {
  if (t.step === "heard" && t.data.text) {
    addBubble("me", t.data.text, t.data.source === "speech-to-text" ? `Caller · speech to text${t.data.ms ? ` · ${t.data.ms} ms` : ""}` : "Caller (typed)");
    return;
  }
  if (t.step === "key") { addBubble("me", t.title, "Caller · key"); return; }
  if (t.step === "plan" && t.data.shortlist?.length) { call.shortlist = t.data.shortlist; renderNow("If the call ended now"); }
  if (t.step === "ranking") { call.shortlist = t.data.options; renderNow("Ranked"); }
  if (t.step === "choice") { call.shortlist = call.shortlist.map((o) => ({...o, chosen: o.rank === t.data.rank})); renderNow("Chosen"); }
  addStep(t);
}

// ---- the right side: understood so far, shortlist, steps ------------------------------------------
function renderNow(note) {
  const pEl = $("#nowProfile"), lEl = $("#nowList");
  if (!pEl) return;
  const d = call.profile;
  if (!d) pEl.innerHTML = `<p class="tiny">Fills in as the caller answers.</p>`;
  else {
    const travel = d.radius_km ?? d.travel_km;
    const rows = [["Name", d.name], ["Age", d.age], ["Studies", d.education_label || d.education], ["Work", (d.work || []).join(", ") + (d.years ? ` · ${d.years} yrs` : "")],
      ["Wants", (d.wants || []).join(", ")], ["Travel", travel ? `${travel} km${d.cannot_leave_home ? " · cannot leave home" : ""}` : ""],
      ["Health", d.health && d.health !== "none" ? d.health : ""], ["Best match", d.lead_label || ""], ["Said no", (d.rejected || []).join(", ")]]
      .filter(([, v]) => v !== undefined && v !== null && v !== "");
    const emph = Object.entries(d.emphasis || {}).map(([k, v]) => `<span class="chip warn">${esc(k)} ${esc(v)}</span>`).join(" ");
    pEl.innerHTML = `<dl class="facts-list">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}</dl>${emph ? `<div style="margin-top:8px;display:flex;gap:4px;flex-wrap:wrap">${emph}</div>` : ""}`;
  }
  if (note !== undefined) $("#slNote").textContent = note;
  lEl.innerHTML = call.shortlist.length ? call.shortlist.map((o) => `<div class="opt ${o.chosen ? "chosen" : ""}"><div class="opt-h"><span class="rank">${o.rank}</span><b>${esc(o.course)}</b><span class="score">${(+o.score).toFixed(2)}</span></div>
      ${o.centre ? `<div class="why">${esc(o.centre)}${o.distance_km !== undefined ? ` · ${o.distance_km} km` : ""}</div>` : ""}</div>`).join("")
    : `<p class="tiny">Appears after the caller's story.</p>`;
}

const STEP_ICON = {heard: ["message", ""], key: ["keypad", ""], llm: ["cpu", "violet"], rules: ["check", ""], plan: ["help", "amber"],
  ranking: ["list", "green"], tradeoff: ["scale", "amber"], choice: ["star", "green"], saved: ["save", "green"], review: ["eye", ""],
  officer: ["alert", "red"], end: ["phoneOff", "red"], skills: ["book", "green"], card: ["idcard", "green"]};
function addBubble(who, text, label) { call.steps.push({bubble: who, text, label, at: Date.now()}); renderSteps(true); }
function addStep(t) { call.steps.push({...t, at: Date.now()}); renderSteps(true); }

function renderSteps(append) {
  const box = $("#steps");
  if (!box) return;
  const only = $("#onlyDecisions")?.checked;
  const items = call.steps.filter((s) => !only || (!s.bubble && !["key"].includes(s.step)));
  if (!items.length) { box.innerHTML = `<p class="tiny">Press the green key to start a call. Each answer shows here with what the system understood and why it chose the next step.</p>`; return; }
  const start = call.steps[0]?.at || Date.now();
  const html = (s) => s.bubble
    ? `<div class="bubble ${s.bubble}"><small>${esc(s.label || (s.bubble === "sys" ? "HunarVaani" : "Caller"))}</small>${esc(s.text)}</div>`
    : stepHtml(s, start);
  if (append && box.children.length && box.firstElementChild.tagName !== "P" && items.length === box.children.length + 1) {
    box.insertAdjacentHTML("beforeend", html(items[items.length - 1]));
    paintIcons(box.lastElementChild);
  } else { box.innerHTML = items.map(html).join(""); paintIcons(box); }
  if (append) box.lastElementChild?.scrollIntoView({block: "nearest", behavior: "smooth"});
}

function bars(list, max) {
  const top = max || Math.max(0.0001, ...list.map((x) => x.v));
  return `<div class="bars-list">${list.map((x) => `<div class="bar ${x.on ? "picked" : ""}"><span title="${esc(x.label)}">${esc(x.label)}</span><span class="track"><i style="width:${Math.max(2, Math.min(100, 100 * x.v / top))}%"></i></span><span class="v">${x.text ?? x.v.toFixed(2)}</span></div>`).join("")}</div>`;
}

function stepHtml(s, start) {
  const [ic, tone] = STEP_ICON[s.step] || ["route", ""];
  const d = s.data || {};
  let extra = "";
  if (s.step === "plan" && d.candidates?.length) {
    extra = `<div class="tiny">Asked: “${esc(d.text)}”</div>` + bars(d.candidates.map((c) => ({label: c.name, v: c.value, on: c.picked})));
  } else if (s.step === "llm") {
    extra = `<details><summary>${esc(d.model || "LLM")}${d.ms !== undefined ? ` · ${d.ms} ms` : ""} · raw answer</summary><pre>${esc(JSON.stringify(d.raw || {}, null, 1))}</pre></details>`;
  } else if (s.step === "ranking") {
    extra = `<div class="tiny">This person's weights (officer weight w × their own emphasis m):</div>`
      + bars((d.weights || []).map((w) => ({label: `${w.label} ×${w.m}`, v: w.share, text: pct(w.share)})), 1)
      + (d.options || []).map((o) => `<div class="opt"><div class="opt-h"><span class="rank">${o.rank}</span><b>${esc(o.course)}</b><span class="score">${o.score.toFixed(2)}</span></div>
          <div class="why">${esc(o.sentence)}</div></div>`).join("")
      + (d.left_out?.length ? `<div class="tiny" style="margin-top:6px">Left out by the gates:</div><div class="left-out">${d.left_out.map((x) => `<div><b>${esc(x.course)}</b> <small>${esc(x.centre)} · fit ${x.fit.toFixed(2)}</small><br>${esc(x.because.join("; "))}</div>`).join("")}</div>` : "");
  } else if (s.step === "card" && d.hv_id) {
    extra = `<div><a class="btn sm" href="#person/${esc(d.hv_id)}">${icon("user")}Open the record</a></div>`;
  } else if (s.step === "saved" && d.hv_id) {
    extra = `<div><a class="btn sm" href="#person/${esc(d.hv_id)}">${icon("user")}Open the record</a></div>`;
  }
  const lines = (s.lines || []).filter((l) => !(s.step === "ranking" && /^Top:|^Left out:/.test(l)));
  return `<div class="step ${esc(s.step)}"><div class="step-h"><span class="ic ${tone}">${icon(ic)}</span>${esc(s.title)}<span class="t">+${dur(s.at - start)}</span></div>
    ${lines.length ? `<ul>${lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : ""}${extra}</div>`;
}

// ---- audio: the rendered voice pieces, or the browser voice if they are missing --------------------
const VOICE = {hi: "hi-IN", mr: "mr-IN", en: "en-IN"};
function enqueue(msg) {
  if (!$("#soundOn")?.checked) { afterAudio(); return; }
  call.audioQ.push(msg);
  if (!call.playing) playNext();
}
function playNext() {
  const msg = call.audioQ.shift();
  if (!msg) { call.playing = false; call.audio = null; renderScreen(); afterAudio(); return; }
  call.playing = true; renderScreen();
  const gen = call.gen;
  if (msg.audio?.length && msg.complete_audio) {
    const urls = msg.audio.slice();
    const step = () => {
      if (gen !== call.gen) return;
      const u = urls.shift();
      if (!u) return playNext();
      const a = new Audio(u); call.audio = a;
      a.onended = step; a.onerror = step; a.play().catch(step);
    };
    step();
  } else if ("speechSynthesis" in window && msg.text) {
    const u = new SpeechSynthesisUtterance(msg.text); u.lang = VOICE[msg.lang] || "hi-IN";
    u.onend = () => { if (gen === call.gen) playNext(); }; u.onerror = u.onend;
    speechSynthesis.speak(u);
    setTimeout(() => { if (gen === call.gen && call.playing && !speechSynthesis.speaking) { call.gen++; playNext(); } }, 2500);
  } else playNext();
}
function stopAudio() {
  call.gen++; call.audioQ = []; call.playing = false;
  if (call.audio) { try { call.audio.pause(); } catch (e) { } call.audio = null; }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  renderScreen();
}
function afterAudio() {
  if (call.ask?.mode === "talk" && $("#autoMic")?.checked && !call.mic && !call.playing) startMic();
}

// ---- microphone: 16 kHz 16-bit mono PCM; stops by itself when the speaker pauses ---------------------
async function startMic() {
  if (call.mic || call.micStarting) return;
  if (!call.ws || call.ask?.mode !== "talk") { toast("The microphone answers spoken questions only.", "err"); return; }
  call.micStarting = true; stopAudio();
  const forAsk = call.ask;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    const AC = window.AudioContext || window.webkitAudioContext;
    let ctx, src;
    try { ctx = new AC({sampleRate: 16000}); src = ctx.createMediaStreamSource(stream); }
    catch (e) { if (ctx) ctx.close(); ctx = new AC(); src = ctx.createMediaStreamSource(stream); }
    const proc = ctx.createScriptProcessor(4096, 1, 1);
    const ratio = ctx.sampleRate / 16000, started = Date.now(), lead = [];
    let heard = false, quietSince = 0;
    const m = {stream, ctx, proc, src};
    proc.onaudioprocess = (e) => {
      if (call.mic !== m || !call.ws || call.ws.readyState !== 1) return;
      const input = e.inputBuffer.getChannelData(0), n = Math.floor(input.length / ratio), out = new Int16Array(n);
      let energy = 0;
      for (let i = 0; i < n; i++) {
        const a = Math.floor(i * ratio), b = Math.max(a + 1, Math.floor((i + 1) * ratio));
        let s = 0; for (let j = a; j < b; j++) s += input[j]; s /= (b - a);
        out[i] = Math.max(-1, Math.min(1, s)) * 32767; energy += s * s;
      }
      const level = Math.sqrt(energy / Math.max(1, n)), now = Date.now(), loud = level > 0.015;
      $$("#mlevel i").forEach((bar, i) => bar.style.height = `${Math.max(3, Math.min(22, level * 600 * (0.6 + ((i * 7) % 5) / 6)))}px`);
      if (loud && !heard) { heard = true; lead.forEach((buf) => call.ws.send(buf)); lead.length = 0; }
      if (heard) call.ws.send(out.buffer); else { lead.push(out.buffer); if (lead.length > 2) lead.shift(); }
      if (loud) quietSince = 0; else if (heard && !quietSince) quietSince = now;
      if ((heard && quietSince && now - quietSince > 1800) || (!heard && now - started > 9000) || now - started > 30000) stopMic(true);
    };
    src.connect(proc); proc.connect(ctx.destination);
    call.micStarting = false;
    if (call.ask !== forAsk) { closeMic(m); return; }
    call.mic = m;
    $("#micBtn").classList.add("rec"); $("#micBtn").lastChild.textContent = "Done";
    renderScreen();
  } catch (err) {
    call.micStarting = false;
    toast(`Microphone not available (${err.name}). Open the console on localhost or https, or type the answer.`, "err");
  }
}
function closeMic(m) { try { m.proc.disconnect(); m.src.disconnect(); m.stream.getTracks().forEach((t) => t.stop()); m.ctx.close(); } catch (e) { } }
function stopMic(send) {
  if (!call.mic) return;
  const m = call.mic; call.mic = null; closeMic(m);
  const b = $("#micBtn"); if (b) { b.classList.remove("rec"); b.lastChild.textContent = "Speak"; }
  if (send && call.ws?.readyState === 1) { call.ws.send(JSON.stringify({type: "speech_end"})); call.ask = null; }
  renderScreen();
}

// ================================================================================================
// Profiles: search by district, status, name or ID
// ================================================================================================
const STATUS = {new: "New", approved: "Approved", referred: "Referred", needs_info: "Needs info"};
const filters = {district: "", status: "", name: "", id: ""};

async function showPeople() {
  const el = $("#view");
  el.innerHTML = `<section class="card"><header><span class="ic">${icon("users")}</span><h3>Profiles</h3><span class="aside" id="peopleCount"></span></header><div class="body">
    <div class="stats" id="stats"></div>
    <form class="toolbar" id="find">
      <select class="in" id="fDistrict"><option value="">All districts</option>${cat.districts.map((d) => `<option value="${esc(d.code)}">${esc(d.name)} (${esc(d.state)})</option>`).join("")}</select>
      <select class="in" id="fStatus"><option value="">Any status</option>${Object.entries(STATUS).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select>
      <input class="in" id="fName" placeholder="Name">
      <input class="in" id="fId" placeholder="HunarVaani ID" style="width:150px">
      <button class="btn primary" type="submit">${icon("search")}Search</button>
    </form>
    <div class="table-wrap"><table><thead><tr><th>ID</th><th>Name</th><th>District</th><th>Via</th><th>Status</th><th>Date</th></tr></thead><tbody id="rows"></tbody></table></div>
  </div></section>`;
  paintIcons(el);
  $("#fDistrict").value = filters.district; $("#fStatus").value = filters.status; $("#fName").value = filters.name; $("#fId").value = filters.id;
  $("#find").onsubmit = (e) => { e.preventDefault(); load(); };
  ["#fDistrict", "#fStatus"].forEach((s) => $(s).onchange = load);
  api("/api/stats").then((s) => {
    const chips = [`<span class="chip">${s.people} people</span>`]
      .concat(Object.entries(s.by_status).map(([k, n]) => `<span class="chip ${esc(k)}">${esc(STATUS[k] || k)}: ${n}</span>`))
      .concat(Object.entries(s.sessions_today).map(([k, n]) => `<span class="chip">${esc(k)} today: ${n}</span>`));
    $("#stats").innerHTML = chips.join("");
  }).catch(fail);
  load();

  async function load() {
    Object.assign(filters, {district: $("#fDistrict").value, status: $("#fStatus").value, name: $("#fName").value.trim(), id: $("#fId").value.replace(/\D/g, "")});
    try {
      const rows = await api("/api/people?" + new URLSearchParams(filters));
      $("#peopleCount").textContent = `${rows.length} shown`;
      $("#rows").innerHTML = rows.length ? rows.map((r) => `<tr data-id="${esc(r.hv_id)}"><td class="mono">${esc(pretty(r.hv_id))}</td><td class="name">${esc(r.name)}</td>
        <td>${esc(r.district_name)}</td><td><span class="chip">${esc(r.channel)}</span></td><td><span class="chip ${esc(r.status)}">${esc(STATUS[r.status] || r.status)}</span></td><td>${esc(day(r.created))}</td></tr>`).join("")
        : `<tr><td colspan="6" class="empty">No records match. Make one with a live call.</td></tr>`;
      $$("#rows tr[data-id]").forEach((tr) => tr.onclick = () => location.hash = "person/" + tr.dataset.id);
    } catch (err) { fail(err); }
  }
}

// ================================================================================================
// Person page: the record in plain words, why these options, why not others; approve, edit, erase
// ================================================================================================
const occName = (c) => cat.occupations.find((o) => o.code === c)?.title || String(c);
const eduName = (e) => cat.education.find((x) => x.code === e)?.title || e || "";
const GENDER = {female: "Woman", male: "Man", other: "Prefers not to say"};
const HEALTH = {none: "None", some: "Some limits", severe: "Severe limits"};
const LEAN = {job: "Salaried job", own_work: "Own work", either: "Either"};

async function showPerson(id) {
  const el = $("#view");
  el.innerHTML = `<p class="tiny">Loading…</p>`;
  let p;
  try { p = await api("/api/person/" + encodeURIComponent(id)); }
  catch (err) { el.innerHTML = `<a class="back" href="#people">${icon("back")}Profiles</a><div class="card"><div class="empty">${esc(err.message)}</div></div>`; paintIcons(el); return; }
  renderPerson(p);
}

function renderPerson(p) {
  const el = $("#view"), pr = p.profile || {}, x = p.explain || {};
  const evidence = (pr.evidence || []).filter((e) => e.quote && !String(e.quote).startsWith("simulated"));
  el.innerHTML = `<a class="back" href="#people">${icon("back")}Profiles</a>
    <section class="card person-head">
      <div><h2>${esc(p.name)}</h2>
        <div class="meta"><span class="mono">${esc(pretty(p.hv_id))}</span><span class="chip ${esc(p.status)}">${esc(STATUS[p.status] || p.status)}</span>
          <span class="chip">${esc(p.channel)}</span><span class="chip">${esc({hi: "Hindi", mr: "Marathi", en: "English"}[p.language] || p.language)}</span>
          <span class="chip">${esc(p.district_name || "no district")}</span><span class="tiny">since ${esc(when(p.created))}</span></div></div>
      <div class="acts">
        <input class="in" id="stNote" placeholder="Note for the decision" style="width:190px">
        <button class="btn" data-status="approved">${icon("check")}Approve</button>
        <button class="btn amber" data-status="referred">${icon("route")}Refer</button>
        <button class="btn red" data-status="needs_info">${icon("help")}Needs info</button>
        <button class="btn" id="editBtn">${icon("edit")}Edit</button>
        <a class="btn" href="/api/person/${esc(p.hv_id)}/card" target="_blank" rel="noopener">${icon("print")}Card</a>
        <button class="btn red" id="eraseBtn">${icon("trash")}Erase</button>
      </div>
    </section>
    <div class="grid2">
      <div class="stack">
        <section class="card"><header><span class="ic violet">${icon("message")}</span><h3>In plain words</h3></header><div class="body">
          ${(x.lines || []).length ? `<ul class="plain">${x.lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : `<p class="tiny">—</p>`}</div></section>
        <section class="card"><header><span class="ic green">${icon("list")}</span><h3>Options offered</h3><span class="aside">score = gates × fit</span></header><div class="body">
          ${(p.options || []).length ? p.options.map((o, i) => optionCard(o, (x.options || [])[i])).join("") : `<p class="tiny">No options were saved.</p>`}</div></section>
        <section class="card"><header><span class="ic red">${icon("filter")}</span><h3>Why other work was left out</h3><span class="aside">with today's policy ${esc(x.policy || "")}</span></header><div class="body">
          ${(x.left_out || []).length ? `<div class="left-out">${x.left_out.map((o) => `<div><b>${esc(o.course)}</b> <small>${esc(o.centre)} · ${o.distance_km} km · fit ${o.fit.toFixed(2)}</small><br>${esc(o.because.join("; "))}</div>`).join("")}</div>` : `<p class="tiny">Nothing strong was held back.</p>`}</div></section>
        <section class="card"><header><span class="ic green">${icon("book")}</span><h3>Skills worth learning</h3></header><div class="body">
          ${(pr.skill_advice || []).length ? pr.skill_advice.map((a) => `<div class="opt"><b>${esc(a.skills.join(", "))}</b><div class="why">for ${esc(a.course)} · ${esc(a.gap)} gap · about ${a.weeks} weeks · ${esc(a.centre)}, ${a.distance_km} km</div></div>`).join("") : `<p class="tiny">None.</p>`}</div></section>
      </div>
      <div class="stack">
        <section class="card"><header><span class="ic">${icon("user")}</span><h3>Profile</h3></header><div class="body"><dl class="facts-list">
          <dt>Age · woman / man</dt><dd>${esc(pr.age ?? "—")} · ${esc(GENDER[pr.gender] || "—")}</dd>
          <dt>Studies</dt><dd>${esc(eduName(pr.education) || "—")}</dd>
          <dt>Work now</dt><dd>${esc((p.work || []).join(", ") || "—")}${pr.years ? ` · ${pr.years} yrs` : ""}</dd>
          <dt>Wants</dt><dd>${esc((p.wants || []).join(", ") || (cat.sectors.find((s) => s.code === pr.aspiration_sector)?.title) || "—")}</dd>
          <dt>Daily travel</dt><dd>${pr.radius_km ? `${esc(pr.radius_km)} km` : "—"}${pr.cannot_leave_home ? " · cannot leave home" : pr.hostel_ok ? " · hostel fine" : ""}</dd>
          <dt>Location</dt><dd>${pr.pin ? `PIN ${esc(pr.pin)} ` : ""}(${esc({device: "from the kiosk / phone line", asked: "asked", officer: "set by an officer"}[pr.location_from] || "—")})</dd>
          <dt>Health</dt><dd>${esc(HEALTH[pr.health] || "—")}</dd>
          <dt>Prefers</dt><dd>${esc(LEAN[pr.lean] || "—")}</dd>
          <dt>Longest course</dt><dd>${pr.max_weeks ? `${esc(pr.max_weeks)} weeks` : "any"}</dd>
          <dt>Said no to</dt><dd>${esc([...(pr.rejected_sectors || []), ...(pr.rejected_kinds || [])].join(", ") || "—")}</dd>
          <dt>Consent</dt><dd>${p.consent?.record_and_share ? "record and share" : "—"}${p.consent?.ai_training ? " · AI training" : ""}</dd>
        </dl></div></section>
        <section class="card"><header><span class="ic amber">${icon("sliders")}</span><h3>Weights for this person</h3><span class="aside">w × m</span></header><div class="body">
          ${bars((x.weights || []).map((w) => ({label: `${w.label} ×${w.m}`, v: w.share, text: pct(w.share)})), 1)}
          <p class="tiny" style="margin-top:8px">w is the officers' base weight; m (0.5 to 3) comes from the person's own words below.</p></div></section>
        <section class="card"><header><span class="ic amber">${icon("quote")}</span><h3>Their own words</h3></header><div class="body">
          ${evidence.length ? evidence.map((e) => `<p class="quote">“${esc(e.quote)}” <small>→ ${esc(e.factor || e.field)} · ${esc(e.strength)}${e.source ? ` · ${esc(e.source)}` : ""}</small></p>`).join("") : `<p class="tiny">No quotes.</p>`}</div></section>
        <section class="card"><header><span class="ic">${icon("help")}</span><h3>How the call was guided</h3></header><div class="body">
          ${(pr.question_plan || []).length ? `<ul class="tl">${pr.question_plan.map((q) => `<li><b>${esc(q.question)}</b><small>${esc(q.why)} · mood ${esc(q.mood)}</small></li>`).join("")}</ul>` : `<p class="tiny">—</p>`}</div></section>
        <section class="card"><header><span class="ic">${icon("message")}</span><h3>Conversation</h3></header><div class="body">
          ${(p.turns || []).filter((t) => ["speech", "key", "tradeoff", "review", "unclear"].includes(t.kind)).map((t) => `<div class="turn"><span>${esc(t.question)}</span><span>${esc(t.answer)}</span></div>`).join("") || `<p class="tiny">Turns are not logged (LOG_TURNS is off) or none yet.</p>`}</div></section>
        <section class="card"><header><span class="ic">${icon("clock")}</span><h3>Audit log</h3></header><div class="body">
          <ul class="tl">${(p.audit || []).slice().reverse().map((a) => `<li><b>${esc(a.action)}</b><small>${esc(when(a.ts))} · ${esc(a.actor)}${a.note ? ` · ${esc(a.note)}` : ""}</small></li>`).join("")}</ul></div></section>
      </div>
    </div>`;
  paintIcons(el);
  $$("[data-status]", el).forEach((b) => b.onclick = async () => {
    try {
      await api(`/api/person/${p.hv_id}/status`, {method: "POST", body: {status: b.dataset.status, note: $("#stNote").value}});
      toast(`Marked: ${STATUS[b.dataset.status]}`); showPerson(p.hv_id);
    } catch (err) { fail(err); }
  });
  $("#editBtn").onclick = () => editPerson(p);
  $("#eraseBtn").onclick = () => erasePerson(p);
}

function optionCard(o, ex) {
  const contrib = ex ? bars(ex.contrib.map((c) => ({label: c.label, v: c.part, text: `${c.f.toFixed(2)}×${pct(c.w)}`}))) : "";
  return `<div class="opt ${o.chosen ? "chosen" : ""}"><div class="opt-h"><span class="rank">${o.rank}</span><b>${esc(o.course)}</b>${o.chosen ? `<span class="chip good">${icon("check")}chosen</span>` : ""}<span class="score">${(+o.score).toFixed(2)}</span></div>
    <div class="why">${esc(ex ? ex.sentence : (o.reasons || []).join("; "))}</div>
    ${o.skill_gap?.length ? `<div class="tiny">Will learn: ${esc(o.skill_gap.join(", "))}</div>` : ""}
    ${contrib ? `<details><summary class="tiny" style="cursor:pointer">Fit by factor (f × w)</summary>${contrib}</details>` : ""}</div>`;
}

function dialog(html, onSubmit) {
  const dlg = $("#dlg");
  dlg.innerHTML = `<form method="dialog">${html}</form>`;
  paintIcons(dlg);
  const form = $("form", dlg);
  $$("[data-close]", dlg).forEach((b) => b.onclick = (e) => { e.preventDefault(); dlg.close(); });
  form.onsubmit = async (e) => {
    e.preventDefault();
    const btn = $("button[type=submit]", form); btn.disabled = true;
    try { if (await onSubmit(form) !== false) dlg.close(); } catch (err) { fail(err); } finally { btn.disabled = false; }
  };
  dlg.showModal();
}

function editPerson(p) {
  const pr = p.profile || {};
  const opt = (pairs, v, blank = "—") => `<option value="">${blank}</option>` + pairs.map(([k, t]) => `<option value="${esc(k)}" ${String(v ?? "") === String(k) ? "selected" : ""}>${esc(t)}</option>`).join("");
  const occ = (sel) => cat.occupations.map((o) => `<option value="${o.code}" ${sel.includes(o.code) ? "selected" : ""}>${esc(o.title)}</option>`).join("");
  dialog(`<h3>Edit ${esc(p.name)}</h3>
    <p class="tiny">Correct what was misheard. Every change is written to the audit log with the old and new value.</p>
    <div class="form-grid">
      <label>Name<input class="in" name="name" value="${esc(p.name)}" maxlength="40" required></label>
      <label>District<select class="in" name="district">${opt(cat.districts.map((d) => [d.code, d.name]), p.district)}</select></label>
      <label>Age<input class="in" name="age" type="number" min="14" max="80" value="${esc(pr.age ?? "")}"></label>
      <label>Woman / man<select class="in" name="gender">${opt(Object.entries(GENDER), pr.gender)}</select></label>
      <label>Studies<select class="in" name="education">${opt(cat.education.map((e) => [e.code, e.title]), pr.education)}</select></label>
      <label>Daily travel (km)<input class="in" name="radius_km" type="number" min="1" max="200" value="${esc(pr.radius_km ?? "")}"></label>
      <label>Health<select class="in" name="health">${opt(Object.entries(HEALTH), pr.health, "None")}</select></label>
      <label>Prefers<select class="in" name="lean">${opt(Object.entries(LEAN), pr.lean)}</select></label>
      <label>Years in their work<input class="in" name="years" type="number" min="0" max="60" value="${esc(pr.years ?? "")}"></label>
      <label>Longest course (weeks)<input class="in" name="max_weeks" type="number" min="1" max="104" value="${esc(pr.max_weeks ?? "")}"></label>
      <label class="full">Work they do (up to 3; Ctrl/⌘-click)<select class="in" name="occupation_codes" multiple>${occ(pr.occupation_codes || [])}</select></label>
      <label class="full">Work they want (up to 3)<select class="in" name="aspiration_codes" multiple>${occ(pr.aspiration_codes || [])}</select></label>
      <label class="full">Or a field they want<select class="in" name="aspiration_sector">${opt(cat.sectors.map((s) => [s.code, s.title]), pr.aspiration_sector)}</select></label>
      <label class="check"><input type="checkbox" name="cannot_leave_home" ${pr.cannot_leave_home ? "checked" : ""}> Cannot leave home</label>
      <label class="check"><input type="checkbox" name="hostel_ok" ${pr.hostel_ok ? "checked" : ""}> A hostel is fine</label>
      <label class="full">Why (goes to the audit log)<input class="in" name="note" placeholder="e.g. checked her documents"></label>
      <label class="check full"><input type="checkbox" name="rerank" checked> Rank the options again with these details</label>
    </div>
    <div class="dlg-acts"><button class="btn" data-close>Cancel</button><button class="btn primary" type="submit">${icon("save")}Save</button></div>`,
  async (f) => {
    const num = (n) => f[n].value === "" ? null : +f[n].value;
    const multi = (n) => Array.from(f[n].selectedOptions).map((o) => +o.value);
    if (multi("occupation_codes").length > 3 || multi("aspiration_codes").length > 3) { toast("Pick at most 3 kinds of work.", "err"); return false; }
    const body = {name: f.name.value.trim(), district: f.district.value || null, age: num("age"), gender: f.gender.value || null,
      education: f.education.value || null, radius_km: num("radius_km"), health: f.health.value || "none", lean: f.lean.value || null,
      years: num("years"), max_weeks: num("max_weeks"), occupation_codes: multi("occupation_codes"), aspiration_codes: multi("aspiration_codes"),
      aspiration_sector: f.aspiration_sector.value || null, cannot_leave_home: f.cannot_leave_home.checked,
      hostel_ok: f.cannot_leave_home.checked ? false : f.hostel_ok.checked, note: f.note.value, rerank: f.rerank.checked};
    if (!body.district) delete body.district;
    const r = await api(`/api/person/${p.hv_id}`, {method: "PATCH", body});
    toast(r.changed.length || r.reranked ? `Saved${r.changed.length ? ": " + r.changed.join(", ") : ""}${r.reranked ? " · ranked again" : ""}` : "Nothing changed");
    renderPerson(r.person);
  });
}

function erasePerson(p) {
  dialog(`<h3>Erase ${esc(p.name)}?</h3>
    <p>This deletes the profile, every answer, the options and the card file. It cannot be undone. One audit line stays, saying who erased it and when.</p>
    <label>Type the HunarVaani ID to confirm<input class="in mono" name="confirm" placeholder="${esc(pretty(p.hv_id))}" autocomplete="off" required></label>
    <label>Why<input class="in" name="note" placeholder="e.g. asked in person at the block office"></label>
    <div class="dlg-acts"><button class="btn" data-close>Keep</button><button class="btn danger" type="submit">${icon("trash")}Erase</button></div>`,
  async (f) => {
    await api(`/api/person/${p.hv_id}`, {method: "DELETE", body: {confirm: f.confirm.value.trim(), note: f.note.value}});
    toast(`${p.name} was erased.`);
    location.hash = "people";
  });
}

// ================================================================================================
// Ranking policy: base weights for all districts or one, the gates, learned proposals, history
// ================================================================================================
async function showPolicy() {
  const el = $("#view");
  let pol;
  try { pol = await api("/api/policy"); } catch (err) { fail(err); return; }
  const FACTORS = cat.factors.map((f) => [f.code, f.label]);
  const a = pol.active, g = a.gates, e = a.emphasis;
  el.innerHTML = `
    <section class="card" style="margin-bottom:16px"><div class="body" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
      <span class="ic green">${icon("check")}</span><div style="flex:1;min-width:200px"><b>Active policy <span class="mono">${esc(a.version)}</span></b>
      <p class="tiny">Score = G × Σ w·m·f. Officers set w and the gates G; m comes from the person's own words; f is how well an option fits. Every save is a new version.</p></div>
      ${Object.keys(a.district_overrides || {}).length ? `<span class="chip warn">Own weights in: ${esc(Object.keys(a.district_overrides).join(", "))}</span>` : ""}</div></section>
    <div class="grid2">
      <section class="card"><header><span class="ic">${icon("sliders")}</span><h3>Base weights (w)</h3></header><div class="body">
        <p class="tiny" style="margin-bottom:8px">How much each fit factor counts for everyone. The person's own priorities (m, 0.5 to 3) multiply these during the call.</p>
        ${FACTORS.map(([k, label]) => `<div class="wrow"><span><b>${esc(label)}</b><small>${k}</small></span><input type="range" min="1" max="60" value="${a.base_weights[k]}" data-w="${k}">
          <input class="in num" type="number" min="1" max="100" value="${a.base_weights[k]}" data-wn="${k}"><span class="share" data-ws="${k}"></span></div>`).join("")}
        <div class="toolbar" style="margin:14px 0 0"><select class="in" id="polDistrict"><option value="">All districts</option>${cat.districts.map((d) => `<option value="${esc(d.code)}">${esc(d.name)}</option>`).join("")}</select>
          <input class="in" id="polNote" placeholder="Why (goes to the history)" style="flex:1"><button class="btn primary" id="polSave">${icon("check")} Save weights</button></div>
      </div></section>
      <section class="card"><header><span class="ic red">${icon("filter")}</span><h3>Gates and priorities</h3></header><div class="body">
        <dl class="facts-list">
          <dt>Work capacity by age</dt><dd>${g.capacity_by_age.map(([age, cap]) => `${age}: ${cap}`).join(" · ")}</dd>
          <dt>Health limit takes off</dt><dd>some ${g.health_penalty.some} · severe ${g.health_penalty.severe}</dd>
          <dt>Each point of load above capacity</dt><dd>× ${g.work_base}</dd>
          <dt>Default daily travel</dt><dd>${g.default_radius_km} km (never below ${g.min_radius_km} km)</dd>
          <dt>Residential above</dt><dd>${g.residential_km} km</dd>
          <dt>Said no to this work</dt><dd>× ${g.rejected_factor}</dd>
          <dt>Unrelated to their work</dt><dd>× ${g.unrelated_factor}</dd>
          <dt>Removed when G is below</dt><dd>${g.drop_below}</dd>
          <dt>Priority multiplier m</dt><dd>${e.min} to ${e.max}</dd>
          <dt>Follow-up questions</dt><dd>at most ${a.questions.max_followups}, only if worth ≥ ${a.questions.min_value}</dd>
        </dl>
        <p class="tiny" style="margin-top:10px">Caste-linked work is offered only if the person brings it up (${(a.consent_only_codes || []).length} occupations).</p>
      </div></section>
    </div>
    <div class="grid2" style="margin-top:16px">
      <section class="card"><header><span class="ic violet">${icon("cpu")}</span><h3>Learned proposals</h3></header><div class="body">
        ${pol.proposals.length ? pol.proposals.map((x) => `<div class="opt" style="margin-bottom:8px"><b class="mono">${esc(x.file)}</b>
          <div class="why">${esc(JSON.stringify((x.report || {}).changes || {}))}</div><div><button class="btn sm" data-activate="${esc(x.file)}">Activate</button></div></div>`).join("")
          : `<p class="tiny">None yet. <span class="mono">scripts/learn.py</span> proposes new weights from real choices and verified outcomes; nothing goes live until an officer activates it, and a proposal that widens the gender gap is blocked.</p>`}
      </div></section>
      <section class="card"><header><span class="ic">${icon("clock")}</span><h3>History</h3></header><div class="body">
        ${pol.history.length ? `<ul class="tl">${pol.history.slice().reverse().map((h) => `<li><b class="mono">${esc(h.version)}</b><small>${esc(h.actor)}${h.note ? ` · ${esc(h.note)}` : ""}</small></li>`).join("")}</ul>`
          : `<p class="tiny">The default policy has not been changed yet.</p>`}
      </div></section>
    </div>`;
  paintIcons(el);
  const shares = () => {
    const w = Object.fromEntries(FACTORS.map(([k]) => [k, +$(`[data-wn="${k}"]`).value || 0]));
    const total = Object.values(w).reduce((s, x) => s + x, 0) || 1;
    FACTORS.forEach(([k]) => $(`[data-ws="${k}"]`).textContent = pct(w[k] / total));
    return w;
  };
  $$("[data-w]", el).forEach((r) => r.oninput = () => { $(`[data-wn="${r.dataset.w}"]`).value = r.value; shares(); });
  $$("[data-wn]", el).forEach((n) => n.oninput = () => { $(`[data-w="${n.dataset.wn}"]`).value = n.value; shares(); });
  shares();
  $("#polSave").onclick = async () => {
    try {
      const r = await api("/api/policy", {method: "POST", body: {base_weights: shares(), district: $("#polDistrict").value, note: $("#polNote").value}});
      toast(`Saved as ${r.version}`);
      showPolicy();
    } catch (err) { fail(err); }
  };
  $$("[data-activate]", el).forEach((b) => b.onclick = async () => {
    try { const r = await api("/api/policy/activate", {method: "POST", body: {file: b.dataset.activate}}); toast(`Activated ${r.version}`); showPolicy(); }
    catch (err) { fail(err); }
  });
}

window.addEventListener("DOMContentLoaded", boot);
