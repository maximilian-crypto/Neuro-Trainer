// Schritt 2: Fallauswahl + Viewer. Schema, Befund und Auflösung folgen in Schritt 3.
const $ = (s) => document.querySelector(s);
let cases = [], cur = -1, loadToken = 0;

const viewer = new StackViewer($("#view"), (v) => {
  $("#hudSlice").textContent = `Schicht ${v.z + 1}/${v.shape[0]}  (${v.spacing[0]} mm)`;
  $("#hudWin").textContent = `W ${v.w}  L ${v.l}`;
  const h = v.hover;
  $("#hudHU").textContent = h && h.hu !== null ? `${h.hu} HU` : "";
  $("#sliceSlider").value = v.shape[0] - 1 - v.z;
  document.querySelectorAll("#presets button").forEach((b) =>
    b.classList.toggle("active", +b.dataset.w === v.w && +b.dataset.l === v.l));
});

for (const p of PRESETS) {
  const b = document.createElement("button");
  b.dataset.w = p.w; b.dataset.l = p.l;
  b.innerHTML = `${p.key} ${p.name}<small>W${p.w} / L${p.l}</small>`;
  b.onclick = () => viewer.setWindow(p.w, p.l);
  $("#presets").append(b);
}

async function fetchBin(url, Type) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return new Type(await r.arrayBuffer());
}

async function openCase(i) {
  cur = (i + cases.length) % cases.length;
  const c = cases[cur], token = ++loadToken;
  $("#caseSel").value = c.id;
  $("#status").textContent = "lädt …";
  const t0 = performance.now();
  const [vol, mask] = await Promise.all([
    fetchBin(`/api/cases/${c.id}/volume`, Int16Array),
    c.has_mask ? fetchBin(`/api/cases/${c.id}/mask`, Uint8Array) : null,
  ]);
  if (token !== loadToken) return;
  viewer.load(vol, c.shape, c.spacing_mm, mask);
  $("#sliceSlider").max = c.shape[0] - 1;
  $("#status").textContent = `${c.shape.join("×")} · ${Math.round(performance.now() - t0)} ms`;
}

async function init() {
  cases = await (await fetch("/api/cases")).json();
  if (!cases.length) { $("#status").textContent = "Keine Fälle. Erst `make data` ausführen."; return; }
  for (const c of cases) $("#caseSel").append(new Option(c.id, c.id));
  $("#caseSel").onchange = (e) => { openCase(cases.findIndex((c) => c.id === e.target.value)); e.target.blur(); };
  $("#prevCase").onclick = () => openCase(cur - 1);
  $("#nextCase").onclick = () => openCase(cur + 1);
  $("#reset").onclick = () => viewer.resetView();
  $("#showMask").onchange = (e) => { viewer.showMask = e.target.checked; viewer.draw(); };
  $("#sliceSlider").oninput = (e) => viewer.setSlice(viewer.shape[0] - 1 - +e.target.value);
  window.addEventListener("keydown", (e) => {
    const t = e.target;
    if (t.tagName === "SELECT" || (t.tagName === "INPUT" && !["checkbox", "range"].includes(t.type))) return;
    const p = PRESETS.find((p) => p.key === e.key);
    if (p) viewer.setWindow(p.w, p.l);
    else if (e.key === "ArrowUp") viewer.setSlice(viewer.z + 1);
    else if (e.key === "ArrowDown") viewer.setSlice(viewer.z - 1);
    else if (e.key === "PageUp") viewer.setSlice(viewer.z + 5);
    else if (e.key === "PageDown") viewer.setSlice(viewer.z - 5);
    else if (e.key === "r" || e.key === "R") viewer.resetView();
    else return;
    e.preventDefault();
  });
  openCase(0);
}
init();
