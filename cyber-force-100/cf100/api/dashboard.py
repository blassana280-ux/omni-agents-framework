"""Tableau de bord HTML embarqué — aucune dépendance, aucun CDN.

Une page unique servie par GET /dashboard : HTML + CSS + JavaScript
vanilla qui interrogent l'API locale (/health, /divisions, /agents,
/evaluation, /evidence/verify). Aucune ressource externe : la page
fonctionne hors ligne et n'exfiltre rien. Toute donnée interpolée en
HTML est échappée (défense XSS en profondeur).
"""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cyber Force 100 — Tableau de bord</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #0d1117;
         color: #e6edf3; padding: 1.5rem; }
  h1 { font-size: 1.4rem; margin-bottom: .25rem; }
  h2 { font-size: 1rem; margin: 1.5rem 0 .5rem; color: #9ecbff; }
  .sub { color: #8b949e; font-size: .85rem; margin-bottom: 1rem; }
  .cards { display: grid; gap: .75rem;
           grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
  .card { background: #161b22; border: 1px solid #30363d;
          border-radius: 8px; padding: .9rem; }
  .card .num { font-size: 1.6rem; font-weight: 600; }
  .card .lab { color: #8b949e; font-size: .75rem; text-transform:
               uppercase; letter-spacing: .04em; }
  .bad .num { color: #f85149; } .ok .num { color: #3fb950; }
  table { border-collapse: collapse; width: 100%; font-size: .82rem; }
  th, td { text-align: left; padding: .4rem .5rem;
           border-bottom: 1px solid #21262d; }
  th { color: #8b949e; font-weight: 500; }
  .tag { padding: .1rem .45rem; border-radius: 99px; font-size: .72rem; }
  .v-op { background: #1f4d2b; color: #3fb950; }
  .v-sur { background: #4d3f1f; color: #d29922; }
  .v-ina { background: #2b2b33; color: #8b949e; }
  .v-def { background: #4d1f1f; color: #f85149; }
  #err { color: #f85149; margin-top: 1rem; }
</style>
</head>
<body>
<h1>Cyber Force 100</h1>
<p class="sub">Plateforme de cybersécurité défensive — 100 agents,
10 divisions, autonomie encadrée.</p>

<div class="cards" id="summary"></div>
<h2>Divisions</h2>
<table id="divisions"><thead><tr>
  <th>Code</th><th>Nom</th><th>Agents</th></tr>
</thead><tbody></tbody></table>
<h2>Évaluation des agents</h2>
<table id="eval"><thead><tr>
  <th>Agent</th><th>Division</th><th>État</th>
  <th>Exécutées</th><th>Échecs</th><th>Verdict</th></tr>
</thead><tbody></tbody></table>
<h2>Chaîne de preuves</h2>
<div class="cards" id="evidence"></div>
<p id="err"></p>

<script>
"use strict";
const TAGS = {"opérationnel": "v-op", "à surveiller": "v-sur",
              "inactif": "v-ina", "défaillant": "v-def"};
const esc = s => String(s).replace(/[&<>"']/g,
  c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;",
         '"': "&quot;", "'": "&#39;"}[c]));
function card(num, lab, cls) {
  return `<div class="card ${cls || ""}"><div class="num">${esc(num)}</div>
          <div class="lab">${esc(lab)}</div></div>`;
}
async function jget(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + " -> HTTP " + r.status);
  return r.json();
}
async function main() {
  const health = await jget("/health");
  document.getElementById("summary").innerHTML =
    card(health.divisions, "divisions") +
    card(health.agents, "agents") +
    card(health.status, "état", health.status === "ok" ? "ok" : "bad");
  const divisions = await jget("/divisions");
  document.querySelector("#divisions tbody").innerHTML = divisions.map(d =>
    `<tr><td>${esc(d.code)}</td><td>${esc(d.name)}</td>
     <td>${esc(d.agents.length)}</td></tr>`
  ).join("");
  const evaluation = await jget("/evaluation");
  document.querySelector("#eval tbody").innerHTML =
    evaluation.agents.slice(0, 100).map(a =>
    `<tr><td>${esc(a.id)}</td><td>${esc(a.division)}</td>
     <td>${esc(a.state)}</td>
     <td>${esc(a.tasks_done)}</td><td>${esc(a.tasks_failed)}</td>
     <td><span class="tag ${TAGS[a.verdict] || "v-ina"}">${esc(a.verdict)}
     </span></td></tr>`).join("");
  const evidence = await jget("/evidence/verify");
  document.getElementById("evidence").innerHTML =
    card(evidence.ok ? "INTACTE" : "CASSÉE", "chaîne de preuves",
         evidence.ok ? "ok" : "bad") +
    card(evidence.entries ?? 0, "entrées scellées");
}
main().catch(e => {
  document.getElementById("err").textContent =
    "Erreur de chargement : " + e.message;
});
</script>
</body>
</html>
"""
