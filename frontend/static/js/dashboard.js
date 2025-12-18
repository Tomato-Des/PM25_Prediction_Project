let forecastChart = null;
let historyChart = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initial Load
    loadDashboardData();
    // Refresh every 30 seconds to catch the background update quickly
    setInterval(loadDashboardData, 30000); 
});

async function loadDashboardData() {
    await Promise.all([
        loadCurrentAndStatus(),
        loadPredictions(),
        loadHistory()
    ]);
}

async function loadCurrentAndStatus() {
    try {
        const response = await fetch('/api/current');
        if (!response.ok) return; // Silent fail on network error
        
        const data = await response.json();
        const updateElem = document.getElementById('lastUpdate');
        const dotElem = document.querySelector('.dot');

        // Handle System Startup State (Empty DB or No recent data)
        if (data.error || data.current_pm25 === undefined) {
            document.getElementById('currentPM25').innerText = "--";
            document.getElementById('currentStatus').innerText = "System Starting...";
            document.getElementById('currentStatus').className = "status-pill loading";
            document.getElementById('healthAdvice').innerText = "The system is gathering initial data. Please wait...";
            updateElem.innerText = "Initializing...";
            dotElem.style.background = "#fbbf24"; // Yellow for waiting
            return;
        }

        // Data is ready
        const pm25 = data.current_pm25;
        
        // 1. Update Main Value
        document.getElementById('currentPM25').innerText = pm25.toFixed(1);
        updateElem.innerText = "Updated " + new Date(data.datetime).toLocaleTimeString('zh-TW', {hour: '2-digit', minute:'2-digit'});
        dotElem.style.background = "#10b981"; // Green for active

        // 2. Client-Side Status Logic (Replaces API call)
        updateHealthStatus(pm25);

        // 3. Update Next Hour
        if (data.next_hour_prediction !== null) {
            const nextVal = data.next_hour_prediction;
            document.getElementById('nextHourPM25').innerText = nextVal.toFixed(1);
            
            // Trend
            const trend = nextVal - pm25;
            const trendElem = document.getElementById('trendIndicator');
            const icon = trend > 0 ? '↗' : '↘';
            const color = trend > 0 ? '#ef4444' : '#10b981';
            
            trendElem.innerHTML = `<span style="color:${color}">${icon} ${Math.abs(trend).toFixed(1)}</span> from current`;
        }

    } catch (error) {
        console.error("Sync error:", error);
    }
}

function updateHealthStatus(pm25) {
    const statusBadge = document.getElementById('currentStatus');
    const adviceBox = document.getElementById('healthAdvice');
    
    let status = '';
    let colorClass = '';
    let advice = '';

    // EPA Standards
    if (pm25 <= 15.4) {
        status = 'Good';
        colorClass = 'good';
        advice = 'Air quality is great! Perfect for outdoor activities and exercise.';
    } else if (pm25 <= 35.4) {
        status = 'Moderate';
        colorClass = 'moderate';
        advice = 'Air quality is acceptable. Extremely sensitive individuals should consider limiting prolonged outdoor exertion.';
    } else if (pm25 <= 54.4) {
        status = 'Unhealthy for Sensitive';
        colorClass = 'unhealthy-sensitive';
        advice = 'Members of sensitive groups (children, elderly, asthmatics) should limit outdoor activities.';
    } else {
        status = 'Unhealthy';
        colorClass = 'unhealthy';
        advice = 'Everyone may begin to experience health effects. Please wear a mask and avoid outdoor activities.';
    }

    statusBadge.innerText = status;
    statusBadge.className = `status-pill ${colorClass}`;
    adviceBox.innerText = advice;
}

async function loadPredictions() {
    try {
        const response = await fetch('/api/predictions');
        const data = await response.json();
        
        if (!data.predictions || data.predictions.length === 0) return;

        // Calculate 24h average
        const avg = data.predictions.reduce((sum, p) => sum + p.predicted_pm25, 0) / data.predictions.length;
        document.getElementById('avgPM25').innerText = avg.toFixed(1);
        
        renderForecastChart(data.predictions);
    } catch (e) { console.error(e); }
}

async function loadHistory() {
    try {
        // Change this to 168 to fetch the full 7 days
        const response = await fetch('/api/history?hours=168'); 
        const data = await response.json();
        if (data.history) renderHistoryChart(data.history);
    } catch (e) { console.error(e); }
}

// Chart Configurations
function renderForecastChart(predictions) {
    const ctx = document.getElementById('forecastChart');
    if (!ctx) return;
    
    const labels = predictions.map(p => {
        const d = new Date(p.target_datetime);
        return `${d.getHours()}:00`;
    });
    const values = predictions.map(p => p.predicted_pm25);

    if (forecastChart) forecastChart.destroy();

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Forecast (μg/m³)',
                data: values,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
                y: { beginAtZero: true, border: { display: false } }
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false }
        }
    });
}

function renderHistoryChart(history) {
    const ctx = document.getElementById('historyChart');
    if (!ctx) return;

    // Decimate data (take every 2nd point) to improve performance but keep enough detail
    const sampled = history.filter((_, i) => i % 2 === 0);
    const labels = sampled.map(h => {
        const d = new Date(h.datetime);
        // Format: "12/07 14:00"
        return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:00`;
    });
    const values = sampled.map(h => h.pm25);

    if (historyChart) historyChart.destroy();

    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Historical PM2.5',
                data: values,
                borderColor: '#64748b',
                backgroundColor: 'rgba(100, 116, 139, 0.1)', // Added fill for better visibility
                borderWidth: 2,
                tension: 0.1,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.parsed.y} μg/m³`;
                        }
                    }
                }
            },
            scales: {
                x: { 
                    display: true, // ENABLED X-AXIS
                    grid: { display: false },
                    ticks: { 
                        maxTicksLimit: 8, // Limit ticks so they don't overlap
                        maxRotation: 0,
                        font: { size: 11 }
                    }
                },
                y: { 
                    display: true, // ENABLED Y-AXIS
                    beginAtZero: true,
                    grid: { 
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 11 }
                    },
                    title: {
                        display: true,
                        text: 'μg/m³',
                        font: { size: 10 }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}