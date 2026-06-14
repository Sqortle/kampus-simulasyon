// Örnek Proje 3 — Enerji & CO2 görselleştirmesi + zaman içinde playback.
// Simülasyon 8 saati anında hesaplar; veriyi ekranda saat saat oynatıyoruz.

const API = "/api/proje3";
let energyChart, pieChart, co2Chart;

Chart.defaults.color = "#6b7280";
Chart.defaults.borderColor = "#e3e6e8";

let hourly = [];          // [{hour, people, co2, temp, energy_wh, vent_on, ...}]
let critical = 1200;
const SIM_DURATION = 28800;   // 8 saat
let revealed = 0;             // gösterilen saat sayısı

// playback
let simTime = 0, playing = false, rafId = null, lastTs = null;

function clockLabel(t) {
  const totalMin = 8 * 60 + (t / SIM_DURATION) * 8 * 60;
  const h = Math.floor(totalMin / 60), m = Math.floor(totalMin % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function buildCharts() {
  if (energyChart) energyChart.destroy();
  if (co2Chart) co2Chart.destroy();
  energyChart = new Chart(document.getElementById("energyChart"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Kümülatif Enerji (Wh)", data: [], backgroundColor: "#5cc0c2" }] },
    options: { responsive: true, animation: false, plugins: { legend: { display: false } } },
  });
  co2Chart = new Chart(document.getElementById("co2Chart"), {
    type: "line",
    data: { labels: [], datasets: [
      { label: "CO₂ (ppm)", data: [], borderColor: "#d64545", yAxisID: "y", tension: .3 },
      { label: "Sıcaklık (°C)", data: [], borderColor: "#5cc0c2", yAxisID: "y1", tension: .3 },
    ]},
    options: {
      responsive: true, animation: false,
      scales: {
        y: { position: "left", title: { display: true, text: "CO₂ ppm" } },
        y1: { position: "right", title: { display: true, text: "°C" }, grid: { drawOnChartArea: false } },
      },
    },
  });
}

function renderPie(e) {
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(document.getElementById("pieChart"), {
    type: "doughnut",
    data: {
      labels: [`Aydınlatma (%${e.lighting_percent})`, `HVAC (%${e.vent_percent})`],
      datasets: [{ data: [e.lighting_energy_wh, e.vent_energy_wh], backgroundColor: ["#e0a83d", "#5cc0c2"] }],
    },
    options: { responsive: true },
  });
}

function revealHours(count) {
  // Sadece eksik saatleri ekle (geri sarmada baştan kur)
  if (count < revealed) {
    const sub = hourly.slice(0, count);
    energyChart.data.labels = sub.map(r => r.hour + ". saat");
    energyChart.data.datasets[0].data = sub.map(r => r.energy_wh);
    co2Chart.data.labels = sub.map(r => r.hour + ". saat");
    co2Chart.data.datasets[0].data = sub.map(r => r.co2);
    co2Chart.data.datasets[1].data = sub.map(r => r.temp);
  } else {
    for (let i = revealed; i < count; i++) {
      const r = hourly[i];
      energyChart.data.labels.push(r.hour + ". saat");
      energyChart.data.datasets[0].data.push(r.energy_wh);
      co2Chart.data.labels.push(r.hour + ". saat");
      co2Chart.data.datasets[0].data.push(r.co2);
      co2Chart.data.datasets[1].data.push(r.temp);
    }
  }
  revealed = count;
  energyChart.update("none");
  co2Chart.update("none");

  // KPI + banner: son gösterilen saate göre
  if (count > 0) {
    const last = hourly[count - 1];
    document.getElementById("k-people").textContent = last.people;
    document.getElementById("k-co2").textContent = last.co2;
    document.getElementById("k-temp").textContent = last.temp;
    document.getElementById("k-vent").textContent = last.vent_on ? "AÇIK" : "KAPALI";
    document.getElementById("co2-banner").classList.toggle("hidden", !(last.co2 >= critical));
  }
}

function renderFrame() {
  document.getElementById("clock").textContent = clockLabel(simTime);
  const count = Math.min(hourly.length, Math.floor(simTime / 3600));
  if (count !== revealed) revealHours(count);
}

function loop(ts) {
  if (!playing) return;
  if (lastTs == null) lastTs = ts;
  const dt = (ts - lastTs) / 1000; lastTs = ts;
  const speed = +document.getElementById("speed").value;
  simTime += dt * speed * 600;          // 1x: 8 saat ~48 sn
  if (simTime >= SIM_DURATION) {
    simTime = SIM_DURATION; renderFrame(); stop(true); return;
  }
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

async function loadAndPlay() {
  const btn = document.getElementById("btn-sim");
  btn.disabled = true; btn.textContent = "Çalışıyor...";
  try {
    await fetch(`${API}/simulate`, { method: "POST" });
    const [hr, energy] = await Promise.all([
      fetch(`${API}/hourly-report`).then(r => r.json()),
      fetch(`${API}/energy-summary`).then(r => r.json()),
    ]);
    hourly = hr.hourly;
    buildCharts();
    renderPie(energy);                 // gün sonu dağılımı (özet)
    document.getElementById("playback").classList.remove("hidden");
    revealed = 0; simTime = 0;
    play();
  } catch (err) {
    alert("Veri yüklenemedi: " + err);
  } finally {
    btn.disabled = false; btn.textContent = "Yeniden Çalıştır";
  }
}

document.getElementById("btn-sim").addEventListener("click", loadAndPlay);
document.getElementById("btn-play").addEventListener("click", () => {
  if (playing) { stop(); return; }
  if (simTime >= SIM_DURATION) { simTime = 0; revealed = 0; buildCharts(); }
  play();
});
document.getElementById("speed").addEventListener("input", (e) => {
  document.getElementById("speed-val").textContent = e.target.value + "x";
});
