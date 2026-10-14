const pct = value => `${Math.round(value * 100)}%`;
let run;

function siloMarkup(silo) {
  const evidence = silo.evidence.map(item => `<li>${item}</li>`).join("");
  return `<article class="silo ${silo.id}">
    <h3>SILO ${silo.name.toUpperCase()}</h3>
    <span class="role">${silo.role}</span>
    <ul>${evidence}</ul>
    <div class="readout">
      <span>LIKELY ROOT</span><b>${pct(silo.result.selected_probability)}</b>
      <span>EVIDENCE SUFFICIENCY</span><b>${silo.result.sufficiency.toFixed(2)} / 3</b>
      <span>ACTION SIGNAL</span><b>${pct(silo.result.requires_action)}</b>
      <span>CONTRADICTION</span><b>${pct(silo.result.material_contradiction)}</b>
    </div>
  </article>`;
}

function disconnect() {
  document.querySelector("#stage").classList.remove("connected");
  document.querySelector("#result-panel").classList.add("hidden");
  document.querySelector("#network-state").textContent = "ISOLATED";
  document.querySelector("#connect").hidden = false;
  document.querySelector("#confidence-bar").style.width = "0";
}

function connect() {
  document.querySelector("#stage").classList.add("connected");
  document.querySelector("#network-state").textContent = "CONNECTED";
  document.querySelector("#connect").hidden = true;
  window.setTimeout(() => {
    document.querySelector("#result-panel").classList.remove("hidden");
    document.querySelector("#confidence-bar").style.width = pct(run.connected.selected_probability);
  }, 600);
}

async function load() {
  const [runResponse, auditResponse] = await Promise.all([
    fetch("/api/run", {cache: "no-store"}),
    fetch("/api/audit-status", {cache: "no-store"}),
  ]);
  if (!runResponse.ok) throw new Error("sealed run unavailable");
  run = await runResponse.json();
  const audit = await auditResponse.json();

  document.querySelector("#model").textContent = run.model;
  document.querySelector("#judgment-count").textContent = run.execution.parallel_judgments;
  document.querySelector("#run-id").textContent = run.run_id.slice(0, 13);
  document.querySelector("#silos").innerHTML = run.silos.map(siloMarkup).join("");
  document.querySelector("#root-cause").textContent = run.connected.root_cause;
  document.querySelector("#response").textContent = `RESPONSE → ${run.connected.response.toUpperCase()}`;
  document.querySelector("#utility-note").textContent = run.utility.note;

  const assurance = document.querySelector("#assurance");
  assurance.querySelector("small").textContent = audit.valid ? `${audit.events} EVENTS / VALID` : "VERIFICATION FAILED";
  if (audit.valid) assurance.classList.add("valid");
}

document.querySelector("#connect").addEventListener("click", connect);
document.querySelector("#replay").addEventListener("click", () => {
  disconnect();
  window.setTimeout(connect, 500);
});

load().catch(error => {
  document.querySelector("#assurance small").textContent = "LOAD FAILED";
  console.error(error);
});
