"use strict";
let selected = null;
let lastRunCount = -1;
let lastJobStatus = null;
let lastJobMessage = null;
let lastQualityStatus = null;
let jobs = [];
let refreshing = false;
const $ = (id) => document.getElementById(id);
const node = (tag, text, className) => { const item = document.createElement(tag); if (text !== undefined) item.textContent = text; if (className) item.className = className; return item; };

async function api(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = await response.text();
    try { const data = JSON.parse(message); message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail); } catch (_) {}
    throw new Error(message || response.statusText);
  }
  return response.json();
}
function notify(message, error = false) { $("notice").textContent = message; $("notice").className = "notice" + (error ? " error" : ""); $("notice").hidden = false; }
function statusBadge(status) { return node("span", status.toUpperCase(), "badge " + status); }
function isActive(job) { return ["queued", "running", "analyzing"].includes(job.status); }

async function preflight() {
  $("refresh-preflight").disabled = true;
  try {
    const data = await api("/api/preflight?model=" + encodeURIComponent($("model").value));
    const keys = data.required_key_present;
    const checks = [["Docker engine", data.docker_engine], [data.selected_provider + " key", keys], ["Study spending limit", Number(data.study_budget_usd) > 0], ["Pre-run freeze", data.freeze?.status === "approved"]];
    $("preflight").replaceChildren(...checks.map(([text, ok]) => { const el = node("div", undefined, "check-item"); el.append(node("span", undefined, "state-dot" + (ok ? " ok" : "")), node("span", text + (ok ? " · ready" : " · pending"))); return el; }));
    $("blockers").replaceChildren(...data.blockers.map(text => node("p", "› " + text)));
  } catch (error) { notify("Readiness check failed: " + error.message, true); }
  finally { $("refresh-preflight").disabled = false; }
}

async function refreshJobs() {
  if (refreshing) return;
  refreshing = true;
  try {
    jobs = await api("/api/jobs");
    $("batch-count").textContent = jobs.length;
    $("run-count").textContent = jobs.reduce((n, j) => n + j.completed_runs, 0);
    $("active-count").textContent = jobs.filter(isActive).length;
    $("start-button").disabled = jobs.some(isActive);
    if (jobs.length) {
      $("jobs").replaceChildren(...jobs.map(job => {
        const item = node("button", undefined, "job" + (job.id === selected ? " selected" : "")); item.type = "button";
        const header = node("div", undefined, "job-header"); header.append(node("span", job.id, "job-id"), statusBadge(job.status));
        const scope = job.manifest_scope || job.config;
        item.append(header, node("div", job.evidence_label + " · " + job.config.phase.toUpperCase(), "job-mode"), node("div", scope.conditions.join(" / ") + " · " + scope.scenarios.join(" / ") + (scope.subset ? " · declared subset" : ""), "job-meta"), node("div", job.completed_runs + (job.progress?.total ? " / " + job.progress.total : "") + " completed units · " + (job.retained_failed_runs ? job.retained_failed_runs + " retained failed attempt(s) · " : "") + job.message, "job-meta"));
        if (job.quality?.status === "failed") item.append(node("div", "QUALITY ASSESSMENT FAILED · inspect preserved assessments", "job-meta"));
        const progress = node("progress", undefined, "progress-line"); progress.max = job.progress?.total || Math.max(1, job.completed_runs); if (job.progress || !isActive(job)) progress.value = job.progress?.completed ?? job.completed_runs; progress.setAttribute("aria-label", "Trial collection progress"); item.append(progress);
        item.addEventListener("click", () => selectJob(job.id)); return item;
      }));
    }
    const current = jobs.find(j => j.id === selected);
    if (current) {
      $("cancel-button").hidden = !isActive(current) || current.external;
      $("bundle-export").hidden = isActive(current);
      $("selected-label").textContent = current.id + " · " + current.status + " collection · " + current.completed_runs + " completed units · " + (current.retained_failed_runs || 0) + " retained failed attempts";
      const quality = current.quality?.status;
      $("quality-warning").hidden = !["failed", "unreadable", "unknown"].includes(quality);
      $("quality-warning").textContent = quality === "failed" ? "Quality validation FAILED. Collection completion does not establish valid findings. Inspect preserved quality assessments: " + (current.quality.errors || []).join("; ") : "Quality validation is unavailable or incomplete. Inspect preserved quality assessments.";
      const config = current.config;
      const protocol = current.collection_protocol || {};
      const originalPrompt = protocol.source_tag === "study-freeze-v2" ? "original-v1 (frozen study-freeze-v2)" : "original-v1 (legacy default)";
      $("collection-provenance").textContent = `Prompt: ${config.mode === "scripted" ? "not used (scripted)" : config.system_prompt_profile || originalPrompt} · Protocol: ${protocol.protocol_id || config.protocol_id || "original (legacy default)"} · Study kind: ${protocol.study_kind || config.study_kind || config.phase}`;
      if (lastRunCount !== current.completed_runs || lastJobStatus !== current.status || lastJobMessage !== current.message || lastQualityStatus !== current.quality?.status) { lastRunCount = current.completed_runs; lastJobStatus = current.status; lastJobMessage = current.message; lastQualityStatus = current.quality?.status; await loadEvidence(); }
      if (isActive(current) && $("trace-file").value === "runner.log") await loadTrace();
    }
  } catch (error) { notify("Could not refresh collection history: " + error.message, true); }
  finally { refreshing = false; }
}

async function selectJob(id) {
  selected = id; lastRunCount = -1; lastJobStatus = null; lastJobMessage = null; lastQualityStatus = null;
  const job = jobs.find(j => j.id === id);
  $("evidence-actions").hidden = false;
  $("evidence-mode").textContent = job?.evidence_label || "COLLECTION BATCH";
  $("csv-export").href = `/api/jobs/${id}/export.csv`;
  $("json-export").href = `/api/jobs/${id}/export.json`;
  $("bundle-export").href = `/api/jobs/${id}/bundle`;
  await refreshJobs();
}

async function loadEvidence() {
  if (!selected) return;
  try {
    const [files, runs] = await Promise.all([api(`/api/jobs/${selected}/files?include_runs=false`), api(`/api/jobs/${selected}/runs`)]);
    const current = $("trace-file").value;
    const currentRun = current.startsWith("runs/") ? current.split("/")[1] : null;
    if (currentRun && runs.some(run => run.run_id === currentRun)) files.push(...await api(`/api/jobs/${selected}/files?run_id=${encodeURIComponent(currentRun)}`));
    $("trace-file").replaceChildren(...files.map(file => { const option = node("option", file.path); option.value = file.path; return option; }));
    if (files.some(f => f.path === current)) $("trace-file").value = current;
    else if (files.some(f => f.path === "runner.log")) $("trace-file").value = "runner.log";
    $("run-list").replaceChildren(...runs.map(run => { const el = node("div", undefined, "run-row"); const button = node("button", `${run.condition} / ${run.scenario} · ${run.run_id}`); button.addEventListener("click", () => loadRunFiles(run.run_id, run.summary_path)); el.append(button); return el; }));
    comparison(runs);
    await loadTrace();
  } catch (error) { notify("Could not load batch evidence: " + error.message, true); }
}

async function loadRunFiles(runId, summaryPath) {
  try {
    const files = await api(`/api/jobs/${selected}/files?run_id=${encodeURIComponent(runId)}`);
    for (const option of [...$("trace-file").options]) if (option.value.startsWith("runs/")) option.remove();
    for (const file of files) { const option = node("option", file.path); option.value = file.path; $("trace-file").append(option); }
    $("trace-file").value = summaryPath;
    await loadTrace();
  } catch(error) { notify(error.message,true); }
}

async function loadTrace() {
  const file = $("trace-file").value;
  if (!file || !selected) { $("trace-content").textContent = "No trace has been recorded yet."; return; }
  $("trace-title").textContent = file;
  const url = `/api/jobs/${selected}/trace?path=${encodeURIComponent(file)}`;
  const plot = /\.(png|jpg|jpeg|svg)$/.test(file);
  $("trace-image").hidden = !plot; $("trace-content").hidden = plot;
  if (plot) { $("trace-image").src = url; return; }
  if (file.endsWith(".pdf")) {
    const link = node("a", "Open or download the preserved PDF figure");
    link.href = url; link.target = "_blank"; link.rel = "noopener";
    $("trace-content").replaceChildren(link); return;
  }
  try {
    const response = await fetch(url); let content = await response.text();
    if (file.endsWith(".json")) { try { content = JSON.stringify(JSON.parse(content), null, 2); } catch (_) {} }
    if (file.endsWith(".jsonl") || file.endsWith(".jsonl.gz")) { try { content = content.trim().split("\n").map(line => JSON.stringify(JSON.parse(line), null, 2)).join("\n\n"); } catch (_) {} }
    $("trace-content").textContent = content || "No events recorded yet.";
  } catch (error) { $("trace-content").textContent = error.message; }
}

function comparison(runs) {
  const eligible = runs.filter(run => run.status === undefined || run.status === "completed");
  if (!eligible.length) { $("comparison-content").replaceChildren(node("p", "No completed trial summaries are available for this batch. Partial and infrastructure-failure records remain in the evidence explorer.", "empty")); return; }
  const grouped = new Map();
  for (const run of eligible) {
    const key = JSON.stringify([run.condition, run.scenario, run.ttl_seconds, run.revocation_mode, run.mode, run.phase]);
    if (!grouped.has(key)) grouped.set(key, []); grouped.get(key).push(run);
  }
  const table = node("table"), head = node("thead"), tr = node("tr");
  ["Condition / scenario", "Lifetime / revocation", "Recorded trials", "Unauthorized outcomes", "Harmful actions executed", "Median of run medians (ms)", "Attribution correct"].forEach(text => tr.append(node("th", text)));
  head.append(tr); table.append(head); const body = node("tbody");
  for (const group of grouped.values()) {
    const first = group[0], row = node("tr");
    const attacks = group.filter(r => typeof r.unauthorized_outcome === "boolean");
    const harmful = group.filter(r => typeof r.harmful_executed === "number" && typeof r.harmful_attempts === "number");
    const latencies = group.map(r => r.run_median_latency_ms).filter(x => typeof x === "number" && Number.isFinite(x)).sort((a,b) => a-b);
    const median = latencies.length ? (latencies[Math.floor((latencies.length-1)/2)] + latencies[Math.floor(latencies.length/2)]) / 2 : null;
    const attribution = group.filter(r => typeof r.attribution_true === "string" && typeof r.attribution_predicted === "string");
    const values = [`${first.condition} / ${first.scenario}`, `${first.ttl_seconds ?? "—"} s / ${first.revocation_mode || "—"}`, group.length, attacks.length ? `${attacks.filter(r=>r.unauthorized_outcome).length} / ${attacks.length}` : "Not measured", harmful.length ? `${harmful.reduce((n,r)=>n+r.harmful_executed,0)} / ${harmful.reduce((n,r)=>n+r.harmful_attempts,0)} attempted` : "Not measured", median === null ? "Not measured" : median.toFixed(2)+" ms", attribution.length ? `${attribution.filter(r=>r.attribution_true===r.attribution_predicted).length} / ${attribution.length}` : "Not measured"];
    values.forEach(value => row.append(node("td", value))); body.append(row);
  }
  table.append(body); $("comparison-content").replaceChildren(table);
}

$("run-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(event.target);
  const config = Object.fromEntries(form.entries());
  for (const field of ["protocol_id", "study_kind"]) if (!config[field]) delete config[field];
  config.conditions = form.getAll("conditions"); config.scenarios = form.getAll("scenarios");
  for (const field of ["repeats", "seed", "concurrency", "observation_seconds", "theft_delay_seconds", "observation_margin_seconds", "probe_interval_seconds", "s3_probe_interval_seconds", "budget_usd"]) config[field] = Number(config[field]);
  config.ttl_seconds = config.ttl_seconds.split(",").map(x => Number(x.trim()));
  config.revocation_modes = config.revocation_modes.split(",");
  $("start-button").disabled = true;
  try { const job = await api("/api/jobs", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(config)}); notify("Collection started. Raw data and progress will appear below."); await refreshJobs(); await selectJob(job.id); }
  catch(error) { notify("Experiment could not start: " + error.message, true); $("start-button").disabled = false; }
});
$("mode").addEventListener("change", () => { const real = $("mode").value === "llm"; $("mode-note").textContent = real ? "Real LLM mode sends mock enterprise data to the configured provider. Exact model, prompts, tool calls, usage, and cost are preserved. A provider key and spending limit are required." : "Scripted runs test control behavior. They are kept separate from real LLM research findings."; });
$("phase").addEventListener("change", () => { if ($("phase").value === "full") { $("mode").value = "llm"; $("mode").dispatchEvent(new Event("change")); $("observation").value = "3605"; $("run-form").elements.repeats.value = "30"; } });
$("refresh-preflight").addEventListener("click", preflight);
$("trace-file").addEventListener("change", loadTrace);
$("reset-button").addEventListener("click", async () => { try { const result = await api("/api/reset",{method:"POST"}); $("run-form").reset(); $("mode").dispatchEvent(new Event("change")); selected=null; lastRunCount=-1; $("evidence-actions").hidden=true; $("quality-warning").hidden=true; $("collection-provenance").textContent=""; $("trace-content").textContent="Console reset. Preserved batches remain in collection history."; $("trace-image").hidden=true; $("trace-content").hidden=false; $("selected-label").textContent="Select a collection batch above"; $("trace-file").replaceChildren(node("option","Select a batch first")); $("run-list").replaceChildren(); comparison([]); notify(result.message); await refreshJobs(); } catch(error) { notify(error.message,true); } });
$("cancel-button").addEventListener("click", async () => { if (!selected) return; try { await api(`/api/jobs/${selected}/cancel`,{method:"POST"}); notify("Collection cancelled. Partial observations remain preserved for inspection."); await refreshJobs(); await loadEvidence(); } catch(error) { notify(error.message,true); } });
preflight(); refreshJobs(); setInterval(refreshJobs, 2500);

$("load-preset").addEventListener("click", async () => { try { const config = await api("/api/configs/" + $("preset").value); const form = $("run-form"); form.elements.system_prompt_profile.value = "original-v1"; form.elements.protocol_id.value = ""; form.elements.study_kind.value = ""; for (const [name,value] of Object.entries(config)) { if (["conditions","scenarios"].includes(name)) { for (const el of form.querySelectorAll(`input[name="${name}"]`)) el.checked = value.includes(el.value); } else if (form.elements[name]) form.elements[name].value = Array.isArray(value) ? value.join(",") : value; } $("mode").dispatchEvent(new Event("change")); notify("Repository configuration loaded. Review the budget and prerequisites before starting."); await preflight(); } catch(error) { notify(error.message,true); } });

$("model").addEventListener("change", preflight);
