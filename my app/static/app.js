// ============= CSRF Token Helper =============
/**
 * Get CSRF token from meta tag or form
 */
function getCsrfToken() {
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (metaToken) return metaToken;
    
    const formToken = document.querySelector('input[name="csrf_token"]')?.value;
    if (formToken) return formToken;
    
    return '';
}

/**
 * Fetch with CSRF token automatically included
 */
async function fetchWithCsrf(url, options = {}) {
    const csrfToken = getCsrfToken();
    const headers = {
        'X-CSRFToken': csrfToken,
        ...options.headers
    };
    
    return fetch(url, {
        ...options,
        headers
    });
}

// ============= VapeCrib Dashboard Animations =============
(function initVCAnimations() {
    /**
     * Animate a numeric value counting up from 0 to target.
     * @param {Element} el - the element whose textContent gets updated
     * @param {number}  target - final value
     * @param {string}  prefix - e.g. '₱'
     * @param {string}  suffix - e.g. '%'
     * @param {number}  duration - ms
     */
    window.vcCountUp = function(el, target, prefix, suffix, duration) {
        if (!el) return;
        prefix  = prefix  || '';
        suffix  = suffix  || '';
        duration = duration || 1400;
        const start = performance.now();
        const tick  = (now) => {
            const pct  = Math.min((now - start) / duration, 1);
            const ease = 1 - Math.pow(1 - pct, 3); // cubic ease-out
            const cur  = Math.floor(ease * target);
            el.textContent = prefix + cur.toLocaleString() + suffix;
            if (pct < 1) requestAnimationFrame(tick);
            else {
                el.textContent = prefix + target.toLocaleString() + suffix;
                el.classList.add('vc-metric-pop');
                setTimeout(() => el.classList.remove('vc-metric-pop'), 500);
            }
        };
        requestAnimationFrame(tick);
    };

    /**
     * Replace element content with skeleton shimmer temporarily,
     * then restore after fetchFn resolves.
     */
    window.vcSkeleton = function(el, fetchFn) {
        if (!el) return fetchFn();
        const original = el.innerHTML;
        const h = el.offsetHeight || 20;
        el.innerHTML = `<span class="vc-skeleton" style="display:block;height:${h}px;width:80%;"></span>`;
        return fetchFn().finally(() => {
            // caller is responsible for setting el.innerHTML after resolve
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        // Only run inside the dashboard (not on the landing page)
        if (!document.querySelector('.dashboard')) return;

        // 1. Stagger summary cards entrance

        // 2. Stagger summary cards entrance
        const summaryCards = document.querySelectorAll('.summary-cards .card');
        summaryCards.forEach((card, i) => {
            card.style.animationDelay = (0.05 + i * 0.07) + 's';
            // small rAF to let browser paint before animating
            requestAnimationFrame(() => card.classList.add('vc-card-in'));
        });

        // 3. Stagger any generic card grids (charts-section, etc.)
        const otherCards = document.querySelectorAll(
            '.charts-section .card, .alerts-section .card'
        );
        otherCards.forEach((card, i) => {
            card.style.animationDelay = (0.1 + i * 0.09) + 's';
            requestAnimationFrame(() => card.classList.add('vc-card-in'));
        });

        // 4. Chart canvas — wrap parent in entrance class
        document.querySelectorAll('canvas').forEach((canvas) => {
            const wrapper = canvas.closest('.card') || canvas.parentElement;
            if (wrapper) {
                wrapper.style.animationDelay = '0.2s';
                wrapper.classList.add('vc-chart-in');
            }
        });

        // 5. Alert row items slide-in via IntersectionObserver
        const alertObserver = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                if (e.isIntersecting) {
                    e.target.classList.add('vc-alert-in');
                    alertObserver.unobserve(e.target);
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.alert-item, .alert').forEach((el, i) => {
            el.style.animationDelay = (i * 0.08) + 's';
            alertObserver.observe(el);
        });

        // 6. Count-up for all .metric elements already in DOM
        document.querySelectorAll('.metric, .metric-value').forEach((el) => {
            const raw = el.textContent.trim();
            const match = raw.match(/^([^\d]*)(\d[\d,.]*)(.*)$/);
            if (!match) return;
            const prefix = match[1];
            const suffix = match[3];
            const target = parseFloat(match[2].replace(/,/g, ''));
            if (!isNaN(target) && target > 0) {
                el.textContent = prefix + '0' + suffix;
                vcCountUp(el, target, prefix, suffix, 1200);
            }
        });
    });
})();

// Modal functionality
window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        document.body.style.paddingRight = getScrollbarWidth() + 'px';
        modal.setAttribute('aria-hidden', 'false');
        // Focus management for accessibility
        const firstInput = modal.querySelector('input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            document.body.style.overflow = 'auto';
            document.body.style.paddingRight = '0px';
            modal.setAttribute('aria-hidden', 'true');
            // Clear any messages
            const messagesDiv = modal.querySelector('.modal-body > div[id$="-messages"]');
            if (messagesDiv) {
                messagesDiv.innerHTML = '';
            }
            // Reset form
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
        }, 300); // Wait for animation to complete
    }
}

function switchModal(targetModalId) {
    // Close all modals first with animation
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (modal.classList.contains('show')) {
            closeModal(modal.id);
        }
    });

    // Open target modal after a short delay to allow close animation
    setTimeout(() => {
        openModal(targetModalId);
    }, 300);
}

// Helper function to get scrollbar width
function getScrollbarWidth() {
    const scrollDiv = document.createElement('div');
    scrollDiv.style.width = '100px';
    scrollDiv.style.height = '100px';
    scrollDiv.style.overflow = 'scroll';
    scrollDiv.style.position = 'absolute';
    scrollDiv.style.top = '-9999px';
    document.body.appendChild(scrollDiv);
    const scrollbarWidth = scrollDiv.offsetWidth - scrollDiv.clientWidth;
    document.body.removeChild(scrollDiv);
    return scrollbarWidth;
}

// Helper function to update comparison cards
function updateComparisonCard(currentId, previousId, changeId, currentValue, previousValue, changePercent, isCurrency) {
    const currentElem = document.getElementById(currentId);
    const previousElem = document.getElementById(previousId);
    const changeElem = document.getElementById(changeId);

    if (!currentElem || !previousElem || !changeElem) return;

    // Format values
    const formatValue = (val) => {
        if (isCurrency) {
                return formatPHP(val || 0);
        } else {
            return (val || 0).toLocaleString('en-PH');
        }
    };

    currentElem.textContent = formatValue(currentValue);
    previousElem.textContent = formatValue(previousValue);

    // Update change indicator
    if (changePercent !== null && changePercent !== undefined) {
        const isPositive = changePercent >= 0;
        const icon = isPositive ? '▲' : '▼';
        
        changeElem.innerHTML = `
            <span class="change-icon" style="font-size: 1.2em;">${icon}</span>
            <span>${Math.abs(changePercent).toFixed(1)}% ${isPositive ? 'increase' : 'decrease'}</span>
        `;
        changeElem.style.opacity = '0.95';
    } else {
        changeElem.innerHTML = `
            <span class="change-icon">—</span>
            <span>No previous data</span>
        `;
        changeElem.style.opacity = '0.7';
    }
}

// Switch Monthly Chart View (Bar Chart vs Daily Trend Line)
window.switchMonthlyView = function(viewType) {
    console.log('switchMonthlyView called with:', viewType);
    window.monthlyChartView = viewType;
    
    // Update button states
    const monthlyBtn = document.getElementById('chart-view-monthly');
    const dailyBtn = document.getElementById('chart-view-daily');
    
    console.log('Buttons found:', { monthlyBtn: !!monthlyBtn, dailyBtn: !!dailyBtn });
    
    if (monthlyBtn && dailyBtn) {
        if (viewType === 'monthly') {
            monthlyBtn.style.background = '#007bff';
            monthlyBtn.style.color = 'white';
            monthlyBtn.style.borderColor = '#007bff';
            monthlyBtn.classList.add('active');
            
            dailyBtn.style.background = 'transparent';
            dailyBtn.style.color = 'var(--color-text-primary)';
            dailyBtn.style.borderColor = '#d1d5db';
            dailyBtn.classList.remove('active');
        } else {
            dailyBtn.style.background = '#007bff';
            dailyBtn.style.color = 'white';
            dailyBtn.style.borderColor = '#007bff';
            dailyBtn.classList.add('active');
            
            monthlyBtn.style.background = 'transparent';
            monthlyBtn.style.color = 'var(--color-text-primary)';
            monthlyBtn.style.borderColor = '#d1d5db';
            monthlyBtn.classList.remove('active');
        }
    }
    
    // Update chart
    console.log('monthlyChartData exists:', !!window.monthlyChartData);
    if (window.monthlyChartData) {
        updateMonthlyChartView(viewType);
    } else {
        console.warn('No chart data available yet. Please wait for data to load.');
    }
}

// Update Monthly Chart View
window.updateMonthlyChartView = function(viewType) {
    console.log('updateMonthlyChartView called with:', viewType);
    
    if (!window.monthlyChart) {
        console.error('monthlyChart not found');
        return;
    }
    
    if (!window.monthlyChartData) {
        console.error('monthlyChartData not found');
        return;
    }
    
    const chartData = window.monthlyChartData;
    console.log('Chart data:', chartData);
    
    if (viewType === 'monthly') {
        // Bar Chart: Monthly aggregates
        window.monthlyChart.config.type = 'bar';
        window.monthlyChart.data.labels = chartData.monthly.labels;
        window.monthlyChart.data.datasets = [{
            label: 'Monthly Sales',
            data: chartData.monthly.data,
            backgroundColor: 'rgba(99,102,241,0.75)',
            borderColor: 'rgba(129,140,248,0.5)',
            borderWidth: 0,
            borderRadius: 6,
            borderSkipped: false
        }];

        window.monthlyChart.options.plugins.title.text = `Monthly Sales Performance (Last ${chartData.monthly.labels.length} Month${chartData.monthly.labels.length !== 1 ? 's' : ''})`;
        window.monthlyChart.options.plugins.subtitle = {
            display: true,
            text: 'Aggregated revenue by month',
            font: { size: 11 },
            color: '#6b7280',
            padding: { bottom: 10 }
        };
    } else {
        // Line Chart: Daily actual sales trend (no forecast)
        const filteredData = [];
        const filteredLabels = [];

        chartData.daily.labels.forEach((label, index) => {
            const value = chartData.daily.data[index];
            if (value !== null && value !== undefined) {
                filteredLabels.push(label);
                filteredData.push(value);
            }
        });

        console.log(`Filtered daily data: ${filteredData.length} days with actual sales`);

        window.monthlyChart.config.type = 'line';
        window.monthlyChart.data.labels = filteredLabels;
        window.monthlyChart.data.datasets = [{
            label: 'Daily Sales',
            data: filteredData,
            borderColor: '#34d399',
            backgroundColor: 'rgba(52,211,153,0.15)',
            borderWidth: 2.5,
            tension: 0.4,
            fill: true,
            pointRadius: 2,
            pointHoverRadius: 6,
            pointBackgroundColor: '#34d399',
            pointBorderColor: '#121212',
            pointBorderWidth: 2
        }];

        window.monthlyChart.options.plugins.title.text = `Daily Sales Trend (${filteredData.length} Days of Actual Revenue)`;
        window.monthlyChart.options.plugins.subtitle = {
            display: true,
            text: 'Historical day-by-day sales performance',
            font: { size: 11 },
            color: '#6b7280',
            padding: { bottom: 10 }
        };
    }
    
    console.log('Updating chart...');
    window.monthlyChart.update();
    console.log('Chart updated successfully');
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            closeModal(modal.id);
        }
    });
}

// Enhanced Dashboard JavaScript with Multiple Charts and Modal Functionality
document.addEventListener('DOMContentLoaded', async function () {
    // Initialize dashboard charts if they exist
    initializeCharts();

    // Initialize modal functionality
    initializeModals();
    
    // Initialize period filter functionality
    initializePeriodFilters();
    
    // Initialize chart view toggle buttons
    initializeChartViewToggle();
    
    // Forecast accuracy is fetched inside loadDashboardData (called by initializePeriodFilters)
    
    // Fetch weekly forecast preview
    fetchWeeklyForecast();
    
    // Fetch enhanced restock alerts
    fetchEnhancedRestockAlerts();
});

// Initialize Chart View Toggle Buttons
function initializeChartViewToggle() {
    const monthlyBtn = document.getElementById('chart-view-monthly');
    const dailyBtn = document.getElementById('chart-view-daily');
    
    if (monthlyBtn && dailyBtn) {
        console.log('Chart view toggle buttons found, attaching event listeners');
        
        monthlyBtn.addEventListener('click', function() {
            console.log('Monthly button clicked');
            window.switchMonthlyView('monthly');
        });
        
        dailyBtn.addEventListener('click', function() {
            console.log('Daily button clicked');
            window.switchMonthlyView('daily');
        });
    } else {
        console.log('Chart view toggle buttons not found on this page');
    }
}

// Modal functionality
function initializeModals() {
    // Close modal when clicking outside
    window.onclick = function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                closeModal(modal.id);
            }
        });
    };

    // Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                closeModal(modal.id);
            });
        }
    });

    // Handle login form submission
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    // Handle register form submission
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

// Period Filter Functionality
let currentPeriod = '7d'; // Default period
let customDateRange = null;

function initializePeriodFilters() {
    // Load saved period from sessionStorage
    const savedPeriod = sessionStorage.getItem('dashboardPeriod');
    if (savedPeriod) {
        currentPeriod = savedPeriod;
    }
    
    // Set active button - remove all active classes first
    const periodButtons = document.querySelectorAll('.period-btn');
    periodButtons.forEach(btn => {
        btn.classList.remove('active'); // Remove all active classes first
        if (btn.dataset.period === currentPeriod) {
            btn.classList.add('active');
        }
        
        btn.addEventListener('click', function() {
            // Remove active from all buttons
            periodButtons.forEach(b => b.classList.remove('active'));
            // Add active to clicked button
            this.classList.add('active');
            // Update period
            currentPeriod = this.dataset.period;
            customDateRange = null; // Clear custom range
            // Save to sessionStorage
            sessionStorage.setItem('dashboardPeriod', currentPeriod);
            // Reload dashboard data
            loadDashboardData(currentPeriod);
        });
    });
    
    // Custom date range
    const applyBtn = document.getElementById('apply-custom-range');
    if (applyBtn) {
        applyBtn.addEventListener('click', function() {
            const startDate = document.getElementById('custom-start-date').value;
            const endDate = document.getElementById('custom-end-date').value;
            
            if (!startDate || !endDate) {
                showToast('Please select both start and end dates', 'error');
                return;
            }
            
            if (new Date(startDate) > new Date(endDate)) {
                showToast('Start date must be before end date', 'error');
                return;
            }
            
            // Deactivate preset buttons
            periodButtons.forEach(b => b.classList.remove('active'));
            
            // Set custom range
            customDateRange = { start: startDate, end: endDate };
            currentPeriod = 'custom';
            
            // Reload with custom range
            loadDashboardData('custom', customDateRange);
            showToast('Custom date range applied', 'success');
        });
    }
    
    // Initial load with saved or default period
    loadDashboardData(currentPeriod);
}

function loadDashboardData(period, dateRange = null) {
    // Build API URL with period parameter
    let url = `/api/metrics?period=${period}`;
    
    // Update period descriptions
    const periodLabels = {
        '7d': 'Last 7 days',
        '30d': 'Last 30 days',
        '3m': 'Last 3 months',
        '6m': 'Last 6 months',
        '1y': 'Last year',
        'all': 'All time',
        'custom': 'Custom range'
    };
    
    const periodLabel = periodLabels[period] || 'Last 7 days';
    
    // Update card descriptions
    const unitsHint = document.getElementById('total-units-period');
    const revenueHint = document.getElementById('total-revenue-period');
    const accuracyHint = document.getElementById('accuracy-period');
    
    if (unitsHint) unitsHint.textContent = periodLabel;
    if (revenueHint) revenueHint.textContent = periodLabel;
    if (accuracyHint) accuracyHint.textContent = `Based on ${periodLabel}`;
    
    if (period === 'custom' && dateRange) {
        url = `/api/metrics?start_date=${dateRange.start}&end_date=${dateRange.end}`;
        const customLabel = `${dateRange.start} to ${dateRange.end}`;
        if (unitsHint) unitsHint.textContent = customLabel;
        if (revenueHint) revenueHint.textContent = customLabel;
        if (accuracyHint) accuracyHint.textContent = `Based on ${customLabel}`;
    }
    
    // Map period to days_back for accuracy API
    const periodDaysMap = {
        '7d': 7,
        '30d': 30,
        '3m': 90,
        '6m': 180,
        '1y': 365,
        'all': 9999
    };
    let accuracyDaysBack = periodDaysMap[period] || 7;
    if (period === 'custom' && dateRange) {
        const ms = new Date(dateRange.end) - new Date(dateRange.start);
        accuracyDaysBack = Math.max(1, Math.round(ms / 86400000));
    }

    // Fetch and update dashboard
    fetch(url, { credentials: 'same-origin' })
        .then(response => response.json())
        .then(data => {
            updateDashboardWithData(data);
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            showToast('Failed to load dashboard data', 'error');
        });

    // Refresh accuracy with matching period
    fetchForecastAccuracy(accuracyDaysBack);
}

// Fetch and display forecast accuracy metrics
window.fetchForecastAccuracy = async function(days_back = 7) {
    console.log('[fetchForecastAccuracy] Starting fetch, days_back=' + days_back);
    try {
        const response = await fetch(`/api/forecast-accuracy?days_back=${days_back}`, { credentials: 'same-origin' });
        
        console.log('[fetchForecastAccuracy] Response status:', response.status);
        
        if (!response.ok) {
            throw new Error('Failed to fetch accuracy data');
        }
        
        const data = await response.json();
        console.log('[fetchForecastAccuracy] Data received:', data);
        
        // API returns data under data.accuracy nested object
        const accuracyData = data.accuracy || data;
        console.log('[fetchForecastAccuracy] Accuracy values:', accuracyData);
        
        // Update 1-day accuracy
        updateAccuracyMetric('1d', accuracyData['1_day']);
        
        // Update 7-day accuracy
        updateAccuracyMetric('7d', accuracyData['7_day']);
        
        // Update 30-day accuracy
        updateAccuracyMetric('30d', accuracyData['30_day']);
        
        // Calculate overall average accuracy for summary card
        const accuracyValues = [accuracyData['1_day'], accuracyData['7_day'], accuracyData['30_day']].filter(v => v !== null && v !== undefined && v > 0);
        
        console.log('[fetchForecastAccuracy] Valid accuracy values:', accuracyValues);
        
        // #accuracy summary card is updated by updateDashboardWithData() from /api/metrics
        // so all summary cards appear at the same time — don't touch it here
        
    } catch (error) {
        console.error('Error fetching forecast accuracy:', error);
        
        // #accuracy summary card is driven by /api/metrics — don't overwrite on detail error
        
        // Show "No data yet" in the detail breakdown if insufficient history
        ['1d', '7d', '30d'].forEach(horizon => {
            const valueEl = document.getElementById(`accuracy-${horizon}`);
            const statusEl = document.getElementById(`accuracy-${horizon}-status`);
            
            if (valueEl && statusEl) {
                valueEl.textContent = '--';
                statusEl.textContent = 'Need sales data';
                statusEl.style.color = '#9ca3af';
            }
        });
    }
}

// Update individual accuracy metric with color-coded status
function updateAccuracyMetric(horizon, accuracy) {
    const valueEl = document.getElementById(`accuracy-${horizon}`);
    const statusEl = document.getElementById(`accuracy-${horizon}-status`);
    
    if (!valueEl || !statusEl) return;
    
    if (accuracy === null || accuracy === undefined) {
        valueEl.textContent = '--';
        statusEl.textContent = 'Insufficient data';
        statusEl.style.color = '#cccccc';
        return;
    }
    
    // Display accuracy percentage
    const accuracyPercent = accuracy.toFixed(1);
    valueEl.textContent = `${accuracyPercent}%`;
    
    // Color-code based on performance thresholds
    if (accuracy >= 85) {
        statusEl.textContent = '[OK] Excellent';
        statusEl.style.color = '#4ade80'; // Green
    } else if (accuracy >= 70) {
        statusEl.textContent = '[OK] Good';
        statusEl.style.color = '#fbbf24'; // Yellow
    } else {
        statusEl.textContent = '[WARNING] Needs Improvement';
        statusEl.style.color = '#f87171'; // Red
    }
}

// Fetch and display weekly forecast preview
async function fetchWeeklyForecast() {
    // Check if table exists before fetching (only on Forecasting tab)
    const tableBody = document.getElementById('weekly-forecast-table');
    if (!tableBody) {
        console.log('Weekly forecast table not found on this page, skipping fetch');
        return;
    }
    
    console.log('Fetching weekly forecast data...');
    
    try {
        const response = await fetch('/api/weekly-forecast', { credentials: 'same-origin' });
        
        console.log('Weekly forecast response:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Weekly forecast error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Weekly forecast data:', data);
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }
        
        // Update summary counts
        const criticalCountEl = document.getElementById('critical-count');
        const lowCountEl = document.getElementById('low-count');
        
        if (criticalCountEl) criticalCountEl.textContent = data.critical_count || 0;
        if (lowCountEl) lowCountEl.textContent = data.low_count || 0;
        
        if (data.forecasts.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" style="padding: 30px; text-align: center;">
                        <div style="color: #6b7280; margin-bottom: 15px; font-size: 1.1em;">
                            <i class="fas fa-chart-bar"></i> <strong>No Forecast Data Available Yet</strong>
                        </div>
                        <div style="color: #9ca3af; font-size: 0.95em; line-height: 1.6;">
                            <p style="margin: 10px 0;">To generate 7-day demand forecasts, the system needs sales history:</p>
                            <ol style="text-align: left; display: inline-block; margin: 15px auto;">
                                <li style="margin: 8px 0;"><i class="fas fa-folder"></i> Upload sales CSV data (at least 7 days of history)</li>
                                <li style="margin: 8px 0;"><i class="fas fa-robot"></i> System automatically trains the forecasting model</li>
                                <li style="margin: 8px 0;"><i class="fas fa-chart-line"></i> Forecasts appear here after processing</li>
                            </ol>
                            <p style="margin-top: 15px; color: #6b7280;">
                                <i class="fas fa-lightbulb"></i> <em>Tip: More historical data = More accurate forecasts</em>
                            </p>
                        </div>
                    </td>
                </tr>
            `;
            // Update counts to 0
            if (criticalCountEl) criticalCountEl.textContent = 0;
            if (lowCountEl) lowCountEl.textContent = 0;
            return;
        }
        
        // Generate table rows
        let rowsHTML = '';
        data.forecasts.forEach(forecast => {
            const statusBadge = getStatusBadge(forecast.status, forecast.status_color);
            const actionText = forecast.reorder_recommended ? 
                '<strong style="color: #ef4444;">Reorder Now</strong>' : 
                '<span style="color: #10b981;">Stock OK</span>';
            
            rowsHTML += `
                <tr style="border-bottom: 1px solid #f3f4f6;">
                    <td style="padding: 12px; font-weight: 500;">${forecast.product_name}</td>
                    <td style="padding: 12px; text-align: center;">${forecast.current_stock}</td>
                    <td style="padding: 12px; text-align: center; font-weight: 600;">${forecast.predicted_7d}</td>
                    <td style="padding: 12px; text-align: center;">${statusBadge}</td>
                    <td style="padding: 12px; text-align: center;">${actionText}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = rowsHTML;
        
    } catch (error) {
        console.error('Error fetching weekly forecast:', error);
        
        const tableBody = document.getElementById('weekly-forecast-table');
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" style="padding: 20px; text-align: center; color: #ef4444;">
                        Failed to load forecast data: ${error.message}
                    </td>
                </tr>
            `;
        }
    }
}

// Helper function to create status badge
function getStatusBadge(status, color) {
    const badges = {
        'CRITICAL': `<span style="background: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;"><i class="fas fa-circle" style="color: #dc2626;"></i> CRITICAL</span>`,
        'HIGH': `<span style="background: #fed7aa; color: #9a3412; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;"><i class="fas fa-circle" style="color: #f97316;"></i> HIGH</span>`,
        'MEDIUM': `<span style="background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;"><i class="fas fa-circle" style="color: #eab308;"></i> MEDIUM</span>`,
        'LOW': `<span style="background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;"><i class="fas fa-circle" style="color: #eab308;"></i> LOW</span>`,
        'OK': `<span style="background: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;"><i class="fas fa-check-circle" style="color: #10b981;"></i> OK</span>`
    };
    
    return badges[status] || `<span style="color: ${color};">${status}</span>`;
}

// Fetch Enhanced Restock Alerts (Multi-Horizon Forecast-Based)
async function fetchEnhancedRestockAlerts() {
    console.log('Fetching enhanced restock alerts...');
    
    try {
        const response = await fetch('/api/enhanced-restock-alerts', { credentials: 'same-origin' });
        
        console.log('Enhanced alerts response:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Enhanced alerts error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Enhanced alerts data:', data);
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }
        
        // Update alerts count in Overview tab
        const alertsCountEl = document.getElementById('alerts-count');
        if (alertsCountEl) {
            alertsCountEl.textContent = data.total_alerts || 0;
        }
        
        // Render alerts in the alerts panel
        renderEnhancedAlerts(data.alerts, data);
        
    } catch (error) {
        console.error('Error fetching enhanced restock alerts:', error);
        
        const alertsList = document.getElementById('alerts-list');
        if (alertsList) {
            alertsList.innerHTML = `
                <div style="padding: 15px; text-align: center; color: #6b7280;">
                    Unable to load alerts: ${error.message}
                </div>
            `;
        }
    }
}

// Render Enhanced Restock Alerts with Forecast Details
function renderEnhancedAlerts(alerts, summary) {
    const alertsList = document.getElementById('alerts-list');
    if (!alertsList) return;
    
    if (!alerts || alerts.length === 0) {
        alertsList.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #6b7280;">
                <div style="font-size: 2em; margin-bottom: 10px;"><i class="fas fa-check-circle" style="color: #10b981;"></i></div>
                <div style="font-size: 1.1em; font-weight: 600; margin-bottom: 5px;">No Restock Alerts</div>
                <div style="font-size: 0.9em;">All products have sufficient stock based on forecasts</div>
            </div>
        `;
        return;
    }
    
    // Create compact header with summary
    let html = `
        <div style="display: flex; gap: 8px; margin-bottom: 12px; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px;">
            <span style="flex: 1; text-align: center; padding: 6px; background: #fee2e2; color: #991b1b; border-radius: 4px; font-size: 0.8em; font-weight: 600;">
                <i class="fas fa-square" style="color: #dc2626;"></i> ${summary.critical_count || 0}
            </span>
            <span style="flex: 1; text-align: center; padding: 6px; background: #fef3c7; color: #92400e; border-radius: 4px; font-size: 0.8em; font-weight: 600;">
                <i class="fas fa-square" style="color: #f97316;"></i> ${summary.high_count || 0}
            </span>
        </div>
    `;
    
    // Render each alert in a more compact, scannable format
    alerts.forEach((alert, index) => {
        const urgencyIcon = {
            'CRITICAL': '<i class="fas fa-square" style="color: #dc2626;"></i>',
            'HIGH': '<i class="fas fa-square" style="color: #f97316;"></i>',
            'MEDIUM': '<i class="fas fa-square" style="color: #eab308;"></i>'
        }[alert.urgency] || '<i class="fas fa-exclamation-triangle"></i>';
        
        const bgColor = {
            'CRITICAL': '#fee2e2',  // Darker red background
            'HIGH': '#fef3c7',      // Darker amber background
            'MEDIUM': '#dcfce7'     // Darker green background
        }[alert.urgency] || '#f9fafb';
        
        const textColor = {
            'CRITICAL': '#7f1d1d',  // Darker red text
            'HIGH': '#78350f',      // Darker amber text
            'MEDIUM': '#15803d'     // Darker green text
        }[alert.urgency] || '#374151';
        
        const borderColor = alert.urgency_color;
        
        html += `
            <div class="alert-item" style="padding: 12px; margin-bottom: 8px; background: ${bgColor}; border-left: 4px solid ${borderColor}; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <!-- Header Row: Product Name & Urgency Badge -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 600; font-size: 0.95em; color: ${textColor};">
                        ${urgencyIcon} ${alert.product_name}
                    </div>
                    <span style="background: ${borderColor}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.7em; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        ${alert.urgency}
                    </span>
                </div>
                
                <!-- Stock Status Row -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.85em; color: ${textColor};">
                    <span>
                        <strong>Stock:</strong> ${alert.current_stock} units
                    </span>
                    <span>
                        <strong style="color: ${borderColor};">Need:</strong> ${alert.shortage} more
                    </span>
                </div>
                
                <!-- Compact Forecast Row -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 8px; padding: 8px; background: rgba(255,255,255,0.7); border-radius: 4px; border: 1px solid rgba(0,0,0,0.05);">
                    <div style="text-align: center;">
                        <div style="font-size: 0.7em; color: ${textColor}; margin-bottom: 2px; font-weight: 500;">1-Day</div>
                        <div style="font-weight: 600; font-size: 0.85em; color: ${textColor};">${alert.forecasts['1_day'] || 'N/A'}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.7em; color: ${textColor}; margin-bottom: 2px; font-weight: 500;">7-Day</div>
                        <div style="font-weight: 600; font-size: 0.85em; color: ${textColor};">${alert.forecasts['7_day'] || 'N/A'}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.7em; color: ${textColor}; margin-bottom: 2px; font-weight: 500;">30-Day</div>
                        <div style="font-weight: 600; font-size: 0.85em; color: ${textColor};">${alert.forecasts['30_day'] || 'N/A'}</div>
                    </div>
                </div>
                
                <!-- Action Row: Recommended Order -->
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: ${{'CRITICAL': '#fecaca', 'HIGH': '#fde047', 'MEDIUM': '#86efac'}[alert.urgency] || '#e5e7eb'}; border-radius: 4px;">
                    <div style="font-size: 0.85em; font-weight: 600; color: ${textColor};">
                        <i class="fas fa-box"></i> Order: <span style="font-size: 1.1em; font-weight: 700;">${alert.recommended_order_qty}</span> units
                    </div>
                    <button class="btn btn-primary" style="padding: 5px 12px; font-size: 0.8em; background: ${borderColor}; border: none; cursor: pointer; color: white; border-radius: 4px; font-weight: 600;" onclick="quickRestock(${alert.product_id}, ${alert.recommended_order_qty})">
                        Order Now
                    </button>
                </div>
            </div>
        `;
    });
    
    alertsList.innerHTML = html;
}

// Quick restock action
function quickRestock(productId, quantity) {
    // Open inventory adjustment modal with pre-filled quantity
    const modal = document.getElementById('inventory-modal');
    if (modal) {
        // Find product details
        fetch(`/api/product/${productId}`, { credentials: 'same-origin' })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.product) {
                    document.getElementById('inventory-product-id').value = productId;
                    document.getElementById('inventory-product-name').textContent = data.product.name;
                    document.getElementById('inventory-current-stock').textContent = data.product.current_stock || 0;
                    document.getElementById('inventory-quantity').value = quantity;
                    document.querySelector('input[name="inventory-operation"][value="add"]').checked = true;
                    document.getElementById('inventory-reason').value = 'Restock based on forecast alert';
                    modal.style.display = 'flex';
                }
            })
            .catch(err => {
                console.error('Error fetching product details:', err);
                alert('Unable to load product details');
            });
    } else {
        alert(`Recommended restock: ${quantity} units for Product ID ${productId}`);
    }
}


function updateDashboardWithData(data) {
    // Hide monthly chart for 7-day period
    const monthlyChartContainer = document.getElementById('monthly-chart-container');
    if (monthlyChartContainer) {
        if (currentPeriod === '7d') {
            monthlyChartContainer.style.display = 'none';
        } else {
            monthlyChartContainer.style.display = 'block';
        }
    }
    
    // Update metric cards
    const totalUnits = document.getElementById('total-units');
    const totalRevenue = document.getElementById('total-revenue');
    const totalInventoryValue = document.getElementById('total-inventory-value');
    const accuracy = document.getElementById('accuracy');
    const alertsCount = document.getElementById('alerts-count');
    const turnoverRateEl = document.getElementById('turnover-rate');
    const fakeBanner = document.getElementById('fake-data-banner');
    const fakeCount = document.getElementById('fake-data-count');

    if (totalUnits) totalUnits.textContent = (data.total_units_sold || 0).toLocaleString('en-PH') + ' units';
    if (totalRevenue) totalRevenue.textContent = formatPHP(data.total_revenue);
    if (totalInventoryValue) totalInventoryValue.textContent = formatPHP(data.total_inventory_value || 0);
    // Accuracy summary card is driven by /api/metrics so it updates with every other card
    if (accuracy) accuracy.textContent = (data.accuracy !== undefined && data.accuracy !== null) ? data.accuracy.toFixed(1) + '%' : '--';
    if (alertsCount) alertsCount.textContent = data.alerts !== undefined ? data.alerts : 0;
    if (turnoverRateEl && typeof data.turnover_rate !== 'undefined') turnoverRateEl.textContent = Number(data.turnover_rate || 0).toFixed(2);

    // Synthetic data banner
    if (fakeBanner) {
        if (data.has_fake_data) {
            fakeBanner.style.display = 'block';
            if (fakeCount) {
                fakeCount.textContent = `( ${Number(data.fake_sales_count || 0).toLocaleString()} sales rows )`;
            }
        } else {
            fakeBanner.style.display = 'none';
        }
    }

    // Update change indicators
    const changeUnits = document.getElementById('change-units');
    const changeRevenue = document.getElementById('change-revenue');
    
    if (changeUnits && data.units_change !== null && data.units_change !== undefined) {
        const isPositive = data.units_change >= 0;
        changeUnits.textContent = (isPositive ? '+' : '') + data.units_change + '%';
        changeUnits.className = 'change ' + (isPositive ? 'positive' : 'negative');
        changeUnits.style.display = 'block';
    }
    
    if (changeRevenue && data.revenue_change !== null && data.revenue_change !== undefined) {
        const isPositive = data.revenue_change >= 0;
        changeRevenue.textContent = (isPositive ? '+' : '') + data.revenue_change + '%';
        changeRevenue.className = 'change ' + (isPositive ? 'positive' : 'negative');
        changeRevenue.style.display = 'block';
    }

    // Update comparison cards
    updateComparisonCard('current-month-revenue', 'last-month-revenue', 'month-revenue-change',
        data.current_month_revenue, data.last_month_revenue, data.month_revenue_change, true);
    updateComparisonCard('current-month-units', 'last-month-units', 'month-units-change',
        data.current_month_units, data.last_month_units, data.month_units_change, false);
    updateComparisonCard('current-year-revenue', 'last-year-revenue', 'year-revenue-change',
        data.current_ytd_revenue, data.year_ago_revenue, data.year_revenue_change, true);
    updateComparisonCard('current-year-units', 'last-year-units', 'year-units-change',
        data.current_ytd_units, data.year_ago_units, data.year_units_change, false);

    // Update charts with monthly daily revenue data (actual vs forecast)
    if (window.trendChart && data.monthly_daily_labels && data.monthly_daily_sales) {
        const labels = data.monthly_daily_labels || [];
        const actualData = data.monthly_daily_sales || [];
        const forecastData = data.monthly_daily_forecasts || [];
        
        window.trendChart.data.labels = labels;
        window.trendChart.data.datasets[0].data = actualData;
        window.trendChart.data.datasets[1].data = forecastData;
        window.trendChart.update();
    }

    // Store monthly chart data and update based on current view
    if (window.monthlyChart && data.monthly_labels && data.monthly_data) {
        // Store data for both views
        window.monthlyChartData = {
            monthly: {
                labels: data.monthly_labels || [],
                data: data.monthly_data || []
            },
            daily: {
                labels: data.monthly_daily_labels || [],
                data: data.monthly_daily_sales || []
            }
        };
        
        // Update chart using the current view type (preserve user's selection)
        const currentView = window.monthlyChartView || 'monthly';
        updateMonthlyChartView(currentView);
    }
}

// ==================== FORECAST VISUALIZATION FUNCTIONS ====================

// Populate product selector for forecast visualization
async function populateForecastProductSelector() {
    try {
        const res = await fetch('/api/products', { credentials: 'same-origin' });
        const data = await res.json();
        
        if (data.success && data.products) {
            const select = document.getElementById('forecast-viz-product-select');
            if (!select) return;
            
            // Clear existing options except the first one
            select.innerHTML = '<option value="">-- Choose a product --</option>';
            
            // Add product options
            data.products.forEach(product => {
                const option = document.createElement('option');
                option.value = product.id;
                option.textContent = `${product.name} (${product.category || 'Uncategorized'})`;
                select.appendChild(option);
            });
            
            // Add change event listener
            select.addEventListener('change', async (e) => {
                const productId = e.target.value;
                if (productId) {
                    await loadForecastVisualization(productId);
                } else {
                    document.getElementById('forecast-charts-container').style.display = 'none';
                }
            });
        }
    } catch (err) {
        console.error('Error loading products for forecast selector:', err);
    }
}

// Load and display forecast visualization for selected product
async function loadForecastVisualization(productId) {
    try {
        const container = document.getElementById('forecast-charts-container');
        container.style.display = 'block';
        
        // Fetch forecast visualization data
        const res = await fetch(`/api/forecast-visualization?product_id=${productId}&days_back=30`, { credentials: 'same-origin' });
        const data = await res.json();
        
        if (!data.success) {
            alert('Error loading forecast: ' + (data.error || 'Unknown error'));
            return;
        }
        
        // Render charts
        renderHistoricalVsPredictedChart(data);
        renderMultiHorizonChart(data);
        renderForecastMetrics(data);
        
        // Load model comparison separately
        loadModelComparisonChart();
        
    } catch (err) {
        console.error('Error loading forecast visualization:', err);
        alert('Failed to load forecast visualization: ' + err.message);
    }
}

// Chart 1: Historical vs Predicted with Confidence Intervals
function renderHistoricalVsPredictedChart(data) {
    const ctx = document.getElementById('forecast-historical-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (window.forecastHistoricalChart) {
        window.forecastHistoricalChart.destroy();
    }
    
    // Combine historical and forecast dates
    const allDates = [...data.historical.dates, ...data.forecast.dates];
    const historicalValues = [...data.historical.values, ...Array(data.forecast.dates.length).fill(null)];
    const forecastValues = [...Array(data.historical.dates.length).fill(null), ...data.forecast.values];
    const confidenceLower = [...Array(data.historical.dates.length).fill(null), ...data.forecast.confidence_lower];
    const confidenceUpper = [...Array(data.historical.dates.length).fill(null), ...data.forecast.confidence_upper];
    
    window.forecastHistoricalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: [
                {
                    label: 'Historical Sales',
                    data: historicalValues,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: '#667eea',
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'Predicted Sales',
                    data: forecastValues,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 3,
                    borderDash: [5, 5],
                    pointRadius: 4,
                    pointBackgroundColor: '#f59e0b',
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'Confidence Upper',
                    data: confidenceUpper,
                    borderColor: 'rgba(245, 158, 11, 0.3)',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1',
                    tension: 0.4
                },
                {
                    label: 'Confidence Lower',
                    data: confidenceLower,
                    borderColor: 'rgba(245, 158, 11, 0.3)',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        filter: (item) => item.text !== 'Confidence Upper' && item.text !== 'Confidence Lower',
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += Math.round(context.parsed.y) + ' units';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Sales Units'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
}

// Chart 2: Multi-Horizon Forecast Comparison
function renderMultiHorizonChart(data) {
    const ctx = document.getElementById('forecast-multihorizon-chart');
    if (!ctx) return;
    
    // Destroy existing chart
    if (window.forecastMultiHorizonChart) {
        window.forecastMultiHorizonChart.destroy();
    }
    
    // Take first 30 forecast values and group by horizons
    const forecast1d = data.forecast.values.slice(0, 1);
    const forecast7d = data.forecast.values.slice(0, 7);
    const forecast30d = data.forecast.values.slice(0, 30);
    
    const avg1d = forecast1d.length ? forecast1d.reduce((a,b) => a+b, 0) / forecast1d.length : 0;
    const avg7d = forecast7d.length ? forecast7d.reduce((a,b) => a+b, 0) / forecast7d.length : 0;
    const avg30d = forecast30d.length ? forecast30d.reduce((a,b) => a+b, 0) / forecast30d.length : 0;
    
    window.forecastMultiHorizonChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['1-Day', '7-Day', '30-Day'],
            datasets: [{
                label: 'Average Forecast',
                data: [avg1d, avg7d, avg30d],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(16, 185, 129, 0.7)'
                ],
                borderColor: [
                    'rgb(239, 68, 68)',
                    'rgb(245, 158, 11)',
                    'rgb(16, 185, 129)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Avg: ' + Math.round(context.parsed.y) + ' units';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Average Units'
                    }
                }
            }
        }
    });
}

// Load and render model comparison chart
async function loadModelComparisonChart() {
    try {
        const res = await fetch('/api/model-comparison', { credentials: 'same-origin' });
        const data = await res.json();
        
        if (!data.success || !data.models || data.models.length === 0) {
            return;
        }
        
        const ctx = document.getElementById('forecast-model-comparison-chart');
        if (!ctx) return;
        
        // Destroy existing chart
        if (window.forecastModelComparisonChart) {
            window.forecastModelComparisonChart.destroy();
        }
        
        const models = data.models;
        const labels = models.map(m => m.model);
        const maeData = models.map(m => m.avg_mae);
        const rmseData = models.map(m => m.avg_rmse);
        
        window.forecastModelComparisonChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'MAE (Mean Absolute Error)',
                        data: maeData,
                        backgroundColor: 'rgba(102, 126, 234, 0.7)',
                        borderColor: 'rgb(102, 126, 234)',
                        borderWidth: 2
                    },
                    {
                        label: 'RMSE (Root Mean Squared Error)',
                        data: rmseData,
                        backgroundColor: 'rgba(245, 158, 11, 0.7)',
                        borderColor: 'rgb(245, 158, 11)',
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Error Magnitude (lower is better)'
                        }
                    }
                }
            }
        });
        
    } catch (err) {
        console.error('Error loading model comparison:', err);
    }
}

// Render forecast metrics summary
function renderForecastMetrics(data) {
    const container = document.getElementById('forecast-metrics-summary');
    if (!container) return;
    
    const metrics = data.metrics || {};
    const product = data.product || {};
    
    container.innerHTML = `
        <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
            <div style="font-size: 0.85em; color: #6b7280; margin-bottom: 5px;">Current Stock</div>
            <div style="font-size: 1.5em; font-weight: bold; color: #374151;">${product.current_stock || 0} units</div>
        </div>
        <div style="background: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b;">
            <div style="font-size: 0.85em; color: #6b7280; margin-bottom: 5px;">Model Used</div>
            <div style="font-size: 1.2em; font-weight: bold; color: #374151;">${metrics.model_used || 'N/A'}</div>
        </div>
        <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
            <div style="font-size: 0.85em; color: #6b7280; margin-bottom: 5px;">MAE (Error)</div>
            <div style="font-size: 1.5em; font-weight: bold; color: #374151;">${metrics.mae || 'N/A'}</div>
        </div>
        <div style="background: #fce7f3; padding: 15px; border-radius: 8px; border-left: 4px solid #ec4899;">
            <div style="font-size: 0.85em; color: #6b7280; margin-bottom: 5px;">RMSE (Error)</div>
            <div style="font-size: 1.5em; font-weight: bold; color: #374151;">${metrics.rmse || 'N/A'}</div>
        </div>
        <div style="background: #ede9fe; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
            <div style="font-size: 0.85em; color: #6b7280; margin-bottom: 5px;">Total Forecasts</div>
            <div style="font-size: 1.5em; font-weight: bold; color: #374151;">${metrics.total_forecasts || 0}</div>
        </div>
    `;
}

// Initialize forecast visualization on page load
document.addEventListener('DOMContentLoaded', function() {
    // Populate product selector if on forecasting tab
    const forecastSelect = document.getElementById('forecast-viz-product-select');
    if (forecastSelect) {
        populateForecastProductSelector();
    }
});

// Guard flags to prevent double-submission on login/register forms
let _loginInProgress = false;
let _registerInProgress = false;

async function handleLogin(event) {
    event.preventDefault();
    if (_loginInProgress) return;
    _loginInProgress = true;

    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // Show loading state
    submitBtn.textContent = 'Logging in...';
    submitBtn.disabled = true;

    const formData = new FormData(form);
    const data = {
        username: formData.get('username'),
        password: formData.get('password')
    };

    let _loginSucceeded = false;

    try {
        const response = await fetchWithCsrf('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            _loginSucceeded = true;
            showMessage('login-messages', 'Login successful! Redirecting...', 'success');
            
            // Signal to browser that credentials are correct (helps with password saving)
            // Keep the form inputs intact until navigation
            form.querySelector('input[name="username"]').setAttribute('data-login-success', 'true');
            form.querySelector('input[name="password"]').setAttribute('data-login-success', 'true');
            
            setTimeout(() => {
                const redirectUrl = result.redirect || '/dashboard';
                window.location.href = getSafeRedirectUrl(redirectUrl, '/dashboard');
            }, 500);
        } else {
            showMessage('login-messages', result.message || 'Login failed', 'error');
        }
    } catch (error) {
        showMessage('login-messages', 'Network error. Please try again.', 'error');
    } finally {
        if (!_loginSucceeded) {
            // Only unlock on failure - on success keep button disabled and lock held during redirect window
            _loginInProgress = false;
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }
}

async function handleRegister(event) {
    event.preventDefault();
    if (_registerInProgress) return;
    _registerInProgress = true;

    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // Show loading state
    submitBtn.textContent = 'Registering...';
    submitBtn.disabled = true;

    const formData = new FormData(form);
    const data = {
        username: formData.get('username'),
        email: formData.get('email'),
        password: formData.get('password'),
        role: formData.get('role')
    };

    try {
        const response = await fetchWithCsrf('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showMessage('register-messages', 'Registration successful! You can now login.', 'success');
            setTimeout(() => {
                switchModal('loginModal');
            }, 1500);
        } else {
            showMessage('register-messages', result.message || 'Registration failed', 'error');
        }
    } catch (error) {
        showMessage('register-messages', 'Network error. Please try again.', 'error');
    } finally {
        _registerInProgress = false;
        // Reset button state
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

function showMessage(containerId, message, type) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `<div class="alert ${type}">${message}</div>`;
    }
}

/* ── Dark-mode Chart.js defaults (applied once before any chart is created) ── */
function setupChartDefaults() {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.color = '#a3a3a3';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.07)';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15,15,15,0.96)';
    Chart.defaults.plugins.tooltip.titleColor = '#f5f5f5';
    Chart.defaults.plugins.tooltip.bodyColor = '#a3a3a3';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.1)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.legend.labels.color = '#a3a3a3';
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.padding = 16;
    Chart.defaults.font.family = "'Roboto', sans-serif";
}

// Store chart instances globally so we can update them
let trendChart = null;
let monthlyChart = null;

// Expose charts to window for updates
window.trendChart = null;
window.monthlyChart = null;
window.monthlyChartView = 'monthly'; // Track current view: 'monthly' or 'daily'
window.monthlyChartData = null; // Store data for view switching

// Chart initialization function
function initializeCharts() {
    setupChartDefaults();

    // Initialize empty charts - will be populated with real data from API
    const labels = [];
    const emptyData = [];

    // Trend Chart (Line Chart) - Forecast Validation: Actual vs Forecasted Revenue
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        const tc = trendCtx.getContext('2d');
        const grad1 = tc.createLinearGradient(0, 0, 0, 380);
        grad1.addColorStop(0, 'rgba(52,211,153,0.35)');
        grad1.addColorStop(1, 'rgba(52,211,153,0.0)');
        const grad2 = tc.createLinearGradient(0, 0, 0, 380);
        grad2.addColorStop(0, 'rgba(129,140,248,0.28)');
        grad2.addColorStop(1, 'rgba(129,140,248,0.0)');

        trendChart = new Chart(tc, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Actual Revenue',
                    data: emptyData,
                    borderColor: '#34d399',
                    backgroundColor: grad1,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#34d399',
                    pointBorderColor: '#121212',
                    pointBorderWidth: 2
                }, {
                    label: 'Forecasted Revenue',
                    data: emptyData,
                    borderColor: '#818cf8',
                    backgroundColor: grad2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#818cf8',
                    pointBorderColor: '#121212',
                    pointBorderWidth: 2,
                    borderDash: [6, 3]
                }]
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    title: {
                        display: true,
                        text: 'Forecast Validation: Actual vs Predicted Revenue',
                        color: '#f5f5f5',
                        font: { size: 14, weight: '500' }
                    },
                    subtitle: {
                        display: true,
                        text: 'Compare predictions with actual sales to validate model accuracy',
                        font: { size: 11 },
                        color: '#6b7280',
                        padding: { bottom: 10 }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + formatPHP(context.parsed.y);
                            },
                            afterBody: function(tooltipItems) {
                                const idx = tooltipItems[0].dataIndex;
                                const actual = tooltipItems[0].chart.data.datasets[0].data[idx];
                                const forecast = tooltipItems[0].chart.data.datasets[1].data[idx];
                                if (actual && forecast && actual > 0) {
                                    const diff = forecast - actual;
                                    const accuracy = Math.max(0, 100 - Math.abs(diff / actual) * 100);
                                    return [
                                        '',
                                        'Accuracy: ' + accuracy.toFixed(1) + '%',
                                        'Diff: ' + (diff >= 0 ? '+' : '') + formatPHP(diff),
                                        accuracy >= 90 ? 'Excellent' : (accuracy >= 80 ? 'Good' : 'Needs improvement')
                                    ];
                                }
                                return [];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: { color: '#a3a3a3' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: {
                            color: '#a3a3a3',
                            callback: function(value) { return formatPHP(value); }
                        },
                        title: { display: true, text: 'Revenue (₱)', color: '#a3a3a3' }
                    }
                }
            }
        });
        window.trendChart = trendChart;
    }

    // Monthly Performance Chart (Switchable: Bar Chart for Monthly / Line Chart for Daily)
    const monthlyCtx = document.getElementById('monthlyChart');
    if (monthlyCtx) {
        const mc = monthlyCtx.getContext('2d');
        const barGrad = mc.createLinearGradient(0, 0, 0, 380);
        barGrad.addColorStop(0, 'rgba(99,102,241,0.9)');
        barGrad.addColorStop(1, 'rgba(67,56,202,0.55)');

        monthlyChart = new Chart(mc, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Monthly Sales',
                    data: [],
                    backgroundColor: barGrad,
                    borderColor: 'rgba(129,140,248,0.6)',
                    borderWidth: 0,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Monthly Sales Performance',
                        color: '#f5f5f5',
                        font: { size: 14, weight: '500' }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Monthly Sales: ' + formatPHP(context.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: { color: '#a3a3a3' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: {
                            color: '#a3a3a3',
                            callback: function(value) { return formatPHP(value); }
                        },
                        title: { display: true, text: 'Revenue (₱)', color: '#a3a3a3' }
                    }
                }
            }
        });
        window.monthlyChart = monthlyChart;
    }

    // Alerts are handled by fetchEnhancedRestockAlerts() called on DOMContentLoaded

    console.log('Enhanced dashboard loaded with charts');
}

// Function to update charts with forecast data
function updateChartsWithForecast(forecastResult) {
    if (trendChart) {
        trendChart.data.labels = forecastResult.labels;
        trendChart.data.datasets[0].data = forecastResult.actual_data;
        trendChart.data.datasets[1].data = forecastResult.forecast_data;
        trendChart.update();
    }

    // Update metric cards (removed accuracy)
    const totalActual = document.getElementById('total-actual');
    const turnover = document.getElementById('turnover-rate');
    const alertsCount = document.getElementById('alerts-count');

    if (totalActual) totalActual.textContent = forecastResult.total_sales;
    if (turnover) turnover.textContent = forecastResult.turnover.toFixed(2);
    if (alertsCount) alertsCount.textContent = forecastResult.alerts_count;
}

// ==================== PRODUCT MANAGEMENT FUNCTIONS (GLOBAL SCOPE) ====================
// These need to be in global scope for onclick handlers to work

let currentEditingProductId = null;
let currentDeletingProduct = null;
let currentInventoryProduct = null;

// Product Modal Functions
window.openProductModal = function(productId = null) {
    console.log('[Products] openProductModal called with ID:', productId);
    const modal = document.getElementById('product-modal');
    const title = document.getElementById('product-modal-title');
    const form = document.getElementById('product-modal-form');
    
    if (!modal || !title || !form) {
        console.error('[Products] Modal elements not found!');
        return;
    }
    
    // Reset form
    form.reset();
    document.getElementById('modal-product-id').value = '';
    
    if (productId) {
        title.textContent = 'Edit Product';
        currentEditingProductId = productId;
        
        // Load product data
        fetch(`/api/products/${productId}`, { credentials: 'same-origin' })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.product) {
                    document.getElementById('modal-product-id').value = data.product.id;
                    document.getElementById('modal-product-name').value = data.product.name;
                    document.getElementById('modal-product-category').value = data.product.category || '';
                    document.getElementById('modal-product-cost').value = data.product.unit_cost || '';
                }
            });
    } else {
        title.textContent = 'Add New Product';
        currentEditingProductId = null;
    }
    
    modal.classList.add('show');
};

window.openEditProductModal = function(productId) {
    window.openProductModal(productId);
};

window.closeProductModal = function() {
    const modal = document.getElementById('product-modal');
    if (modal) {
        modal.classList.remove('show');
    }
    currentEditingProductId = null;
};

// Delete Modal Functions
window.openDeleteModal = function(productId, productName) {
    console.log('[Products] openDeleteModal called:', productId, productName);
    const modal = document.getElementById('delete-modal');
    const message = document.getElementById('delete-modal-message');
    const warning = document.getElementById('delete-modal-warning');
    
    if (!modal || !message || !warning) {
        console.error('[Products] Delete modal elements not found!');
        return;
    }
    
    currentDeletingProduct = { id: productId, name: productName };
    
    message.textContent = `Checking data for "${productName}"...`;
    warning.innerHTML = '⏳ Loading impact assessment...';
    warning.style.display = 'block';
    
    // Get impact assessment WITHOUT actually deleting
    fetch(`/api/products/${productId}?confirm=false`, {
        method: 'DELETE',
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.action === 'confirm_required' && data.impact_assessment) {
            const alerts = data.impact_assessment.alerts;
            
            // Update modal message
            message.innerHTML = `
                <div style="margin-bottom: 12px;">
                    <strong><i class="fas fa-exclamation-triangle"></i> DELETE "${productName}"?</strong>
                    <p style="font-size: 0.9em; color: #6b7280; margin-top: 4px;">This action <strong>cannot be undone</strong>. The following data will be permanently deleted:</p>
                </div>
            `;
            
            // Format the warnings
            const warningHTML = `
                <div style="background: #fef2f2; border: 2px solid #fecaca; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                    <p style="color: #991b1b; font-weight: 600; margin: 0 0 8px 0;"><i class="fas fa-exclamation-triangle"></i> Data Impact:</p>
                    <ul style="margin: 0; padding-left: 20px; color: #7f1d1d; font-size: 0.9em; line-height: 1.6;">
                        ${alerts.map(alert => `<li>${alert}</li>`).join('')}
                    </ul>
                </div>
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px; border-radius: 4px; font-size: 0.85em; color: #78350f;">
                    <strong><i class="fas fa-lightbulb"></i> Recommendation:</strong> Consider archiving or disabling the product instead of permanent deletion.
                    <br><strong>Next Step:</strong> After deletion, you may need to regenerate forecasts for other products.
                </div>
            `;
            
            warning.innerHTML = warningHTML;
            warning.style.display = 'block';
            
            // Update the delete button to trigger actual deletion
            const confirmBtn = document.getElementById('confirm-delete-btn');
            if (confirmBtn) {
                confirmBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Yes, Delete Permanently';
                confirmBtn.style.backgroundColor = '#dc2626';
                confirmBtn.style.color = 'white';
            }
        }
    })
    .catch(error => {
        console.error('Error getting impact assessment:', error);
        warning.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Error: ${error.message}`;
    });
    
    modal.classList.add('show');
};

window.closeDeleteModal = function() {
    const modal = document.getElementById('delete-modal');
    if (modal) {
        modal.classList.remove('show');
    }
    currentDeletingProduct = null;
};

// Inventory Adjustment Modal Functions
window.openInventoryModal = function(productId, productName, currentStock) {
    console.log('[Products] openInventoryModal called:', productId, productName, currentStock);
    const modal = document.getElementById('inventory-modal');
    const form = document.getElementById('inventory-modal-form');
    
    if (!modal || !form) {
        console.error('[Products] Inventory modal elements not found!');
        return;
    }
    
    form.reset();
    document.getElementById('inventory-product-id').value = productId;
    document.getElementById('inventory-product-name').textContent = productName;
    document.getElementById('inventory-current-stock').textContent = currentStock;
    
    currentInventoryProduct = { id: productId, name: productName, stock: currentStock };
    
    modal.classList.add('show');
};

window.closeInventoryModal = function() {
    const modal = document.getElementById('inventory-modal');
    if (modal) {
        modal.classList.remove('show');
    }
    currentInventoryProduct = null;
};

// ==================== END PRODUCT MANAGEMENT FUNCTIONS ====================

// Initialize export buttons for admin/manager users
document.addEventListener('DOMContentLoaded', function() {
    const exportAlertsBtn = document.getElementById('export-alerts-csv');
    const downloadReportBtn = document.getElementById('download-report');

    if (exportAlertsBtn) {
        exportAlertsBtn.addEventListener('click', function() {
            window.location.href = '/api/export-alerts';
        });
    }

    if (downloadReportBtn) {
        downloadReportBtn.addEventListener('click', function() {
            window.location.href = '/api/export-report';
        });
    }

    // --- Data Management Handlers ---

    // Upload CSV file
    const uploadCsvBtn = document.getElementById('upload-csv-btn');
    if (uploadCsvBtn) {
        uploadCsvBtn.addEventListener('click', async function() {
            const fileInput = document.getElementById('csv-import');
            const importStatus = document.getElementById('import-status');

            if (!fileInput.files.length) {
                importStatus.innerHTML = '<span style="color: #dc3545;">Please select a file</span>';
                return;
            }

            const file = fileInput.files[0];
            if (!file.name.endsWith('.csv')) {
                importStatus.innerHTML = '<span style="color: #dc3545;">Only CSV files are allowed</span>';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);
            // Always use unified_sales format (data type selector removed from UI)
            formData.append('data_type', 'unified_sales');

            try {
                // Show initial progress bar
                importStatus.innerHTML = `
                    <div style="color: #007bff; padding: 15px; background: #e7f3ff; border-radius: 8px; border-left: 4px solid #007bff; box-shadow: 0 2px 8px rgba(0,123,255,0.2);">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                            <div style="width: 20px; height: 20px; border: 3px solid #007bff; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                            <div>
                                <strong style="font-size: 1.1em;">⏳ Uploading & Processing CSV...</strong><br/>
                                <small style="opacity: 0.9;">Please do not close this page.</small>
                            </div>
                        </div>
                        <div style="width: 100%; background: #d4e8f7; border-radius: 10px; overflow: hidden; height: 25px; position: relative;">
                            <div id="upload-progress-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #007bff, #0056b3); transition: width 0.3s ease; display: flex; align-items: center; justify-content: center;">
                                <span id="upload-progress-text" style="color: white; font-weight: bold; font-size: 0.85em; position: absolute; left: 50%; transform: translateX(-50%); text-shadow: 0 1px 2px rgba(0,0,0,0.3);">0%</span>
                            </div>
                        </div>
                        <div id="upload-stage" style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">Uploading file...</div>
                    </div>
                    <style>
                        @keyframes spin { to { transform: rotate(360deg); } }
                    </style>
                `;
                uploadCsvBtn.disabled = true;
                uploadCsvBtn.textContent = '⏳ Uploading...';
                uploadCsvBtn.style.cursor = 'not-allowed';
                uploadCsvBtn.style.opacity = '0.6';
                
                // Use XMLHttpRequest to track upload progress
                const xhr = new XMLHttpRequest();
                const progressBar = document.getElementById('upload-progress-bar');
                const progressText = document.getElementById('upload-progress-text');
                const uploadStage = document.getElementById('upload-stage');
                
                // Track upload progress
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        if (progressBar && progressText) {
                            progressBar.style.width = percentComplete + '%';
                            progressText.textContent = Math.round(percentComplete) + '%';
                        }
                        if (uploadStage) {
                            if (percentComplete < 100) {
                                uploadStage.textContent = 'Uploading file...';
                            } else {
                                uploadStage.textContent = 'Processing data and generating forecasts...';
                            }
                        }
                    }
                });
                
                // Handle completion
                xhr.addEventListener('load', () => {
                    if (progressBar && progressText) {
                        progressBar.style.width = '100%';
                        progressText.textContent = '100%';
                    }
                    
                    const response = xhr.response;
                    let result;
                    try {
                        result = JSON.parse(response);
                    } catch (e) {
                        importStatus.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px;"><strong>Error:</strong> Invalid server response</div>`;
                        uploadCsvBtn.disabled = false;
                        uploadCsvBtn.textContent = 'Upload CSV';
                        uploadCsvBtn.style.cursor = 'pointer';
                        uploadCsvBtn.style.opacity = '1';
                        return;
                    }

                    if (xhr.status === 200 && result.success) {
                        const rowsProcessed = (result.summary && result.summary.processed) || result.rows_processed || 0;
                        const forecastsFailed = (result.summary && result.summary.forecasts_failed) || 0;
                        const forecastsRetrained = (result.summary && result.summary.forecasts_regenerated) || 0;
                        
                        // Build success message with warnings
                        let statusHtml = `
                            <div style="color: #28a745; padding: 10px; background: #d4edda; border-radius: 4px; border-left: 4px solid #28a745;">
                                <strong><i class="fas fa-check-circle"></i> CSV Upload Complete!</strong><br/>
                                <small style="white-space: pre-wrap;">${result.message}</small>
                            </div>
                        `;
                        
                        // Show warnings if present (forecast failures are critical)
                        if (result.warnings && result.warnings.length > 0) {
                            statusHtml += `
                                <div style="color: #856404; padding: 12px; background: #fff3cd; border-radius: 4px; border-left: 4px solid #ffc107; margin-top: 10px;">
                                    <strong><i class="fas fa-exclamation-triangle"></i> Warnings:</strong><br/>
                                    <ul style="margin: 8px 0 0 20px; padding: 0;">
                                        ${result.warnings.map(w => `<li style="margin: 4px 0;">${w}</li>`).join('')}
                                    </ul>
                                    ${forecastsFailed > 0 ? '<br/><small><strong>Action Required:</strong> Re-upload this CSV or run manual forecast generation.</small>' : ''}
                                </div>
                            `;
                        }
                        
                        // Show forecast errors if present
                        if (result.forecast_errors && result.forecast_errors.length > 0) {
                            statusHtml += `
                                <div style="color: #721c24; padding: 12px; background: #f8d7da; border-radius: 4px; border-left: 4px solid #dc3545; margin-top: 10px;">
                                    <strong><i class="fas fa-exclamation-circle"></i> Forecast Generation Errors:</strong><br/>
                                    <ul style="margin: 8px 0 0 20px; padding: 0; max-height: 200px; overflow-y: auto;">
                                        ${result.forecast_errors.map(e => `<li style="margin: 4px 0; font-size: 0.9em;">${e}</li>`).join('')}
                                    </ul>
                                    <small style="display: block; margin-top: 8px;"><strong>What to do:</strong> Review errors above, then either upload cleaned data or run: <code>python generate_forecasts.py</code></small>
                                </div>
                            `;
                        }
                        
                        // Success indicator with forecast status
                        if (forecastsRetrained === 0 && result.summary && result.summary.forecasts_skipped === 0 && forecastsFailed === 0) {
                            // No forecast generation attempted (non-sales upload)
                            statusHtml += `<div style="color: #6c757d; padding: 8px; background: #e9ecef; border-radius: 4px; margin-top: 10px; font-size: 0.9em;">ℹ️ Forecast generation not applicable for this data type.</div>`;
                        }
                        
                        importStatus.innerHTML = statusHtml;
                        fileInput.value = '';
                        
                        // Reload imports list
                        loadImportsList();
                        // Refresh forecast accuracy after new data import
                        fetchForecastAccuracy();
                        // Refresh weekly forecast preview
                        fetchWeeklyForecast();
                        // Refresh enhanced restock alerts
                        fetchEnhancedRestockAlerts();
                        // Refresh synchronized daily/weekly forecasts
                        if (typeof loadSynchronizedForecasts === 'function') {
                            const productSelect = document.getElementById('sync-forecast-product-select');
                            const selectedProduct = productSelect ? productSelect.value : null;
                            loadSynchronizedForecasts(selectedProduct);
                        }
                    } else {
                        importStatus.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px;"><strong>Error:</strong> ${result.error || 'Upload failed'}</div>`;
                    }
                    
                    uploadCsvBtn.disabled = false;
                    uploadCsvBtn.textContent = 'Upload CSV';
                    uploadCsvBtn.style.cursor = 'pointer';
                    uploadCsvBtn.style.opacity = '1';
                });
                
                // Handle errors
                xhr.addEventListener('error', () => {
                    importStatus.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px;"><strong>Upload failed:</strong> Network error</div>`;
                    uploadCsvBtn.disabled = false;
                    uploadCsvBtn.textContent = 'Upload CSV';
                    uploadCsvBtn.style.cursor = 'pointer';
                    uploadCsvBtn.style.opacity = '1';
                });
                
                // Send request
                xhr.open('POST', '/api/upload-csv');
                xhr.send(formData);
                
            } catch (error) {
                importStatus.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px;"><strong>Upload failed:</strong> ${error.message}</div>`;
                uploadCsvBtn.disabled = false;
                uploadCsvBtn.textContent = 'Upload CSV';
                uploadCsvBtn.style.cursor = 'pointer';
                uploadCsvBtn.style.opacity = '1';
            }
        });
    }

    // Download all data
    const downloadAllDataBtn = document.getElementById('download-all-data-btn');
    if (downloadAllDataBtn) {
        downloadAllDataBtn.addEventListener('click', async function() {
            try {
                const response = await fetch('/api/download-all-data', { credentials: 'same-origin' });
                if (response.ok) {
                    // Get filename from Content-Disposition header
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'dashboard_data.csv';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
                        if (filenameMatch) filename = filenameMatch[1];
                    }

                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(link);
                } else {
                    alert('Failed to download data');
                }
            } catch (error) {
                alert(`Download error: ${error.message}`);
            }
        });
    }

    // Load imports list
    window.loadImportsList = function() {
        const importsList = document.getElementById('imports-list');
        if (!importsList) return;

        fetch('/api/list-imports', { credentials: 'same-origin' })
            .then(response => {
                if (response.status === 401) {
                    throw new Error('Session expired - please log in again');
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.imports && data.imports.length > 0) {
                    importsList.innerHTML = data.imports.map(imp => {
                        const statusClass = imp.status === 'success' ? 'success' : (imp.status === 'partial' ? 'partial' : 'failed');
                        return `
                            <div class="import-item">
                                <strong>${imp.filename}</strong>
                                <span class="import-status-badge ${statusClass}">${imp.status.toUpperCase()}</span>
                                <br/>
                                <small style="color: #666;">
                                    ${imp.upload_date} | ${imp.data_type || 'unknown'} | 
                                    <i class="fas fa-check"></i> New: ${imp.rows_processed} | 
                                    ${imp.rows_skipped > 0 ? `<i class="fas fa-forward"></i> Skipped: ${imp.rows_skipped} | ` : ''}
                                    ${imp.rows_failed > 0 ? `<i class="fas fa-times"></i> Failed: ${imp.rows_failed} | ` : ''}
                                    User: ${imp.username}
                                </small>
                                ${imp.validation_errors ? `<br/><small style="color: #856404; background: #fff3cd; padding: 2px 6px; border-radius: 3px;"><i class="fas fa-exclamation-triangle"></i> ${imp.validation_errors}</small>` : ''}
                                ${imp.error_message ? `<br/><small style="color: #dc3545;"><i class="fas fa-times-circle"></i> ${imp.error_message.substring(0, 100)}</small>` : ''}
                            </div>
                        `;
                    }).join('');
                } else {
                    importsList.innerHTML = '<p style="padding: 20px; color: #999; text-align: center;">No previous imports</p>';
                }
            })
            .catch(error => {
                console.error('Error loading imports:', error);
                importsList.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <p style="color: #dc3545; margin: 0 0 12px;"><i class="fas fa-exclamation-triangle"></i> Error: ${error.message}</p>
                        <button onclick="loadImportsList()" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem;">
                            <i class="fas fa-sync-alt"></i> Retry
                        </button>
                    </div>
                `;
            });
    }

    // Upload CSV with data type selection
    const uploadBtn = document.getElementById('upload-csv-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', async function() {
            const fileInput = document.getElementById('csv-import');
            const statusDiv = document.getElementById('import-status');
            
            if (!fileInput.files[0]) {
                statusDiv.innerHTML = '<p style="color: #dc3545;">Please select a CSV file</p>';
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            // Always use unified_sales format (data type selector removed from UI)
            formData.append('data_type', 'unified_sales');

            statusDiv.innerHTML = '<p style="color: #007bff;">Uploading and validating...</p>';

            try {
                const response = await fetch('/api/upload-csv', {
                    method: 'POST',
                    credentials: 'same-origin',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    const summary = result.summary;
                    statusDiv.innerHTML = `
                        <div style="color: #28a745; background: #d4edda; padding: 12px; border-radius: 4px; border: 1px solid #c3e6cb;">
                            <strong><i class="fas fa-check-circle"></i> Import Successful</strong><br/>
                            <div style="margin-top: 8px; font-size: 13px; line-height: 1.6;">
                                <i class="fas fa-chart-bar"></i> Total Rows: <strong>${summary.total_rows}</strong><br/>
                                <i class="fas fa-check-circle"></i> New Records: <strong>${summary.new_records}</strong><br/>
                                ${summary.duplicates_found > 0 ? `<i class="fas fa-forward"></i> Duplicates Skipped: <strong>${summary.duplicates_found}</strong><br/>` : ''}
                                ${summary.failed > 0 ? `<i class="fas fa-times-circle"></i> Failed: <strong>${summary.failed}</strong>` : ''}
                            </div>
                        </div>
                    `;
                    fileInput.value = '';
                    loadImportsList();
                    // Reload products if products were imported
                    if (dataTypeSelect.value === 'products') {
                        loadProducts();
                    }
                    // Refresh forecast accuracy after sales data import
                    if (dataTypeSelect.value === 'sales') {
                        fetchForecastAccuracy();
                        fetchWeeklyForecast();
                        fetchEnhancedRestockAlerts();
                    }
                } else {
                    // Handle validation errors with detailed formatting
                    let errorHTML = result.error || 'Unknown error occurred';
                    
                    // If error contains newlines, format as list
                    if (errorHTML.includes('\n')) {
                        const lines = errorHTML.split('\n').filter(line => line.trim());
                        errorHTML = lines.map(line => {
                            // Highlight row numbers and product names
                            line = line.replace(/Row (\d+):/g, '<strong style="color: #991b1b;">Row $1:</strong>');
                            line = line.replace(/'([^']+)'/g, '<code style="background: #fee2e2; padding: 2px 6px; border-radius: 3px; font-size: 0.9em;">$1</code>');
                            return line;
                        }).join('<br/>');
                    }
                    
                    statusDiv.innerHTML = `
                        <div style="color: #991b1b; background: #fee2e2; padding: 16px; border-radius: 6px; border: 2px solid #fecaca; max-height: 400px; overflow-y: auto;">
                            <strong style="font-size: 1.1em;"><i class="fas fa-times-circle"></i> Import Rejected</strong><br/>
                            <div style="margin-top: 12px; font-size: 13px; line-height: 1.8; white-space: pre-wrap; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                                ${errorHTML}
                            </div>
                            ${result.total_unknown ? `
                                <div style="margin-top: 12px; padding: 10px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px; color: #78350f; font-size: 0.85em;">
                                    <strong><i class="fas fa-lightbulb"></i> Next Steps:</strong><br/>
                                    1. Add missing products manually using the "Add Product" button above<br/>
                                    2. OR fix typos in your CSV file and re-upload<br/>
                                    3. Check product names match exactly (case-sensitive)
                                </div>
                            ` : ''}
                        </div>
                    `;
                }
            } catch (error) {
                statusDiv.innerHTML = `
                    <div style="color: #dc3545; background: #f8d7da; padding: 12px; border-radius: 4px; border: 1px solid #f5c6cb;">
                        <strong><i class="fas fa-times-circle"></i> Upload Error</strong><br/>
                        ${error.message}
                    </div>
                `;
            }
        });
    }

    // Product Management Functions
    let topProductsChart = null;

    // Load products with enhanced UI - EXPOSE TO GLOBAL SCOPE
    window.loadProducts = function(searchTerm = '') {
        const productsList = document.getElementById('products-list');
        if (productsList) {
            console.log('[loadProducts] Starting to load products, searchTerm:', searchTerm);
        } else {
            console.warn('[loadProducts] products-list element not found!');
            return;
        }

        const url = searchTerm ? `/api/products?search=${encodeURIComponent(searchTerm)}` : '/api/products';
        console.log('[loadProducts] Fetching from:', url);

        fetch(url, { credentials: 'same-origin' })
            .then(response => {
                console.log('[loadProducts] Response status:', response.status);
                if (response.status === 401) {
                    throw new Error('Session expired - please log in again');
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('[loadProducts] Data received:', data);
                if (data.success && data.products && data.products.length > 0) {
                    console.log('[loadProducts] Rendering', data.products.length, 'products');
                    productsList.innerHTML = data.products.map(product => {
                        const stock = product.current_stock || 0;
                        let stockClass = 'high';
                        if (stock < 10) stockClass = 'low';
                        else if (stock < 50) stockClass = 'medium';

                        return `
                            <div class="product-item" data-product-id="${product.id}">
                                <div class="product-info">
                                    <div class="product-name">${product.name}</div>
                                    <div class="product-meta">
                                        <span><i class="fas fa-folder"></i> ${product.category || 'Uncategorized'}</span>
                                        <span><i class="fas fa-money-bill-wave"></i> ₱${parseFloat(product.unit_cost || 0).toFixed(2)}</span>
                                        <span class="stock-badge ${stockClass}"><i class="fas fa-box"></i> ${stock} units</span>
                                    </div>
                                </div>
                                <div class="product-actions">
                                    <button class="btn-stock" onclick="openInventoryModal(${product.id}, '${product.name.replace(/'/g, "\\'")}', ${stock})">
                                        <i class="fas fa-box"></i> Update
                                    </button>
                                    <button class="btn-edit" onclick="openEditProductModal(${product.id})">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    <button class="btn-delete" onclick="openDeleteModal(${product.id}, '${product.name.replace(/'/g, "\\'")}')">
                                        <i class="fas fa-trash-alt"></i> Delete
                                    </button>
                                </div>
                            </div>
                            `;
                        }).join('');
                } else {
                    productsList.innerHTML = `
                        <div style="text-align: center; padding: 60px 20px;">
                            <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;"><i class="fas fa-box" style="font-size: 3rem;"></i></div>
                            <p style="color: #9ca3af; font-size: 1rem; margin: 0;">No products found</p>
                            <p style="color: #d1d5db; font-size: 0.875rem; margin-top: 8px;">Try adjusting your search or add a new product</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading products:', error);
                productsList.innerHTML = `
                    <div style="text-align: center; padding: 60px 20px;">
                        <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;"><i class="fas fa-exclamation-triangle" style="font-size: 3rem;"></i></div>
                        <p style="color: #ef4444; font-size: 1rem; margin: 0;">Error loading products</p>
                        <p style="color: #fca5a5; font-size: 0.875rem; margin-top: 8px;">${error.message}</p>
                        <button onclick="loadProducts()" style="margin-top: 16px; padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem;">
                            <i class="fas fa-sync-alt"></i> Retry
                        </button>
                    </div>
                `;
            });
    };

    // Product Modal Form Submission
    const productModalForm = document.getElementById('product-modal-form');
    console.log('[Products] Product modal form element:', productModalForm);
    if (productModalForm) {
        console.log('[Products] Attaching submit event listener to product form');
        productModalForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('[Products] Product form submitted');

            const productId = document.getElementById('modal-product-id').value;
            const productData = {
                name: document.getElementById('modal-product-name').value,
                category: document.getElementById('modal-product-category').value,
                unit_cost: document.getElementById('modal-product-cost').value
            };

            // If creating a new product, handle initial stock
            const isNew = !productId;
            if (isNew) {
                const currentStock = parseInt(document.getElementById('modal-product-stock')?.value) || 0;
                productData.current_stock = currentStock;
                console.log('[Products] New product with stock:', currentStock);
            }

            try {
                console.log('[Products] Sending request:', { url: productId ? `/api/products/${productId}` : '/api/products', method: productId ? 'PUT' : 'POST', data: productData });
                const url = productId ? `/api/products/${productId}` : '/api/products';
                const method = productId ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productData),
                    credentials: 'same-origin'
                });

                console.log('[Products] Response status:', response.status);
                const result = await response.json();
                console.log('[Products] Response data:', result);

                if (result.success) {
                    console.log('[Products] Product operation successful');
                    showNotification(result.message, 'success');
                    closeProductModal();
                    loadProducts();
                } else {
                    console.error('[Products] Product operation failed:', result.error);
                    showNotification(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                console.error('[Products] Exception during product operation:', error);
                showNotification(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Confirm Delete Button - now with explicit confirmation
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    console.log('[Products] Confirm delete button element:', confirmDeleteBtn);
    if (confirmDeleteBtn) {
        console.log('[Products] Attaching click event listener to delete button');
        confirmDeleteBtn.addEventListener('click', async function() {
            console.log('[Products] Delete button clicked, product:', currentDeletingProduct);
            if (!currentDeletingProduct) return;

            // Disable button to prevent double-click
            confirmDeleteBtn.disabled = true;
            confirmDeleteBtn.innerHTML = '⏳ Deleting...';

            try {
                // Now actually delete with confirm=true
                const response = await fetch(`/api/products/${currentDeletingProduct.id}?confirm=true`, {
                    method: 'DELETE',
                    credentials: 'same-origin'
                });

                const result = await response.json();

                if (result.success) {
                    closeDeleteModal();
                    loadProducts();
                    
                    // Show success with next steps
                    const nextSteps = result.next_steps ? result.next_steps.join('\n') : '';
                    showNotification(`[OK] ${result.message}\n${nextSteps}`, 'success');
                } else {
                    showNotification(`Error: ${result.error}`, 'error');
                    confirmDeleteBtn.disabled = false;
                    confirmDeleteBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Yes, Delete Permanently';
                }
            } catch (error) {
                showNotification(`Error: ${error.message}`, 'error');
                confirmDeleteBtn.disabled = false;
                confirmDeleteBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Yes, Delete Permanently';
            }
        });
    }

    // Inventory Modal Form Submission
    const inventoryModalForm = document.getElementById('inventory-modal-form');
    console.log('[Products] Inventory modal form element:', inventoryModalForm);
    if (inventoryModalForm) {
        console.log('[Products] Attaching submit event listener to inventory form');
        inventoryModalForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('[Products] Inventory form submitted');
            
            const productId = document.getElementById('inventory-product-id').value;
            const quantity = parseInt(document.getElementById('inventory-quantity').value);
            const operation = document.querySelector('input[name="inventory-operation"]:checked').value;
            const reason = document.getElementById('inventory-reason').value;

            try {
                const response = await fetch('/api/inventory/adjust', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        product_id: productId,
                        quantity: quantity,
                        operation: operation,
                        reason: reason
                    })
                });

                const result = await response.json();

                if (result.success) {
                    closeInventoryModal();
                    loadProducts();
                    showNotification(`Stock updated! New stock: ${result.product.current_stock} units`, 'success');
                } else {
                    showNotification(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showNotification(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Notification Helper
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 9999;
            max-width: 400px;
            animation: slideInRight 0.3s ease-out;
            font-weight: 500;
        `;
        
        if (type === 'success') {
            notification.style.background = '#10b981';
            notification.style.color = 'white';
        } else if (type === 'error') {
            notification.style.background = '#ef4444';
            notification.style.color = 'white';
        } else {
            notification.style.background = '#3b82f6';
            notification.style.color = 'white';
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }

    // Add animation styles
    if (!document.getElementById('notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Product search
    const productSearch = document.getElementById('product-search');
    if (productSearch) {
        productSearch.addEventListener('input', function() {
            loadProducts(this.value);
        });
    }

    // Close modals on outside click
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('show');
        }
    });

    // Legacy function redirects (for backward compatibility)
    window.deleteProduct = function(productId, productName) {
        openDeleteModal(productId, productName);
    };

    window.adjustStock = function(productId, productName) {
        // Get current stock first
        fetch(`/api/products/${productId}`, { credentials: 'same-origin' })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.product) {
                    openInventoryModal(productId, productName, data.product.current_stock);
                }
            });
    };

    window.editProduct = function(productId) {
        openEditProductModal(productId);
    };

    // ======= Available periods for dropdowns (Top Products + Synchronized Views) =======
    async function fetchAvailablePeriods() {
        try {
            const res = await fetch('/api/available-periods', { credentials: 'same-origin' });
            const data = await res.json();
            if (!data.success) return null;
            return data;
        } catch (e) { return null; }
    }

    function populateTopProductsPeriodDropdowns(periods) {
        const ySel = document.getElementById('ranking-year');
        const mSel = document.getElementById('ranking-month');
        const wSel = document.getElementById('ranking-week');
        if (!ySel || !mSel || !wSel) return;

        // Helper: clear and add default option
        const resetSelect = (sel, placeholder) => {
            sel.innerHTML = '';
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = placeholder;
            sel.appendChild(opt);
        };

        resetSelect(ySel, '- Select -');
        (periods?.years || []).forEach(yr => {
            const opt = document.createElement('option');
            opt.value = yr;
            opt.textContent = yr;
            ySel.appendChild(opt);
        });

        const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];

        function refreshMonths() {
            resetSelect(mSel, '- Select -');
            resetSelect(wSel, '- Select -');
            const yr = ySel.value;
            if (!yr) return; // No year selected
            const months = periods?.monthsByYear?.[yr] || [];
            months.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = monthNames[m-1] || `Month ${m}`;
                mSel.appendChild(opt);
            });
        }

        function refreshWeeks() {
            resetSelect(wSel, '- Select -');
            const yr = ySel.value;
            const m = mSel.value;
            if (!yr || !m) return;
            const key = `${yr}-${String(m).padStart(2,'0')}`;
            const weeks = periods?.weeksByYearMonth?.[key] || [];
            weeks.forEach(w => {
                const opt = document.createElement('option');
                opt.value = w;
                opt.textContent = `Week ${w}`;
                wSel.appendChild(opt);
            });
        }

        ySel.onchange = () => { 
            // Clear period dropdown when year is selected
            const periodSel = document.getElementById('ranking-period');
            if (ySel.value && periodSel) {
                periodSel.value = '';
            }
            refreshMonths(); 
            refreshWeeks(); 
            loadTopProducts(); 
        };
        mSel.onchange = () => { 
            // Clear period dropdown when month is selected
            const periodSel = document.getElementById('ranking-period');
            if (mSel.value && periodSel) {
                periodSel.value = '';
            }
            refreshWeeks(); 
            loadTopProducts(); 
        };
        wSel.onchange = () => {
            // Clear period dropdown when week is selected
            const periodSel = document.getElementById('ranking-period');
            if (wSel.value && periodSel) {
                periodSel.value = '';
            }
            loadTopProducts();
        };

        // Initial state
        refreshMonths();
        refreshWeeks();
    }

    // Top Products Chart
    window.loadTopProducts = function() {
        console.log('[loadTopProducts] Function called');
        const canvas = document.getElementById('topProductsChart');
        if (!canvas) {
            console.warn('[loadTopProducts] Canvas not found!');
            return;
        }

        const period = document.getElementById('ranking-period')?.value || '7d';
        const metric = document.getElementById('ranking-metric')?.value || 'revenue';
        const year = document.getElementById('ranking-year')?.value || '';
        const month = document.getElementById('ranking-month')?.value || '';
        const week = document.getElementById('ranking-week')?.value || '';

        console.log('[loadTopProducts] Filters:', { period, metric, year, month, week });

        const params = new URLSearchParams({ limit: '10', metric });
        // If any calendar filter set, they override the period window
        if (year || month || week) {
            if (year) params.set('year', year);
            if (month) params.set('month', month);
            if (week) params.set('week', week);
        } else {
            params.set('period', period);
        }

        console.log('[loadTopProducts] Fetching from:', `/api/top-products?${params.toString()}`);

        fetch(`/api/top-products?${params.toString()}`, { credentials: 'same-origin' })
            .then(response => {
                console.log('[loadTopProducts] Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('[loadTopProducts] Data received:', data);
                if (data.success && data.products) {
                    console.log('[loadTopProducts] Products count:', data.products.length);
                    const labels = data.products.map(p => p.product_name);
                    const values = data.products.map(p => metric === 'revenue' ? p.total_revenue : p.total_quantity);
                    console.log('[loadTopProducts] Labels:', labels);
                    console.log('[loadTopProducts] Values:', values);

                    if (topProductsChart) {
                        topProductsChart.destroy();
                    }

                    // Period labels for better display
                    const periodLabels = {
                        '7d': 'Last 7 Days',
                        '30d': 'Last 30 Days',
                        '90d': 'Last 90 Days',
                        '1y': 'Last Year'
                    };

                    // Build dynamic title based on filters
                    let titleSuffix = '';
                    if (year || month || week) {
                        const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                        const parts = [];
                        if (year) parts.push(year);
                        if (month) parts.push(monthNames[(parseInt(month)-1)||0]);
                        if (week) parts.push(`Week ${week}`);
                        titleSuffix = parts.join(' • ');
                    } else {
                        titleSuffix = periodLabels[period] || period;
                    }

                    const ctx = canvas.getContext('2d');
                    topProductsChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: metric === 'revenue' ? 'Revenue (₱)' : 'Quantity Sold',
                                data: values,
                                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                                borderColor: 'rgba(102, 126, 234, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: {
                                    display: false
                                },
                                title: {
                                    display: true,
                                    text: `Top 10 Products by ${metric === 'revenue' ? 'Revenue' : 'Quantity'} - ${titleSuffix}`,
                                    font: {
                                        size: 16,
                                        weight: 'bold'
                                    },
                                    color: '#f5f5f5'
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(value) {
                                                return metric === 'revenue' ? formatPHP(value) : value;
                                        }
                                        },
                                        title: {
                                            display: true,
                                            text: metric === 'revenue' ? 'Revenue (₱)' : 'Quantity Sold'
                                    }
                                    },
                                    x: {
                                        ticks: {
                                            maxRotation: 45,
                                            minRotation: 45
                                        }
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.dataset.label || '';
                                            const value = context.parsed.y;
                                            return label + ': ' + (metric === 'revenue' ? formatPHP(value) : value);
                                        }
                                }
                            }
                        }
                    });
                } else {
                    console.warn('[loadTopProducts] No products or unsuccessful response:', data);
                }
            })
            .catch(error => {
                console.error('[loadTopProducts] Error loading top products:', error);
            });
    }

    // Event listeners for ranking controls
    const rankingPeriod = document.getElementById('ranking-period');
    const rankingMetric = document.getElementById('ranking-metric');
    const rankingYear = document.getElementById('ranking-year');
    const rankingMonth = document.getElementById('ranking-month');
    const rankingWeek = document.getElementById('ranking-week');
    
    if (rankingPeriod) {
        rankingPeriod.addEventListener('change', function() {
            // Clear calendar filters when period is selected
            if (rankingPeriod.value) {
                const rankingYear = document.getElementById('ranking-year');
                const rankingMonth = document.getElementById('ranking-month');
                const rankingWeek = document.getElementById('ranking-week');
                if (rankingYear) rankingYear.value = '';
                if (rankingMonth) rankingMonth.value = '';
                if (rankingWeek) rankingWeek.value = '';
            }
            loadTopProducts();
        });
    }
    
    if (rankingMetric) {
        rankingMetric.addEventListener('change', loadTopProducts);
    }

    // Export Top Products Report
    const exportTopProductsBtn = document.getElementById('export-top-products-btn');
    if (exportTopProductsBtn) {
        exportTopProductsBtn.addEventListener('click', async function() {
            const period = document.getElementById('ranking-period')?.value || '7d';
            const metric = document.getElementById('ranking-metric')?.value || 'revenue';
            
            try {
                const response = await fetch(`/api/top-products?limit=10&period=${period}&metric=${metric}`, { credentials: 'same-origin' });
                const data = await response.json();
                
                if (data.success && data.products) {
                    // Create CSV content
                    const periodLabels = {
                        '7d': 'Last 7 Days',
                        '30d': 'Last 30 Days',
                        '90d': 'Last 90 Days',
                        '1y': 'Last Year',
                        'all': 'All Time'
                    };
                    
                    let csv = `Top Products Report - ${periodLabels[period] || period}\n`;
                    csv += `Generated: ${new Date().toLocaleString()}\n`;
                    csv += `Metric: ${metric === 'revenue' ? 'Revenue (₱)' : 'Quantity Sold'}\n\n`;
                    csv += `Rank,Product Name,${metric === 'revenue' ? 'Total Revenue (₱)' : 'Quantity Sold'},Sales Count\n`;
                    
                    data.products.forEach((product, index) => {
                        const value = metric === 'revenue' 
                            ? parseFloat(product.total_revenue || 0).toFixed(2)
                            : product.total_quantity || 0;
                        csv += `${index + 1},"${product.product_name}",${value},${product.sales_count || 0}\n`;
                    });
                    
                    // Download CSV
                    const blob = new Blob([csv], { type: 'text/csv' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `top_products_${period}_${metric}_${new Date().toISOString().split('T')[0]}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    showNotification('Report exported successfully!', 'success');
                } else {
                    showNotification('No data available to export', 'error');
                }
            } catch (error) {
                showNotification(`Export failed: ${error.message}`, 'error');
            }
        });
    }

    // Load initial data
    loadImportsList();
    if (document.getElementById('products-list')) {
        loadProducts();
    }
    if (document.getElementById('topProductsChart')) {
        // Populate Year/Month/Week from available periods
        fetchAvailablePeriods().then(periods => {
            if (periods) populateTopProductsPeriodDropdowns(periods);
            loadTopProducts();
        });
    }
    
    // Load products into forecast dropdown
    const forecastProductSelect = document.getElementById('forecast-product');
    if (forecastProductSelect) {
        fetch('/api/products', { credentials: 'same-origin' })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.products) {
                    data.products.forEach(product => {
                        const option = document.createElement('option');
                        option.value = product.id;
                        option.textContent = product.name;
                        forecastProductSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading products for forecast:', error);
            });
    }
});

// ==================== SYNCHRONIZED DAILY & WEEKLY FORECAST CHARTS ====================

// Populate product selector for synchronized forecasts
async function populateSyncForecastProductSelector() {
    try {
        const response = await fetch('/api/products', { credentials: 'same-origin' });
        if (!response.ok) return;
        
        const data = await response.json();
        const select = document.getElementById('sync-forecast-product-select');
        
        if (!select) return;
        
        // Clear existing options (keep "All Products")
        select.innerHTML = '<option value="">-- All Products (Aggregated) --</option>';
        
        // Add product options
        if (data.success && data.products) {
            data.products.forEach(product => {
                const option = document.createElement('option');
                option.value = product.id;
                option.textContent = `${product.name} (${product.category || 'Uncategorized'})`;
                select.appendChild(option);
            });
        }
        
    } catch (error) {
        console.error('Error populating product selector:', error);
    }
}

// Load both synchronized forecast charts
async function loadSynchronizedForecasts(productId = null) {
    try {
        // Show loading state
        const dailyContainer = document.getElementById('daily-forecast-chart-container');
        const weeklyContainer = document.getElementById('weekly-forecast-chart-container');
        
        if (dailyContainer) {
            dailyContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #9ca3af;">Loading daily forecast...</div>';
        }
        if (weeklyContainer) {
            weeklyContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #9ca3af;">Loading weekly forecast...</div>';
        }
        
        // Reload chart canvases
        setTimeout(() => {
            if (dailyContainer) {
                dailyContainer.innerHTML = '<canvas id="daily-forecast-chart" style="max-height: 350px;"></canvas>';
            }
            if (weeklyContainer) {
                weeklyContainer.innerHTML = '<canvas id="weekly-forecast-chart" style="max-height: 350px;"></canvas>';
            }
            
            // Load both charts
            Promise.all([
                loadDailyForecastChart(productId),
                loadWeeklyForecastChart(productId)
            ]).then(() => {
                // Update accuracy displays
                updateForecastAccuracyDisplays();
            });
        }, 100);
        
    } catch (error) {
        console.error('Error loading synchronized forecasts:', error);
    }
}

// Load daily forecast chart
async function loadDailyForecastChart(productId = null) {
    try {
        // Read year/month/week selectors if present
        const yEl = document.getElementById('forecast-year');
        const mEl = document.getElementById('forecast-month');
        const wEl = document.getElementById('forecast-week');
        const y = yEl ? yEl.value : '';
        const m = mEl ? mEl.value : '';
        const w = wEl ? wEl.value : '';
        const params = new URLSearchParams();
        if (productId) params.set('product_id', productId);
        if (y) params.set('year', y);
        if (m) params.set('month', m);
        if (w) params.set('week', w);
        const url = `/api/forecast/daily${params.toString() ? ('?' + params.toString()) : ''}`;
        const response = await fetch(url, { credentials: 'same-origin' });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }
        
        renderDailyForecastChart(data);
        
    } catch (error) {
        console.error('Error loading daily forecast:', error);
        
        const container = document.getElementById('daily-forecast-chart-container');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #9ca3af;">
                    <p style="font-size: 1.1em; margin-bottom: 10px;"><i class="fas fa-exclamation-triangle"></i> Unable to load daily forecast</p>
                    <p style="font-size: 0.9em;">${error.message}</p>
                    <p style="font-size: 0.85em; margin-top: 10px; color: #6b7280;">Upload sales data to generate forecasts</p>
                </div>
            `;
        }
    }
}

// Render daily forecast chart
function renderDailyForecastChart(data) {
    const ctx = document.getElementById('daily-forecast-chart');
    if (!ctx) return;
    
    // Destroy existing chart to prevent accumulation
    if (window.dailyForecastChart) {
        window.dailyForecastChart.destroy();
        window.dailyForecastChart = null;
    }
    
    // Create a date map for all days (actual + forecast combined)
    const dateMap = new Map();
    
    // Process actual sales data (includes last 4 weeks for context)
    if (data.actual && data.actual.length > 0) {
        data.actual.forEach(day => {
            dateMap.set(day.date, {
                date: day.date,
                day_name: day.day_name,
                actual: day.sales,
                forecast: null,
                confidence_upper: null,
                confidence_lower: null,
                yoy: null
            });
        });
    }
    
    // Process forecast data - add to existing dates or create new entries
    if (data.forecast && data.forecast.length > 0) {
        data.forecast.forEach(day => {
            if (dateMap.has(day.date)) {
                // Date exists (has actual data) - add forecast to compare
                const existing = dateMap.get(day.date);
                existing.forecast = day.sales;
                existing.confidence_upper = day.confidence_upper;
                existing.confidence_lower = day.confidence_lower;
            } else {
                // New date (future) - only forecast
                dateMap.set(day.date, {
                    date: day.date,
                    day_name: day.day_name,
                    actual: null,
                    forecast: day.sales,
                    confidence_upper: day.confidence_upper,
                    confidence_lower: day.confidence_lower,
                    yoy: null
                });
            }
        });
    }
    
    // Process year-over-year data for historical comparison
    if (data.yoy_data && data.yoy_data.length > 0) {
        data.yoy_data.forEach(day => {
            if (dateMap.has(day.date)) {
                dateMap.get(day.date).yoy = day.sales;
            }
        });
    }
    
    // Sort by date and build arrays
    const sortedDates = Array.from(dateMap.keys()).sort();
    const allDays = [];
    const actualData = [];
    const forecastData = [];
    const confidenceUpper = [];
    const confidenceLower = [];
    const yoyData = [];
    const predictionErrors = []; // Track accuracy at each point
    
    sortedDates.forEach(dateStr => {
        const entry = dateMap.get(dateStr);
        const dayDate = new Date(entry.date);
        const dateLabel = dayDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        allDays.push(`${entry.day_name}\n${dateLabel}`);
        actualData.push(entry.actual);
        forecastData.push(entry.forecast);
        confidenceUpper.push(entry.confidence_upper);
        confidenceLower.push(entry.confidence_lower);
        yoyData.push(entry.yoy);
        
        // Calculate prediction error percentage if both actual and forecast exist
        if (entry.actual !== null && entry.forecast !== null && entry.actual > 0) {
            const errorPct = Math.abs((entry.forecast - entry.actual) / entry.actual) * 100;
            predictionErrors.push({ date: dateStr, error: errorPct, actual: entry.actual, forecast: entry.forecast });
        }
    });
    
    // Calculate average prediction error for completed days
    let avgAccuracy = null;
    if (predictionErrors.length > 0) {
        const avgError = predictionErrors.reduce((sum, p) => sum + p.error, 0) / predictionErrors.length;
        avgAccuracy = Math.max(0, 100 - avgError);
    }
    
    window.dailyForecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDays,
            datasets: [
                {
                    label: 'Actual Sales',
                    data: actualData,
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52,211,153,0.15)',
                    borderWidth: 2.5,
                    pointRadius: function(context) {
                        const idx = context.dataIndex;
                        return (actualData[idx] !== null && forecastData[idx] !== null) ? 5 : 0;
                    },
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#34d399',
                    pointBorderColor: '#121212',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    order: 2
                },
                {
                    label: 'Forecasted Sales',
                    data: forecastData,
                    borderColor: '#818cf8',
                    backgroundColor: 'rgba(129,140,248,0.12)',
                    borderWidth: 2.5,
                    borderDash: function(context) {
                        const idx = context.dataIndex;
                        return actualData[idx] === null ? [6, 3] : [];
                    },
                    pointRadius: function(context) {
                        const idx = context.dataIndex;
                        return (actualData[idx] !== null && forecastData[idx] !== null) ? 5 : 3;
                    },
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#818cf8',
                    pointBorderColor: '#121212',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    order: 1
                },
                {
                    label: 'Last Year Same Period',
                    data: yoyData,
                    borderColor: '#fbbf24',
                    backgroundColor: 'rgba(251,191,36,0.08)',
                    borderWidth: 1.5,
                    borderDash: [4, 3],
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointBackgroundColor: '#fbbf24',
                    fill: false,
                    tension: 0.4,
                    order: 3
                },
                {
                    label: 'Confidence Upper',
                    data: confidenceUpper,
                    borderColor: 'rgba(129,140,248,0.25)',
                    backgroundColor: 'rgba(129,140,248,0.07)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1',
                    tension: 0.4,
                    order: 4
                },
                {
                    label: 'Confidence Lower',
                    data: confidenceLower,
                    borderColor: 'rgba(129,140,248,0.25)',
                    backgroundColor: 'rgba(129,140,248,0.07)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4,
                    order: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: `Daily Sales Trend & Forecast${data.history_start ? ' (Historical Context: ' + data.history_start + ')' : ''}`,
                    color: '#f5f5f5',
                    font: { size: 16, weight: '500' },
                    padding: { bottom: 5 }
                },
                subtitle: {
                    display: true,
                    text: [
                        data.accuracy ? `Yesterday's Accuracy: ${data.accuracy.toFixed(1)}%` : 'Model: Linear Regression with seasonal patterns',
                        avgAccuracy !== null ? `Avg Accuracy (past ${predictionErrors.length} days): ${avgAccuracy.toFixed(1)}%` : '',
                        `Period: ${data.week_start} to ${data.week_end}` + (data.yoy_data && data.yoy_data.length > 0 ? ' · Amber = Same period last year' : '')
                    ].filter(t => t),
                    font: { size: 11 },
                    color: data.accuracy ? (data.accuracy >= 85 ? '#34d399' : (data.accuracy >= 70 ? '#818cf8' : '#ef4444')) : '#6b7280',
                    padding: { bottom: 15 }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        filter: (item) => item.text !== 'Confidence Upper' && item.text !== 'Confidence Lower',
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    padding: 12,
                    titleFont: { size: 13, weight: '600' },
                    bodyFont: { size: 12 },
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label.replace('\n', ' ');
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) label += Math.round(context.parsed.y) + ' units';
                            return label;
                        },
                        afterBody: function(tooltipItems) {
                            const idx = tooltipItems[0].dataIndex;
                            const actual = actualData[idx];
                            const forecast = forecastData[idx];
                            const yoy = yoyData[idx];
                            const lines = [];

                            if (actual !== null && forecast !== null && actual > 0) {
                                const accuracy = Math.max(0, 100 - Math.abs((forecast - actual) / actual) * 100);
                                const diff = forecast - actual;
                                lines.push('');
                                lines.push(`Accuracy: ${accuracy.toFixed(1)}%`);
                                lines.push(`Diff: ${diff >= 0 ? '+' : ''}${Math.round(diff)} units`);
                                lines.push(accuracy >= 90 ? 'Excellent' : (accuracy >= 80 ? 'Good' : (accuracy >= 70 ? 'Fair' : 'Needs improvement')));
                            }

                            if (yoy !== null && actual !== null && actual > 0) {
                                const yoyGrowth = ((actual - yoy) / yoy) * 100;
                                lines.push('');
                                lines.push(`vs Last Year: ${yoyGrowth >= 0 ? '+' : ''}${yoyGrowth.toFixed(1)}%`);
                            }
                            
                            // Show confidence range for forecasts
                            if (forecast !== null && confidenceLower[idx] && confidenceUpper[idx]) {
                                lines.push('');
                                lines.push(`Confidence Range: ${Math.round(confidenceLower[idx])} - ${Math.round(confidenceUpper[idx])} units`);
                            }
                            
                            return lines;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Sales Units'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
    
    // Store accuracy for display
    if (data.accuracy !== null) {
        window.dailyForecastAccuracy = data.accuracy;
    }
}

// Load weekly forecast chart
async function loadWeeklyForecastChart(productId = null) {
    try {
        // Read year/month selectors (weekly only needs year and month)
        const yEl = document.getElementById('forecast-year');
        const mEl = document.getElementById('forecast-month');
        const y = yEl ? yEl.value : '';
        const m = mEl ? mEl.value : '';
        const params = new URLSearchParams();
        if (productId) params.set('product_id', productId);
        if (y) params.set('year', y);
        if (m) params.set('month', m);
        const url = `/api/forecast/weekly${params.toString() ? ('?' + params.toString()) : ''}`;
        const response = await fetch(url, { credentials: 'same-origin' });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error');
        }
        
        renderWeeklyForecastChart(data);
        
    } catch (error) {
        console.error('Error loading weekly forecast:', error);
        
        const container = document.getElementById('weekly-forecast-chart-container');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #9ca3af;">
                    <p style="font-size: 1.1em; margin-bottom: 10px;"><i class="fas fa-exclamation-triangle"></i> Unable to load weekly forecast</p>
                    <p style="font-size: 0.9em;">${error.message}</p>
                    <p style="font-size: 0.85em; margin-top: 10px; color: #6b7280;">Upload sales data to generate forecasts</p>
                </div>
            `;
        }
    }
}

// Render weekly forecast chart
function renderWeeklyForecastChart(data) {
    const ctx = document.getElementById('weekly-forecast-chart');
    if (!ctx) return;
    
    // Destroy existing chart to prevent accumulation
    if (window.weeklyForecastChart) {
        window.weeklyForecastChart.destroy();
        window.weeklyForecastChart = null;
    }
    
    // Create a week map for combining actual and forecast
    const weekMap = new Map();
    
    // Process actual sales data
    if (data.actual && data.actual.length > 0) {
        data.actual.forEach(week => {
            weekMap.set(week.week, {
                week: week.week,
                week_start: week.week_start,
                actual: week.sales,
                forecast: null,
                confidence_upper: null,
                confidence_lower: null
            });
        });
    }
    
    // Process forecast data - add to existing weeks or create new entries
    if (data.forecast && data.forecast.length > 0) {
        data.forecast.forEach(week => {
            if (weekMap.has(week.week)) {
                // Week exists (has actual data) - add forecast to compare
                const existing = weekMap.get(week.week);
                existing.forecast = week.sales;
                existing.confidence_upper = week.confidence_upper;
                existing.confidence_lower = week.confidence_lower;
            } else {
                // New week (future) - only forecast
                weekMap.set(week.week, {
                    week: week.week,
                    week_start: week.week_start,
                    actual: null,
                    forecast: week.sales,
                    confidence_upper: week.confidence_upper,
                    confidence_lower: week.confidence_lower
                });
            }
        });
    }
    
    // Sort by week number and build arrays
    const sortedWeeks = Array.from(weekMap.keys()).sort((a, b) => a - b);
    const allWeeks = [];
    const actualData = [];
    const forecastData = [];
    const confidenceUpper = [];
    const confidenceLower = [];
    
    sortedWeeks.forEach(weekNum => {
        const entry = weekMap.get(weekNum);
        allWeeks.push(`Week ${entry.week}`);
        actualData.push(entry.actual);
        forecastData.push(entry.forecast);
        confidenceUpper.push(entry.confidence_upper);
        confidenceLower.push(entry.confidence_lower);
    });
    
    // Calculate prediction errors for weeks with both actual and forecast
    const weeklyPredictionErrors = [];
    sortedWeeks.forEach((weekNum, idx) => {
        if (actualData[idx] !== null && forecastData[idx] !== null && actualData[idx] > 0) {
            const errorPct = Math.abs((forecastData[idx] - actualData[idx]) / actualData[idx]) * 100;
            weeklyPredictionErrors.push({ week: weekNum, error: errorPct, actual: actualData[idx], forecast: forecastData[idx] });
        }
    });
    
    let avgWeeklyAccuracy = null;
    if (weeklyPredictionErrors.length > 0) {
        const avgError = weeklyPredictionErrors.reduce((sum, p) => sum + p.error, 0) / weeklyPredictionErrors.length;
        avgWeeklyAccuracy = Math.max(0, 100 - avgError);
    }
    
    window.weeklyForecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allWeeks,
            datasets: [
                {
                    label: 'Actual Sales',
                    data: actualData,
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52,211,153,0.15)',
                    borderWidth: 2.5,
                    pointRadius: function(context) {
                        const idx = context.dataIndex;
                        return (actualData[idx] !== null && forecastData[idx] !== null) ? 6 : 4;
                    },
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#34d399',
                    pointBorderColor: '#121212',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    order: 1
                },
                {
                    label: 'Forecasted Sales',
                    data: forecastData,
                    borderColor: '#818cf8',
                    backgroundColor: 'rgba(129,140,248,0.12)',
                    borderWidth: 2.5,
                    borderDash: function(context) {
                        const idx = context.dataIndex;
                        return actualData[idx] === null ? [6, 3] : [];
                    },
                    pointRadius: function(context) {
                        const idx = context.dataIndex;
                        return (actualData[idx] !== null && forecastData[idx] !== null) ? 6 : 4;
                    },
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#818cf8',
                    pointBorderColor: '#121212',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    order: 2
                },
                {
                    label: 'Confidence Upper',
                    data: confidenceUpper,
                    borderColor: 'rgba(129,140,248,0.25)',
                    backgroundColor: 'rgba(129,140,248,0.07)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1',
                    tension: 0.4,
                    order: 3
                },
                {
                    label: 'Confidence Lower',
                    data: confidenceLower,
                    borderColor: 'rgba(129,140,248,0.25)',
                    backgroundColor: 'rgba(129,140,248,0.07)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3,
                    order: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: `Weekly Sales Trend & Forecast - ${data.month_name || 'Current Month'}`,
                    font: { size: 16, weight: 'bold' },
                    padding: { bottom: 5 }
                },
                subtitle: {
                    display: true,
                    text: [
                        data.accuracy !== null && data.accuracy !== undefined ? `Last Week's Accuracy: ${data.accuracy.toFixed(1)}%` : 'Model: Aggregated daily forecasts',
                        avgWeeklyAccuracy !== null ? `Avg Accuracy (${weeklyPredictionErrors.length} weeks): ${avgWeeklyAccuracy.toFixed(1)}%` : ''
                    ].filter(t => t),
                    font: { size: 11 },
                    color: data.accuracy ? (data.accuracy >= 85 ? '#34d399' : (data.accuracy >= 70 ? '#818cf8' : '#ef4444')) : '#6b7280',
                    padding: { bottom: 15 }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        filter: (item) => item.text !== 'Confidence Upper' && item.text !== 'Confidence Lower',
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    padding: 12,
                    titleFont: { size: 13, weight: '600' },
                    bodyFont: { size: 12 },
                    callbacks: {
                        title: function(tooltipItems) {
                            return tooltipItems[0].label;
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) label += Math.round(context.parsed.y) + ' units';
                            return label;
                        },
                        afterBody: function(tooltipItems) {
                            const idx = tooltipItems[0].dataIndex;
                            const actual = actualData[idx];
                            const forecast = forecastData[idx];
                            const lines = [];

                            if (actual !== null && forecast !== null && actual > 0) {
                                const accuracy = Math.max(0, 100 - Math.abs((forecast - actual) / actual) * 100);
                                const diff = forecast - actual;
                                lines.push('');
                                lines.push(`Accuracy: ${accuracy.toFixed(1)}%`);
                                lines.push(`Diff: ${diff >= 0 ? '+' : ''}${Math.round(diff)} units`);
                                lines.push(accuracy >= 90 ? 'Excellent' : (accuracy >= 80 ? 'Good' : (accuracy >= 70 ? 'Fair' : 'Needs improvement')));
                            }
                            
                            // Show confidence range for forecasts
                            if (forecast !== null && confidenceLower[idx] && confidenceUpper[idx]) {
                                lines.push('');
                                lines.push(`Confidence Range: ${Math.round(confidenceLower[idx])} - ${Math.round(confidenceUpper[idx])} units`);
                                const margin = ((confidenceUpper[idx] - confidenceLower[idx]) / forecast) * 100;
                                lines.push(`   (±${margin.toFixed(0)}% uncertainty)`);
                            }
                            
                            return lines;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Total Sales Units'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Week of Month'
                    }
                }
            }
        }
    });
    
    // Store accuracy for display
    if (data.accuracy !== null) {
        window.weeklyForecastAccuracy = data.accuracy;
    }
}

// Update accuracy displays
function updateForecastAccuracyDisplays() {
    const dailyEl = document.getElementById('daily-accuracy-display');
    const weeklyEl = document.getElementById('weekly-accuracy-display');
    
    if (dailyEl && window.dailyForecastAccuracy !== undefined) {
        dailyEl.textContent = window.dailyForecastAccuracy + '%';
        dailyEl.style.color = window.dailyForecastAccuracy >= 85 ? '#10b981' : 
                               (window.dailyForecastAccuracy >= 70 ? '#f59e0b' : '#ef4444');
    }
    
    if (weeklyEl && window.weeklyForecastAccuracy !== undefined) {
        weeklyEl.textContent = window.weeklyForecastAccuracy + '%';
        weeklyEl.style.color = window.weeklyForecastAccuracy >= 85 ? '#10b981' : 
                                (window.weeklyForecastAccuracy >= 70 ? '#f59e0b' : '#ef4444');
    }
}

// Initialize synchronized forecasts on page load
document.addEventListener('DOMContentLoaded', function() {
    const syncSelect = document.getElementById('sync-forecast-product-select');
    if (syncSelect) {
        populateSyncForecastProductSelector();
        loadSynchronizedForecasts();
    }
    // Initialize Year/Month/Week selectors for synchronized views
    const yEl = document.getElementById('forecast-year');
    const mEl = document.getElementById('forecast-month');
    const wEl = document.getElementById('forecast-week');
    if (yEl && mEl && wEl) {
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;
        
        // Populate years (current year +/- 2)
        const years = [currentYear - 2, currentYear - 1, currentYear, currentYear + 1, currentYear + 2];
        yEl.innerHTML = '';
        years.forEach(yr => {
            const opt = document.createElement('option');
            opt.value = yr;
            opt.textContent = yr;
            if (yr === currentYear) opt.selected = true;
            yEl.appendChild(opt);
        });
        
        // Populate months with names
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        mEl.innerHTML = '';
        for (let i = 1; i <= 12; i++) {
            const opt = document.createElement('option');
            opt.value = i;
            opt.textContent = monthNames[i - 1];
            if (i === currentMonth) opt.selected = true;
            mEl.appendChild(opt);
        }
        
        // Function to populate weeks based on selected year/month
        function populateWeeks() {
            const year = parseInt(yEl.value);
            const month = parseInt(mEl.value);
            const firstDay = new Date(year, month - 1, 1);
            const lastDay = new Date(year, month, 0);
            const numDays = lastDay.getDate();
            
            // Calculate number of weeks (7-day chunks)
            const numWeeks = Math.ceil(numDays / 7);
            
            wEl.innerHTML = '';
            for (let w = 1; w <= numWeeks; w++) {
                const weekStart = new Date(year, month - 1, (w - 1) * 7 + 1);
                const weekEnd = new Date(year, month - 1, Math.min(w * 7, numDays));
                const opt = document.createElement('option');
                opt.value = w;
                opt.textContent = `Week ${w} (${weekStart.getDate()}-${weekEnd.getDate()})`;
                wEl.appendChild(opt);
            }
            
            // Auto-select current week if we're in the current month
            if (year === currentYear && month === currentMonth) {
                const today = now.getDate();
                const currentWeekNum = Math.floor((today - 1) / 7) + 1;
                wEl.value = currentWeekNum;
            }
        }
        
        // Initial population
        populateWeeks();
        
        // Re-populate weeks when year or month changes
        yEl.addEventListener('change', () => {
            populateWeeks();
            loadSynchronizedForecasts(syncSelect ? syncSelect.value : null);
        });
        mEl.addEventListener('change', () => {
            populateWeeks();
            loadSynchronizedForecasts(syncSelect ? syncSelect.value : null);
        });
        wEl.addEventListener('change', () => loadSynchronizedForecasts(syncSelect ? syncSelect.value : null));
    }
});

// ==================== FORECAST HISTORY MODULE (Removed: consolidated into synchronized views) ====================

// ==================== USER PREFERENCES ====================

// Load user preferences on page load
async function loadUserPreferences() {
    try {
        const response = await fetch('/api/preferences', { credentials: 'same-origin' });
        if (response.ok) {
            const preferences = await response.json();
            
            // Apply preferences to UI
            if (preferences.default_tab) {
                document.getElementById('pref-default-tab').value = preferences.default_tab;
            }
            if (preferences.realtime_updates !== undefined) {
                document.getElementById('pref-realtime-updates').checked = preferences.realtime_updates === 'true';
            }
            if (preferences.items_per_page) {
                document.getElementById('pref-items-per-page').value = preferences.items_per_page;
            }
            if (preferences.email_notifications !== undefined) {
                document.getElementById('pref-email-notifications').checked = preferences.email_notifications === 'true';
            }
            if (preferences.browser_notifications !== undefined) {
                document.getElementById('pref-browser-notifications').checked = preferences.browser_notifications === 'true';
            }
            if (preferences.default_forecast_days) {
                document.getElementById('pref-forecast-days').value = preferences.default_forecast_days;
            }
            if (preferences.auto_refresh !== undefined) {
                document.getElementById('pref-auto-refresh').checked = preferences.auto_refresh === 'true';
            }
            if (preferences.refresh_interval) {
                document.getElementById('pref-refresh-interval').value = preferences.refresh_interval;
            }
            
            // Apply default tab if not navigating via hash
            if (!window.location.hash && preferences.default_tab) {
                const tabButtons = document.querySelectorAll('.tab-btn');
                const tabContents = document.querySelectorAll('.tab-content');
                
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                const targetButton = document.querySelector(`[data-tab="${preferences.default_tab}"]`);
                const targetContent = document.getElementById(`tab-${preferences.default_tab}`);
                
                if (targetButton && targetContent) {
                    targetButton.classList.add('active');
                    targetContent.classList.add('active');
                }
            }
            
            // Setup auto-refresh if enabled
            if (preferences.auto_refresh === 'true' && preferences.refresh_interval) {
                setupAutoRefresh(parseInt(preferences.refresh_interval) * 1000);
            }
        }
    } catch (error) {
        console.error('Error loading preferences:', error);
    }
}

// Save user preferences
async function saveUserPreferences() {
    const saveBtn = document.getElementById('save-settings-btn');
    const messageDiv = document.getElementById('settings-message');
    
    // Disable button and show loading state
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    
    try {
        const preferences = {
            default_tab: document.getElementById('pref-default-tab').value,
            realtime_updates: document.getElementById('pref-realtime-updates').checked.toString(),
            items_per_page: document.getElementById('pref-items-per-page').value,
            email_notifications: document.getElementById('pref-email-notifications').checked.toString(),
            browser_notifications: document.getElementById('pref-browser-notifications').checked.toString(),
            default_forecast_days: document.getElementById('pref-forecast-days').value,
            auto_refresh: document.getElementById('pref-auto-refresh').checked.toString(),
            refresh_interval: document.getElementById('pref-refresh-interval').value
        };
        
        const response = await fetch('/api/preferences', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        });
        
        if (response.ok) {
            messageDiv.textContent = '[OK] Settings saved successfully!';
            messageDiv.style.color = '#10b981';
            messageDiv.style.display = 'block';
            
            // Apply auto-refresh settings immediately
            if (preferences.auto_refresh === 'true') {
                setupAutoRefresh(parseInt(preferences.refresh_interval) * 1000);
            } else {
                clearAutoRefresh();
            }
            
            setTimeout(() => {
                messageDiv.style.display = 'none';
            }, 3000);
        } else {
            const error = await response.json();
            messageDiv.textContent = '[ERROR] ' + (error.error || 'Failed to save settings');
            messageDiv.style.color = '#ef4444';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error saving preferences:', error);
        messageDiv.textContent = '[ERROR] Failed to save settings';
        messageDiv.style.color = '#ef4444';
        messageDiv.style.display = 'block';
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Settings';
    }
}

// Auto-refresh functionality
let autoRefreshInterval = null;

function setupAutoRefresh(intervalMs) {
    clearAutoRefresh();
    autoRefreshInterval = setInterval(() => {
        // Only refresh if on overview tab
        const overviewTab = document.getElementById('tab-overview');
        if (overviewTab && overviewTab.classList.contains('active')) {
            console.log('Auto-refreshing dashboard metrics...');
            if (typeof updateMetrics === 'function') {
                updateMetrics();
            }
        }
    }, intervalMs);
}

function clearAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// ==================== FORECASTING PAGE: PRODUCT SELECTORS ====================

/**
 * Populate product selectors on forecasting page
 * Only includes products that have forecast data
 */
async function populateProductSelectors() {
    try {
        // Fetch products with forecasts
        const response = await fetch('/api/products?with_forecasts=true', { credentials: 'same-origin' });
        if (!response.ok) {
            console.error('Failed to fetch products with forecasts');
            return;
        }
        
        const data = await response.json();
        const products = data.products || [];
        
        console.log(`Found ${products.length} products with forecast data`);
        
        // Populate the sync forecast product selector
        const syncSelector = document.getElementById('sync-forecast-product-select');
        if (syncSelector) {
            // Clear existing options except the "All Products" option
            syncSelector.innerHTML = '<option value="">-- Select a Product --</option>';
            
            if (products.length > 0) {
                // Add products with forecasts
                products.forEach(product => {
                    const option = document.createElement('option');
                    option.value = product.id;
                    option.textContent = `${product.name} (${product.category || 'No Category'})`;
                    syncSelector.appendChild(option);
                });
                
                // Auto-select the first product with forecasts
                syncSelector.value = products[0].id;
                // Load forecasts for this product
                loadSynchronizedForecasts(products[0].id);
            } else {
                syncSelector.innerHTML = '<option value="">-- No products with forecast data --</option>';
                // Show message to user
                const dailyContainer = document.getElementById('daily-forecast-chart-container');
                const weeklyContainer = document.getElementById('weekly-forecast-chart-container');
                
                const message = `
                    <div style="text-align: center; padding: 40px; color: #6b7280;">
                        <p style="font-size: 1.2em; margin-bottom: 10px;"><i class="fas fa-chart-bar"></i> No Forecast Data Available</p>
                        <p style="font-size: 0.95em;">Generate forecasts by uploading sales data or running the forecast generation script.</p>
                    </div>
                `;
                
                if (dailyContainer) dailyContainer.innerHTML = message;
                if (weeklyContainer) weeklyContainer.innerHTML = message;
            }
        }
        
    } catch (error) {
        console.error('Error populating product selectors:', error);
    }
}

// Initialize preferences on page load
if (document.getElementById('save-settings-btn')) {
    loadUserPreferences();
    
    // Attach save button handler
    document.getElementById('save-settings-btn').addEventListener('click', saveUserPreferences);
}

/**
 * Helper to show notifications
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10001;
        font-size: 14px;
        font-weight: 500;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Add CSS animations for notifications
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

