document.addEventListener('DOMContentLoaded', () => {
    
    const API_BASE = "/api/proje1";
    let systemData = null;
    let stationList = [];
    
    // Zaman yönetimi değişkenleri
    let isPlaying = false;
    let currentStepIndex = 0;
    let playInterval = null;
    
    // UI Elemanları
    const stationGrid = document.getElementById('station-grid');
    const clockDisplay = document.getElementById('clock-display');
    const timeSlider = document.getElementById('time-slider');
    const btnPlay = document.getElementById('btn-toggle-play');
    
    // Grafik (Chart.js)
    let stationChart = null;

    // --- 1. SİMÜLASYON VERİSİNİ ÇEKME ---
    async function initializeSystem() {
        const btn = document.getElementById('btn-init-sim');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Üretiliyor...';
        btn.disabled = true;

        try {
            await fetch(`${API_BASE}/simulate`, { method: "POST" });
            const response = await fetch(`${API_BASE}/bins`);
            systemData = await response.json();
            stationList = systemData.bins;
            
            // Slider ayarları (timeline'daki toplam adım sayısı)
            const maxSteps = stationList[0].timeline.length - 1;
            timeSlider.max = maxSteps;
            currentStepIndex = 0;
            timeSlider.value = 0;
            
            renderStations();
            updateDashboardStats();
        } catch (error) {
            console.error(error);
            alert("Veri bağlantısı kurulamadı. Siyah terminalde sunucunun (uvicorn) çalıştığından emin olun.");
        } finally {
            btn.innerHTML = '<i class="fa-solid fa-check mr-2"></i> Güncellendi';
            setTimeout(() => btn.innerHTML = '<i class="fa-solid fa-microchip mr-2"></i> Yeni Veri Üret', 2000);
            btn.disabled = false;
        }
    }

    // --- 2. KUTULARI (İSTASYONLARI) EKRANA ÇİZME ---
    function renderStations() {
        if (!stationList.length) return;
        stationGrid.innerHTML = '';
        
        stationList.forEach(station => {
            const currentState = station.timeline[currentStepIndex];
            const maxFill = Math.max(currentState.metal, currentState.plastic, currentState.glass, currentState.other);
            
            let statusColor = maxFill > 80 ? 'bg-red-500' : (maxFill > 50 ? 'bg-amber-400' : 'bg-emerald-500');
            let bgLight = maxFill > 80 ? 'bg-red-50' : 'bg-white';

            const card = document.createElement('div');
            card.className = `border rounded-xl p-4 cursor-pointer hover:shadow-md transition ${bgLight}`;
            card.onclick = () => openChartModal(station);
            
            card.innerHTML = `
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h4 class="font-bold text-slate-700 text-sm">${station.building}</h4>
                        <p class="text-xs text-slate-400">Kat ${station.floor} | ${station.bin_id.split('_').pop()}</p>
                    </div>
                    <div class="px-2 py-1 rounded text-xs font-bold text-white ${statusColor}">%${Math.round(maxFill)}</div>
                </div>
                <div class="w-full bg-slate-200 rounded-full h-1.5">
                    <div class="${statusColor} h-1.5 rounded-full transition-all duration-300" style="width: ${Math.min(maxFill, 100)}%"></div>
                </div>
            `;
            stationGrid.appendChild(card);
        });
        
        const totalMinutes = (currentStepIndex / timeSlider.max) * 8 * 60;
        const hours = Math.floor(totalMinutes / 60) + 8;
        const minutes = Math.floor(totalMinutes % 60);
        clockDisplay.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    }

    function updateDashboardStats() {
        document.getElementById('stat-count').textContent = stationList.length;
        if(stationList.length === 0) return;
        
        let total = 0;
        stationList.forEach(s => {
            let state = s.timeline[currentStepIndex];
            total += Math.max(state.metal, state.plastic, state.glass, state.other);
        });
        document.getElementById('stat-avg').textContent = `%${(total / stationList.length).toFixed(1)}`;
    }

    // --- 3. ZAMAN ÇİZELGESİ VE OYNATMA (PLAYBACK) ---
    function togglePlay() {
        isPlaying = !isPlaying;
        btnPlay.innerHTML = isPlaying ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
        
        if (isPlaying) {
            playInterval = setInterval(() => {
                if (currentStepIndex >= timeSlider.max) {
                    currentStepIndex = 0; 
                } else {
                    currentStepIndex++;
                }
                timeSlider.value = currentStepIndex;
                renderStations();
                updateDashboardStats();
            }, 200);
        } else {
            clearInterval(playInterval);
        }
    }

    timeSlider.addEventListener('input', (e) => {
        currentStepIndex = parseInt(e.target.value);
        renderStations();
        updateDashboardStats();
    });

    // --- 4. GRAFİK MODALI (CHART.JS) ---
    function openChartModal(station) {
        document.getElementById('chart-modal').classList.remove('hidden');
        document.getElementById('modal-title').textContent = `${station.building} (Kat ${station.floor}) Geçmişi`;

        const ctx = document.getElementById('history-chart').getContext('2d');
        if(stationChart) stationChart.destroy(); 

        const labels = station.timeline.map(t => (t.t / 3600).toFixed(1) + 's');
        
        stationChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels.slice(0, currentStepIndex + 1), 
                datasets: [
                    { label: 'Plastik', data: station.timeline.map(t=>t.plastic).slice(0, currentStepIndex + 1), borderColor: '#3b82f6', tension: 0.3 },
                    { label: 'Metal', data: station.timeline.map(t=>t.metal).slice(0, currentStepIndex + 1), borderColor: '#64748b', tension: 0.3 },
                    { label: 'Cam', data: station.timeline.map(t=>t.glass).slice(0, currentStepIndex + 1), borderColor: '#10b981', tension: 0.3 }
                ]
            },
            options: { animation: false }
        });
    }

    document.getElementById('close-modal').onclick = () => document.getElementById('chart-modal').classList.add('hidden');

    // --- 5. ROTA OPTİMİZASYONU ---
    document.getElementById('btn-calc-route').onclick = async () => {
        const material = document.getElementById('route-material').value;
        const resBox = document.getElementById('route-results');
        resBox.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Hesaplanıyor...';
        resBox.classList.remove('hidden');

        try {
            const atSeconds = stationList[0].timeline[currentStepIndex].t;
            const res = await fetch(`${API_BASE}/route?material=${material}&threshold=75&at=${atSeconds}`);
            const data = await res.json();
            
            if(data.total_bins_in_route === 0) {
                resBox.innerHTML = 'Toplanması gereken acil kutu bulunamadı.';
                return;
            }

            resBox.innerHTML = `
                <div class="font-bold mb-2">Rota Oluşturuldu (${data.total_bins_in_route} Nokta)</div>
                <div class="text-xs mb-2">Tahmini Mesafe: ${data.total_distance_meters}m | Yük: ${data.total_liters}L</div>
                <div class="bg-white rounded p-2 text-xs text-slate-600 max-h-32 overflow-y-auto">
                    ${data.route.map((r, i) => {
                        const maxPct = Math.max(r.fill_metal_pct || 0, r.fill_plastic_pct || 0, r.fill_glass_pct || 0, r.fill_other_pct || 0);
                        return `<b>${i+1}.</b> ${r.bin_id.split('_')[1]} (%${Math.round(maxPct)})<br>`;
                    }).join('')}
                </div>
            `;
        } catch(e) {
            resBox.innerHTML = 'Hata oluştu.';
        }
    };

    // --- 6. YAPAY ZEKA GÖRÜNTÜ İŞLEME (KAMERA TESTİ) ---
    const dropzone = document.getElementById('ai-dropzone');
    const fileInput = document.getElementById('ai-file');
    const aiResult = document.getElementById('ai-result');

    dropzone.onclick = () => fileInput.click();
    fileInput.onchange = (e) => processImage(e.target.files[0]);

    dropzone.ondragover = (e) => { e.preventDefault(); dropzone.classList.add('border-indigo-500'); };
    dropzone.ondragleave = () => dropzone.classList.remove('border-indigo-500');
    dropzone.ondrop = (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-indigo-500');
        if(e.dataTransfer.files.length) processImage(e.dataTransfer.files[0]);
    };

    async function processImage(file) {
        if(!file) return;
        aiResult.classList.remove('hidden');
        aiResult.innerHTML = '<span class="text-indigo-500"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Analiz ediliyor...</span>';
        
        const fd = new FormData();
        fd.append("file", file);
        
        try {
            const res = await fetch(`${API_BASE}/classify-image`, { method: "POST", body: fd });
            const data = await res.json();
            
            if(!data.model_used) {
                aiResult.innerHTML = `<span class="text-amber-600"><i class="fa-solid fa-triangle-exclamation"></i> Model yüklü değil, rastgele sonuç: ${data.category_tr}</span>`;
            } else {
                aiResult.innerHTML = `<span class="text-emerald-600"><i class="fa-solid fa-check mr-1"></i> Tespit: <b>${data.category_tr}</b> (Güven: %${Math.round(data.confidence*100)})</span>`;
            }
        } catch(e) {
            aiResult.innerHTML = `<span class="text-red-500">Bağlantı hatası.</span>`;
        }
    }

    // Event Listeners Set
    document.getElementById('btn-init-sim').addEventListener('click', initializeSystem);
    btnPlay.addEventListener('click', togglePlay);
});