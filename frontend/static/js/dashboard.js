// Dashboard JavaScript - Chart.js Visualizations

let forecastChart = null;
let historyChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    // Auto-refresh every 5 minutes
    setInterval(loadDashboardData, 300000);
});

async function loadDashboardData() {
    try {
        await Promise.all([
            loadCurrentData(),
            loadPredictions(),
            loadHistory(),
            loadHealthAdvice()
        ]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadCurrentData() {
    try {
        const response = await fetch('/api/current');
        const data = await response.json();
        
        if (data.error) {
            console.error('API Error:', data.error);
            return;
        }
        
        // Update current PM2.5
        document.getElementById('currentPM25').textContent = data.current_pm25.toFixed(1);
        
        // Update status badge
        const statusBadge = document.getElementById('currentStatus');
        statusBadge.textContent = data.status;
        statusBadge.className = 'status-badge ' + data.status.toLowerCase().replace(/ /g, '-');
        
        // Update next hour prediction
        if (data.next_hour_prediction) {
            document.getElementById('nextHourPM25').textContent = data.next_hour_prediction.toFixed(1);
            
            // Trend indicator
            const trend = data.next_hour_prediction - data.current_pm25;
            const trendElem = document.getElementById('trendIndicator');
            if (trend > 0) {
                trendElem.textContent = `↗ +${trend.toFixed(1)}`;
                trendElem.style.color = '#ef4444';
            } else {
                trendElem.textContent = `↘ ${trend.toFixed(1)}`;
                trendElem.style.color = '#10b981';
            }
        }
        
        // Update last update time
        document.getElementById('lastUpdate').textContent = new Date(data.datetime).toLocaleString('zh-TW');
        
    } catch (error) {
        console.error('Error loading current data:', error);
    }
}

async function loadPredictions() {
    try {
        const response = await fetch('/api/predictions');
        const data = await response.json();
        
        if (data.error || !data.predictions || data.predictions.length === 0) {
            return;
        }
        
        // Calculate 24h average
        const avg = data.predictions.reduce((sum, p) => sum + p.predicted_pm25, 0) / data.predictions.length;
        document.getElementById('avgPM25').textContent = avg.toFixed(1);
        
        // Update forecast chart
        updateForecastChart(data.predictions);
        
    } catch (error) {
        console.error('Error loading predictions:', error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history?hours=168'); // 7 days
        const data = await response.json();
        
        if (data.error || !data.history) {
            return;
        }
        
        updateHistoryChart(data.history);
        
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

async function loadHealthAdvice() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.status) {
            document.getElementById('healthAdvice').innerHTML = `<p>${data.status}</p>`;
        }
        
    } catch (error) {
        console.error('Error loading health advice:', error);
    }
}

function updateForecastChart(predictions) {
    const ctx = document.getElementById('forecastChart').getContext('2d');
    
    const labels = predictions.map(p => {
        const date = new Date(p.target_datetime);
        return date.getHours() + ':00';
    });
    
    const values = predictions.map(p => p.predicted_pm25);
    
    if (forecastChart) {
        forecastChart.destroy();
    }
    
    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Predicted PM2.5 (μg/m³)',
                data: values,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: '#6366f1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: { size: 14, weight: '600' },
                        color: '#1f2937'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 14 },
                    bodyFont: { size: 13 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: { size: 12 },
                        color: '#6b7280'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        font: { size: 12 },
                        color: '#6b7280',
                        maxRotation: 45
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function updateHistoryChart(history) {
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    // Sample data every 3 hours for cleaner display
    const sampled = history.filter((_, i) => i % 3 === 0);
    
    const labels = sampled.map(h => {
        const date = new Date(h.datetime);
        return `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:00`;
    });
    
    const values = sampled.map(h => h.pm25);
    
    if (historyChart) {
        historyChart.destroy();
    }
    
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Historical PM2.5 (μg/m³)',
                data: values,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                pointHoverRadius: 5,
                pointBackgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: { size: 14, weight: '600' },
                        color: '#1f2937'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 14 },
                    bodyFont: { size: 13 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: { size: 12 },
                        color: '#6b7280'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    ticks: {
                        font: { size: 10 },
                        color: '#6b7280',
                        maxRotation: 45,
                        maxTicksLimit: 20
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}