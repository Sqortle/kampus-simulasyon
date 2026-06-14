// Örnek Proje 1 — Kutu Filosu panosu.
// Tek arayüzden tüm kutuları izle, materyal bazlı doluluğu gör, rota hesapla.
// Simülasyon 8 saati anında hesaplar; veriyi ekranda zaman içinde oynatırız.

const API = "/api/proje1";
const MAT_LABELS = { metal: "Metal", plastic: "Plastik", glass: "Cam", other: "Diğer" };
const MAT_COLORS = { metal: "#6b7280", plastic: "#3b82f6", glass: "#5cc0c2", other: "#a855f7" };

Chart.defaults.color = "#6b7280";
Chart.defaults.borderColor = "#e3e6e8";

// Filo verisi
let fleet = null, bins = [], binById = {};
let sampleInterval = 900, simDuration = 28800;

// Playback
let simTime = 0, playing = false, rafId = null, lastTs = null;

// Detay
let selectedBinId = null, detailChart = null;

// --- yardımcılar ---
function clockLabel(t) {
  const totalMin = 8 * 60 + (t / simDuration) * 8 * 60;
  const h = Math.floor(totalMin / 60), m = Math.floor(totalMin % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
function sampleIndex() {
  const n = bins.length ? bins[0].timeline.length : 0;
  return Math.min(n - 1, Math.floor(simTime / sampleInterval));
}
function fillColor(pct) {
  if (pct >= 80) return "#d64545";   // dolu
  if (pct >= 50) return "#e0a83d";   // orta
  if (pct >= 25) return "#7cc6b1";   // az
  return "#5cc0c2";                  // boş (turkuaz)
}
function fillAt(bin, idx, material) {
  const s = bin.timeline[idx];
  return material === "all" ? Math.max(s.metal, s.plastic, s.glass, s.other) : s[material];
}
function shortLabel(binId) { return binId.split("_").pop(); }
function currentMaterial() { return document.getElementById("material").value; }

// Okunabilir isim: BIN_Kutuphane_K1_N1 -> "Kütüphane · 1. kat · 1. kutu"
const BUILDING_TR = { Kutuphane: "Kütüphane", Yemekhane: "Yemekhane", AnaKampus: "Ana Bina", Bahce: "Bahçe" };
function friendlyName(b) {
  const parts = b.bin_id.split("_");
  if (parts.length === 4 && parts[2][0] === "K" && parts[3][0] === "N") {
    const bld = BUILDING_TR[parts[1]] || parts[1];
    return `${bld} · ${+parts[2].slice(1)}. kat · ${+parts[3].slice(1)}. kutu`;
  }
  return displayBuilding(b.building || "");
}

// Bina adını Türkçe göster
function displayBuilding(name) {
  return name
    .replace("AnaKampus", "Ana Bina").replace("Kutuphane", "Kütüphane")
    .replace("Bahce", "Bahçe");
}

// Sütun (bina) sırası: kantinler ait oldukları binanın hemen sağında
const BUILDING_ORDER = [
  "Kutuphane", "Kutuphane Kantin", "Yemekhane",
  "AnaKampus", "Ana Bina Kantin", "Bahce",
];

// --- ızgara kurulumu ---
function buildGrid() {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  const buildings = [...new Set(bins.map(b => b.building))].sort((a, b) => {
    const ia = BUILDING_ORDER.indexOf(a), ib = BUILDING_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });

  for (const building of buildings) {
    const col = document.createElement("div");
    col.className = "building";
    col.innerHTML = `<div class="b-name">${displayBuilding(building)}</div>`;
    // Sadece bu binada bulunan katlar (üst kat üstte)
    const floors = [...new Set(bins.filter(b => b.building === building).map(b => b.floor))]
      .sort((a, b) => b - a);
    for (const floor of floors) {
      const floorBins = bins
        .filter(b => b.building === building && b.floor === floor)
        .sort((a, b) => a.bin_id.localeCompare(b.bin_id));
      if (!floorBins.length) continue;
      const row = document.createElement("div");
      row.className = "floor-row";
      row.innerHTML = `<span class="f-label">K${floor}</span>`;
      for (const b of floorBins) {
        const chip = document.createElement("div");
        chip.className = "bin-chip";
        chip.dataset.binId = b.bin_id;
        chip.innerHTML = `<span class="b-id">${shortLabel(b.bin_id)}</span><span class="b-pct">0%</span>`;
        chip.addEventListener("click", () => selectBin(b.bin_id));
        row.appendChild(chip);
      }
      col.appendChild(row);
    }
    grid.appendChild(col);
  }
}

function updateGrid() {
  const idx = sampleIndex();
  const material = currentMaterial();
  document.querySelectorAll(".bin-chip").forEach(chip => {
    const b = binById[chip.dataset.binId];
    const pct = fillAt(b, idx, material);
    chip.style.background = fillColor(pct);
    chip.querySelector(".b-pct").textContent = Math.round(pct) + "%";
  });
}

// --- detay paneli ---
function selectBin(binId) {
  selectedBinId = binId;
  document.querySelectorAll(".bin-chip").forEach(c =>
    c.classList.toggle("selected", c.dataset.binId === binId));
  document.getElementById("detail").classList.remove("hidden");
  document.querySelector(".layout").classList.add("with-detail");
  buildDetailChart();
  renderDetail();
}

function buildDetailChart() {
  if (detailChart) detailChart.destroy();
  detailChart = new Chart(document.getElementById("d-chart"), {
    type: "line",
    data: {
      labels: [],
      datasets: Object.keys(MAT_LABELS).map(m => ({
        label: MAT_LABELS[m], data: [], borderColor: MAT_COLORS[m],
        pointRadius: 0, tension: .25,
      })),
    },
    options: {
      responsive: true, animation: false,
      scales: {
        x: { title: { display: true, text: "Saat" } },
        y: { min: 0, max: 100, title: { display: true, text: "Doluluk %" } },
      },
    },
  });
}

function renderDetail() {
  if (!selectedBinId) return;
  const b = binById[selectedBinId];
  const idx = sampleIndex();
  const s = b.timeline[idx];

  document.getElementById("d-title").textContent = b.bin_id;
  document.getElementById("d-meta").textContent =
    `${b.building} · Kat ${b.floor} · ${b.ip_address} · (${b.x_coord}, ${b.y_coord})`;

  // Materyal barları (o anki örnek)
  const barsEl = document.getElementById("d-bars");
  barsEl.innerHTML = Object.keys(MAT_LABELS).map(m => `
    <div class="bar">
      <div class="bar-top"><span>${MAT_LABELS[m]}</span><span>${Math.round(s[m])}%</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${s[m]}%;background:${MAT_COLORS[m]}"></div></div>
    </div>`).join("");

  // Zaman serisi grafiği (o ana kadar)
  const upto = b.timeline.slice(0, idx + 1);
  detailChart.data.labels = upto.map(p => (p.t / 3600).toFixed(0));
  Object.keys(MAT_LABELS).forEach((m, i) => {
    detailChart.data.datasets[i].data = upto.map(p => p[m]);
  });
  detailChart.update("none");
}

// --- playback ---
function renderFrame() {
  document.getElementById("clock").textContent = clockLabel(simTime);
  updateGrid();
  if (selectedBinId) renderDetail();
}
function loop(ts) {
  if (!playing) return;
  if (lastTs == null) lastTs = ts;
  const dt = (ts - lastTs) / 1000; lastTs = ts;
  const speed = +document.getElementById("speed").value;
  simTime += dt * speed * 600;          // 1x: 600 sim-sn/sn -> 8 saat ~48 sn
  if (simTime >= simDuration) { simTime = simDuration; renderFrame(); stop(true); return; }
  renderFrame();
  rafId = requestAnimationFrame(loop);
}
function play() {
  playing = true; lastTs = null;
  document.getElementById("btn-play").textContent = "Duraklat";
  rafId = requestAnimationFrame(loop);
}
function stop(finished = false) {
  playing = false;
  if (rafId) cancelAnimationFrame(rafId);
  document.getElementById("btn-play").textContent = finished ? "Tekrar Oynat" : "Devam";
}

// --- rota ---
function clearRoute() {
  document.querySelectorAll(".order-badge").forEach(e => e.remove());
  document.getElementById("route-svg").innerHTML = "";
  document.getElementById("route-summary").classList.add("hidden");
}

async function calcRoute() {
  const material = currentMaterial();
  const threshold = +document.getElementById("threshold").value;
  // Rota, ekranda gördüğün ANA göre hesaplansın (duraklatınca tutarlı olur)
  const at = Math.floor(simTime);
  const data = await fetch(`${API}/route?material=${material}&threshold=${threshold}&at=${at}`).then(r => r.json());
  clearRoute();

  // Sıra rozetleri
  data.route_order.forEach((binId, i) => {
    const chip = document.querySelector(`.bin-chip[data-bin-id="${binId}"]`);
    if (!chip) return;
    const badge = document.createElement("span");
    badge.className = "order-badge"; badge.textContent = i + 1;
    chip.appendChild(badge);
  });

  // Rota çizgisi (chip merkezleri üzerinden)
  const wrap = document.getElementById("grid-wrap");
  const svg = document.getElementById("route-svg");
  const wr = wrap.getBoundingClientRect();
  const pts = data.route_order.map(binId => {
    const chip = document.querySelector(`.bin-chip[data-bin-id="${binId}"]`);
    const r = chip.getBoundingClientRect();
    return `${r.left - wr.left + r.width / 2},${r.top - wr.top + r.height / 2}`;
  });
  if (pts.length > 1) {
    svg.innerHTML = `<polyline points="${pts.join(" ")}" fill="none"
      stroke="#0ea5e9" stroke-width="3" stroke-dasharray="6 5" stroke-linejoin="round"/>`;
  }

  // Özet — kart halinde
  const cs = data.collection_summary;
  const el = document.getElementById("route-summary");
  el.classList.remove("hidden");

  const cards = data.route.map((d, i) => `
    <div class="route-card">
      <div class="rc-order">${i + 1}</div>
      <div class="rc-body">
        <div class="rc-name">${friendlyName(d)}</div>
        <div class="rc-vol">${d.total_liters} L toplam</div>
        <div class="rc-mats">
          <span title="Metal">M ${Math.round(d.fill_metal_pct)}%</span>
          <span title="Plastik">P ${Math.round(d.fill_plastic_pct)}%</span>
          <span title="Cam">C ${Math.round(d.fill_glass_pct)}%</span>
          <span title="Diğer">D ${Math.round(d.fill_other_pct)}%</span>
        </div>
      </div>
    </div>`).join("");

  const empty = data.total_bins_in_route === 0
    ? `<p class="rc-empty">Bu eşikte toplanacak kutu yok.</p>` : "";

  el.innerHTML = `
    <div class="panel">
      <div class="rs-top">
        <h2>Toplama Rotası</h2>
        <span class="rs-tag">${data.material_filter} · eşik %${data.threshold_used}</span>
      </div>
      <div class="rs-head">
        <div class="rs-stat"><span>${data.total_bins_in_route}/${data.total_bins_in_system}</span><label>Toplanacak Kutu</label></div>
        <div class="rs-stat"><span>${data.total_distance_meters} m</span><label>Toplam Mesafe</label></div>
        <div class="rs-stat"><span>${data.total_liters} L</span><label>Toplam Hacim</label></div>
      </div>
      <div class="rs-mat-summary">
        <span><i style="background:#6b7280"></i>Metal ${cs.metal_liters} L</span>
        <span><i style="background:#3b82f6"></i>Plastik ${cs.plastic_liters} L</span>
        <span><i style="background:#5cc0c2"></i>Cam ${cs.glass_liters} L</span>
        <span><i style="background:#a855f7"></i>Diğer ${cs.other_liters} L</span>
      </div>
      ${empty}
      <div class="route-cards">${cards}</div>
    </div>`;
}

// --- çalıştır ---
async function runSim() {
  const btn = document.getElementById("btn-sim");
  btn.disabled = true; btn.textContent = "Çalışıyor...";
  try {
    await fetch(`${API}/simulate`, { method: "POST" });
    fleet = await fetch(`${API}/bins`).then(r => r.json());
    bins = fleet.bins;
    binById = Object.fromEntries(bins.map(b => [b.bin_id, b]));
    sampleInterval = fleet.sample_interval;
    simDuration = fleet.sim_duration;

    clearRoute();
    selectedBinId = null;
    document.getElementById("detail").classList.add("hidden");
    document.querySelector(".layout").classList.remove("with-detail");
    document.getElementById("playback").classList.remove("hidden");
    document.getElementById("toolbar").classList.remove("hidden");

    buildGrid();
    simTime = 0;
    play();
  } catch (err) {
    alert("Simülasyon çalıştırılamadı: " + err);
  } finally {
    btn.disabled = false; btn.textContent = "Yeniden Çalıştır";
  }
}

// --- olaylar ---
document.getElementById("btn-sim").addEventListener("click", runSim);
document.getElementById("btn-play").addEventListener("click", () => {
  if (playing) { stop(); return; }
  if (simTime >= simDuration) simTime = 0;
  play();
});
document.getElementById("speed").addEventListener("input", (e) => {
  document.getElementById("speed-val").textContent = e.target.value + "x";
});
document.getElementById("material").addEventListener("change", () => { if (bins.length) updateGrid(); });
document.getElementById("btn-route").addEventListener("click", calcRoute);
document.getElementById("btn-clear").addEventListener("click", clearRoute);

// --- 6.2 Kamera testi: görsel sürükle-bırak (şimdilik sadece önizleme) ---
(function setupDropzone() {
  const dz = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const inner = document.getElementById("dz-inner");
  const preview = document.getElementById("dz-preview");
  if (!dz) return;

  const result = document.getElementById("dz-result");
  const clearBtn = document.getElementById("dz-clear");

  function reset() {
    preview.src = "";
    preview.classList.add("hidden");
    inner.classList.remove("hidden");
    result.classList.add("hidden");
    result.innerHTML = "";
    input.value = "";
  }

  function showFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    preview.src = URL.createObjectURL(file);
    preview.classList.remove("hidden");
    inner.classList.add("hidden");
    classify(file);
  }

  async function classify(file) {
    result.classList.remove("hidden");
    result.innerHTML = `<span class="dz-loading">Analiz ediliyor…</span>`;
    try {
      const fd = new FormData();
      fd.append("file", file);
      const data = await fetch(`${API}/classify-image`, { method: "POST", body: fd }).then(r => r.json());
      if (!data.model_used) {
        result.innerHTML = `<div class="dz-warn">${data.message || "Sınıflandırma modeli yüklü değil."}</div>`;
        return;
      }
      result.innerHTML = `
        <div class="dz-card">
          <div>
            <div class="dz-cat">${data.category_tr}</div>
            <div class="dz-meta">Güven %${Math.round(data.confidence * 100)}</div>
          </div>
        </div>`;
    } catch (err) {
      result.innerHTML = `<div class="dz-warn">İstek başarısız: ${err}</div>`;
    }
  }

  dz.addEventListener("click", () => input.click());
  if (clearBtn) clearBtn.addEventListener("click", reset);
  input.addEventListener("change", (e) => showFile(e.target.files[0]));
  ["dragenter", "dragover"].forEach(ev =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach(ev =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("dragover"); }));
  dz.addEventListener("drop", (e) => showFile(e.dataTransfer.files[0]));
})();
