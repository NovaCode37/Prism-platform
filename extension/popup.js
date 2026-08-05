const DEFAULT_URL = "https://getprism.su";
const $ = (id) => document.getElementById(id);
const t = (k, f) => chrome.i18n.getMessage(k) || f;

document.querySelectorAll("[data-i18n]").forEach((el) => {
  const m = chrome.i18n.getMessage(el.getAttribute("data-i18n"));
  if (m) el.textContent = m;
});
document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
  const m = chrome.i18n.getMessage(el.getAttribute("data-i18n-ph"));
  if (m) el.setAttribute("placeholder", m);
});

function baseUrl(url) {
  let u = (url || DEFAULT_URL).trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(u)) u = "https://" + u;
  return u;
}
function mk(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text != null) el.textContent = text;
  return el;
}
function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const formView = $("formView"), scanView = $("scanView");
const urlInput = $("url"), keyInput = $("apikey"), targetInput = $("target"), saved = $("saved");
const bar = $("bar"), barWrap = $("barWrap"), logEl = $("log"), statusEl = $("status");
const recentEl = $("recentTargets");

const RECENT_KEY = "recentTargets";
const MAX_RECENT = 5;

function renderRecentTargets(list) {
  clear(recentEl);
  recentEl.hidden = !list.length;
  list.forEach((target) => {
    const chip = mk("button", "chip", target);
    chip.type = "button";
    chip.addEventListener("click", () => {
      targetInput.value = target;
      targetInput.focus();
    });
    recentEl.appendChild(chip);
  });
}

function loadRecentTargets() {
  chrome.storage.local.get({ [RECENT_KEY]: [] }, (data) => renderRecentTargets(data[RECENT_KEY]));
}

function saveRecentTarget(target) {
  chrome.storage.local.get({ [RECENT_KEY]: [] }, (data) => {
    const list = data[RECENT_KEY].filter((t) => t.toLowerCase() !== target.toLowerCase());
    list.unshift(target);
    const trimmed = list.slice(0, MAX_RECENT);
    chrome.storage.local.set({ [RECENT_KEY]: trimmed });
    renderRecentTargets(trimmed);
  });
}

loadRecentTargets();

function showForm() { formView.hidden = false; scanView.hidden = true; }
function showScan() { formView.hidden = true; scanView.hidden = false; }

chrome.storage.sync.get({ instanceUrl: DEFAULT_URL, apiKey: "" }, ({ instanceUrl, apiKey }) => {
  urlInput.value = instanceUrl;
  keyInput.value = apiKey;
});
$("save").addEventListener("click", () => {
  chrome.storage.sync.set({ instanceUrl: urlInput.value.trim(), apiKey: keyInput.value.trim() }, () => {
    saved.textContent = t("savedOk", "Saved") + " ✓";
    setTimeout(() => (saved.textContent = ""), 1500);
  });
});

chrome.storage.local.get({ pendingTarget: null, activeScan: null }, ({ pendingTarget, activeScan }) => {
  if (pendingTarget) {
    chrome.storage.local.remove("pendingTarget");
    chrome.storage.sync.get({ instanceUrl: DEFAULT_URL, apiKey: "" }, ({ instanceUrl, apiKey }) => {
      start(pendingTarget, baseUrl(instanceUrl), apiKey);
    });
  } else if (activeScan && activeScan.scanId) { showScan(); resume(activeScan); }
  else showForm();
});

$("back").addEventListener("click", () => {
  chrome.storage.local.remove("activeScan");
  clear(logEl); clear($("results")); $("error").hidden = true;
  showForm();
});

function runScan() {
  const target = targetInput.value.trim();
  if (!target) return;
  const server = baseUrl(urlInput.value);
  const apiKey = keyInput.value.trim();
  chrome.storage.sync.set({ instanceUrl: urlInput.value.trim(), apiKey });
  saveRecentTarget(target);
  start(target, server, apiKey);
}
$("scan").addEventListener("click", runScan);
targetInput.addEventListener("keydown", (e) => { if (e.key === "Enter") runScan(); });

function setStatus(text, cls) { statusEl.textContent = text; statusEl.className = "status" + (cls ? " " + cls : ""); }
function fail(msg) {
  setStatus(t("failed", "Scan failed"), "err");
  barWrap.classList.add("done");
  const e = $("error"); e.hidden = false; e.textContent = msg;
}

let seen;
function resetScanUi(target) {
  seen = new Set();
  clear(logEl); clear($("results")); $("error").hidden = true;
  barWrap.classList.remove("done"); bar.style.width = "0";
  $("scanTarget").textContent = target;
}
function pushLog(msg) {
  const key = `${msg.type}:${msg.module}`;
  if (seen.has(key)) return; seen.add(key);
  let line;
  if (msg.type === "module_start") line = mk("div", null, `→ ${msg.module}`);
  else {
    const detail = msg.reason || msg.error;
    const map = { ok: ["ok", "✓"], skipped: ["skip", "⊘"], rate_limited: ["rl", "⏳"], error: ["err", "✗"] };
    const [cls, mark] = map[msg.status] || ["ok", "✓"];
    line = mk("div", cls, `${mark} ${msg.module}${detail ? " — " + detail : ""}`);
  }
  logEl.appendChild(line); logEl.scrollTop = logEl.scrollHeight;
  const done = [...seen].filter((k) => k.startsWith("module_done")).length;
  bar.style.width = Math.min(92, 10 + done * 7) + "%";
}

async function start(target, server, apiKey) {
  showScan(); resetScanUi(target); setStatus(t("scanning", "Scanning…"));
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;
  let scanId;
  try {
    const r = await fetch(`${server}/api/scan`, { method: "POST", headers, body: JSON.stringify({ target, scan_type: "auto", modules: [] }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || data.error || `HTTP ${r.status}`);
    scanId = data.scan_id;
  } catch (e) {
    const msg = e.message || "";
    if (/api key|\b40[13]\b/i.test(msg)) return fail("This PRISM instance needs an API key. Add it in the popup, or set Server to your own instance.");
    return fail(`Cannot reach PRISM at ${server} — ${msg}`);
  }
  const active = { scanId, server, apiKey, target };
  chrome.storage.local.set({ activeScan: active });
  poll(active);
}

function resume(active) {
  resetScanUi(active.target); setStatus(t("scanning", "Scanning…"));
  poll(active);
}

async function poll(active) {
  const headers = active.apiKey ? { "X-API-Key": active.apiKey } : {};
  for (let i = 0; i < 200; i++) {
    let data;
    try { data = await (await fetch(`${active.server}/api/scan/${active.scanId}`, { headers })).json(); }
    catch { await sleep(1500); continue; }
    (data.progress || []).forEach(pushLog);
    if (data.status === "completed") {
      bar.style.width = "100%"; setTimeout(() => barWrap.classList.add("done"), 400);
      setStatus(t("complete", "Complete"), "ok");
      render(data.results || {}, active.server, active.target);
      return;
    }
    if (data.status === "error") return fail(data.error || "Scan failed.");
    await sleep(1500);
  }
  fail("Timed out.");
}

const SKIP = new Set(["graph", "report_path", "map_data", "opsec_score", "opsec", "dorks"]);
const TITLES = { dns: "DNS", geoip: "GeoIP", whois: "WHOIS", cert_transparency: "Subdomains (CT)", shodan: "Shodan", virustotal: "VirusTotal", abuseipdb: "AbuseIPDB", breaches: "Breaches", emailrep: "Email reputation", smtp: "SMTP", blackbird: "Accounts", maigret: "Maigret", telegram: "Telegram", censys: "Censys", wayback: "Wayback", phone: "Phone", github: "GitHub", gravatar: "Gravatar", onion: "Dark web", website: "Website" };
const scoreColor = (s) => (s >= 71 ? "#3fb950" : s >= 51 ? "#d29922" : "#f85149");

function render(results, server, target) {
  const root = $("results"); clear(root);
  const opsec = results.opsec_score || results.opsec;
  if (opsec && typeof opsec.score === "number") {
    const c = scoreColor(opsec.score);
    const box = mk("div", "opsec");
    const score = mk("div", "score", String(opsec.score)); score.style.color = c;
    const meta = mk("div");
    meta.appendChild(mk("div", "meta", t("opsecScore", "OPSEC score")));
    const risk = mk("div", "risk", opsec.risk_level || ""); risk.style.color = c;
    meta.appendChild(risk);
    box.appendChild(score); box.appendChild(meta); root.appendChild(box);

    root.appendChild(mk("div", "section-title", t("findings", "Findings")));
    const findings = opsec.all_findings || [];
    if (findings.length) findings.forEach((f) => {
      const d = mk("div", "finding");
      d.appendChild(mk("span", "sev " + f.severity, f.severity));
      d.appendChild(mk("span", null, f.message));
      root.appendChild(d);
    });
    else root.appendChild(mk("div", "empty", t("noFindings", "No notable findings")));
  }

  Object.keys(results).forEach((key) => {
    if (SKIP.has(key)) return;
    const card = moduleCard(key, results[key]);
    if (card) root.appendChild(card);
  });

  const full = mk("a", "full", t("openFull", "Open full report"));
  full.href = `${server}/?target=${encodeURIComponent(target)}`;
  full.target = "_blank"; full.rel = "noreferrer";
  root.appendChild(full);
}

function moduleCard(name, obj) {
  const rows = [];
  if (Array.isArray(obj)) {
    if (!obj.length) return null;
    rows.push(["found", String(obj.filter((x) => x && x.status === "found").length || obj.length)]);
  } else if (obj && typeof obj === "object") {
    if (obj.error && Object.keys(obj).filter((k) => obj[k] != null && k !== "error").length === 0) return null;
    for (const [k, v] of Object.entries(obj)) {
      if (v == null || k === "status" || k === "status_reason") continue;
      if (typeof v === "object") {
        if (Array.isArray(v)) { if (v.length) rows.push([k, v.length <= 8 && v.every((x) => typeof x !== "object") ? v : String(v.length)]); }
        else { for (const [sk, sv] of Object.entries(v)) { if (Array.isArray(sv) && sv.length && sv.every((x) => typeof x !== "object")) rows.push([sk, sv]); if (rows.length >= 8) break; } }
        continue;
      }
      rows.push([k, String(v)]); if (rows.length >= 8) break;
    }
  } else return null;
  if (!rows.length) return null;

  const card = mk("div", "card");
  card.appendChild(mk("h3", null, TITLES[name] || name));
  rows.forEach(([k, v]) => {
    const row = mk("div", "row");
    row.appendChild(mk("span", "k", k));
    const val = mk("span", "v");
    if (Array.isArray(v)) v.slice(0, 8).forEach((x) => val.appendChild(mk("span", "tag", String(x))));
    else val.textContent = v;
    row.appendChild(val);
    card.appendChild(row);
  });
  return card;
}
