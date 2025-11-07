// Modal functionality
function openModal(modalId) {
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

function closeModal(modalId) {
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
    
    // Fetch forecast accuracy metrics
    fetchForecastAccuracy();
    
    // Fetch weekly forecast preview
    fetchWeeklyForecast();
    
    // Fetch enhanced restock alerts
    fetchEnhancedRestockAlerts();
});

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
    
    // Set active button
    const periodButtons = document.querySelectorAll('.period-btn');
    periodButtons.forEach(btn => {
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
    
    // Fetch and update dashboard
    fetch(url)
        .then(response => response.json())
        .then(data => {
            updateDashboardWithData(data);
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            showToast('Failed to load dashboard data', 'error');
        });
}

// Fetch and display forecast accuracy metrics
async function fetchForecastAccuracy() {
    try {
        const response = await fetch('/api/forecast-accuracy?days_back=7');
        
        if (!response.ok) {
            throw new Error('Failed to fetch accuracy data');
        }
        
        const data = await response.json();
        
        // Update 1-day accuracy
        updateAccuracyMetric('1d', data['1_day']);
        
        // Update 7-day accuracy
        updateAccuracyMetric('7d', data['7_day']);
        
        // Update 30-day accuracy
        updateAccuracyMetric('30d', data['30_day']);
        
        // Calculate overall average accuracy for summary card
        const accuracyValues = [data['1_day'], data['7_day'], data['30_day']].filter(v => v !== null && v !== undefined);
        
        const summaryAccuracyEl = document.getElementById('accuracy');
        if (summaryAccuracyEl && accuracyValues.length > 0) {
            const avgAccuracy = accuracyValues.reduce((sum, val) => sum + val, 0) / accuracyValues.length;
            summaryAccuracyEl.textContent = avgAccuracy.toFixed(1) + '%';
        } else if (summaryAccuracyEl) {
            summaryAccuracyEl.textContent = '--';
        }
        
    } catch (error) {
        console.error('Error fetching forecast accuracy:', error);
        
        // Update summary card to show no data
        const summaryAccuracyEl = document.getElementById('accuracy');
        if (summaryAccuracyEl) {
            summaryAccuracyEl.textContent = 'No data';
        }
        
        // Show "No data yet" if insufficient history
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
        statusEl.textContent = '✓ Excellent';
        statusEl.style.color = '#4ade80'; // Green
    } else if (accuracy >= 70) {
        statusEl.textContent = '⚠ Good';
        statusEl.style.color = '#fbbf24'; // Yellow
    } else {
        statusEl.textContent = '✗ Needs Improvement';
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
        const response = await fetch('/api/weekly-forecast');
        
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
                            📊 <strong>No Forecast Data Available Yet</strong>
                        </div>
                        <div style="color: #9ca3af; font-size: 0.95em; line-height: 1.6;">
                            <p style="margin: 10px 0;">To generate 7-day demand forecasts, the system needs sales history:</p>
                            <ol style="text-align: left; display: inline-block; margin: 15px auto;">
                                <li style="margin: 8px 0;">📁 Upload sales CSV data (at least 7 days of history)</li>
                                <li style="margin: 8px 0;">🤖 System automatically trains the forecasting model</li>
                                <li style="margin: 8px 0;">📈 Forecasts appear here after processing</li>
                            </ol>
                            <p style="margin-top: 15px; color: #6b7280;">
                                💡 <em>Tip: More historical data = More accurate forecasts</em>
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
        'CRITICAL': `<span style="background: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">🔴 CRITICAL</span>`,
        'LOW': `<span style="background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">🟡 LOW</span>`,
        'OK': `<span style="background: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">🟢 OK</span>`
    };
    
    return badges[status] || `<span style="color: ${color};">${status}</span>`;
}

// Fetch Enhanced Restock Alerts (Multi-Horizon Forecast-Based)
async function fetchEnhancedRestockAlerts() {
    console.log('Fetching enhanced restock alerts...');
    
    try {
        const response = await fetch('/api/enhanced-restock-alerts');
        
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
                <div style="font-size: 2em; margin-bottom: 10px;">✅</div>
                <div style="font-size: 1.1em; font-weight: 600; margin-bottom: 5px;">No Restock Alerts</div>
                <div style="font-size: 0.9em;">All products have sufficient stock based on forecasts</div>
            </div>
        `;
        return;
    }
    
    // Create header with summary
    let html = `
        <div style="display: flex; gap: 10px; margin-bottom: 15px; padding: 10px; background: #f9fafb; border-radius: 6px;">
            <span style="flex: 1; text-align: center; padding: 8px; background: #fee2e2; color: #991b1b; border-radius: 4px; font-size: 0.85em; font-weight: 600;">
                🔴 Critical: ${summary.critical_count || 0}
            </span>
            <span style="flex: 1; text-align: center; padding: 8px; background: #fef3c7; color: #92400e; border-radius: 4px; font-size: 0.85em; font-weight: 600;">
                🟡 High: ${summary.high_count || 0}
            </span>
            <span style="flex: 1; text-align: center; padding: 8px; background: #d1fae5; color: #065f46; border-radius: 4px; font-size: 0.85em; font-weight: 600;">
                🟢 Medium: ${summary.medium_count || 0}
            </span>
        </div>
    `;
    
    // Render each alert
    alerts.forEach(alert => {
        const urgencyIcon = {
            'CRITICAL': '🔴',
            'HIGH': '🟡',
            'MEDIUM': '🟢'
        }[alert.urgency] || '⚠️';
        
        const bgColor = {
            'CRITICAL': '#fef2f2',
            'HIGH': '#fffbeb',
            'MEDIUM': '#f0fdf4'
        }[alert.urgency] || '#f9fafb';
        
        const borderColor = alert.urgency_color;
        
        html += `
            <div class="alert-item" style="padding: 12px; margin-bottom: 10px; background: ${bgColor}; border-left: 4px solid ${borderColor}; border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <div>
                        <div style="font-weight: 600; font-size: 1em; margin-bottom: 4px;">
                            ${urgencyIcon} ${alert.urgency} - ${alert.product_name}
                        </div>
                        <div style="font-size: 0.85em; color: #6b7280;">
                            ${alert.category} • Current Stock: <strong>${alert.current_stock}</strong>
                        </div>
                    </div>
                    <span style="background: ${borderColor}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; white-space: nowrap;">
                        ${alert.urgency}
                    </span>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 10px 0; padding: 10px; background: white; border-radius: 4px;">
                    <div style="text-align: center;">
                        <div style="font-size: 0.75em; color: #9ca3af; margin-bottom: 2px;">1-Day Forecast</div>
                        <div style="font-weight: 600; color: #374151;">${alert.forecasts['1_day'] || 'N/A'}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.75em; color: #9ca3af; margin-bottom: 2px;">7-Day Forecast</div>
                        <div style="font-weight: 600; color: #374151;">${alert.forecasts['7_day'] || 'N/A'}</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.75em; color: #9ca3af; margin-bottom: 2px;">30-Day Forecast</div>
                        <div style="font-weight: 600; color: #374151;">${alert.forecasts['30_day'] || 'N/A'}</div>
                    </div>
                </div>
                
                <div style="padding: 8px; background: white; border-radius: 4px; margin-bottom: 8px;">
                    <div style="font-size: 0.85em; color: #374151;">
                        <strong>Shortage:</strong> ${alert.shortage} units • 
                        <strong>Horizons Affected:</strong> ${alert.horizons_affected.join(', ')}
                    </div>
                    ${alert.note ? `<div style="font-size: 0.8em; color: #6b7280; margin-top: 4px; font-style: italic;">ℹ️ ${alert.note}</div>` : ''}
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: #e0e7ff; border-radius: 4px;">
                    <div style="font-size: 0.9em; font-weight: 600; color: #3730a3;">
                        📦 Recommended Order: <span style="font-size: 1.1em;">${alert.recommended_order_qty}</span> units
                    </div>
                    <button class="btn btn-primary" style="padding: 6px 14px; font-size: 0.85em; background: #4f46e5; border: none; cursor: pointer;" onclick="quickRestock(${alert.product_id}, ${alert.recommended_order_qty})">
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
        fetch(`/api/product/${productId}`)
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
    // Update metric cards
    const totalUnits = document.getElementById('total-units');
    const totalRevenue = document.getElementById('total-revenue');
    const totalInventoryValue = document.getElementById('total-inventory-value');
    const accuracy = document.getElementById('accuracy');
    const alertsCount = document.getElementById('alerts-count');
    const fakeBanner = document.getElementById('fake-data-banner');
    const fakeCount = document.getElementById('fake-data-count');

    if (totalUnits) totalUnits.textContent = (data.total_units_sold || 0).toLocaleString('en-PH') + ' units';
    if (totalRevenue) totalRevenue.textContent = formatPHP(data.total_revenue);
    if (totalInventoryValue) totalInventoryValue.textContent = formatPHP(data.total_inventory_value || 0);
    if (accuracy) accuracy.textContent = data.accuracy;
    if (alertsCount) alertsCount.textContent = data.alerts;

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
        data.current_month_revenue, data.year_ago_revenue, data.year_revenue_change, true);
    updateComparisonCard('current-year-units', 'last-year-units', 'year-units-change',
        data.current_month_units, data.year_ago_units, data.year_units_change, false);

    // Update charts with monthly daily revenue data
    if (window.trendChart && data.monthly_daily_labels && data.monthly_daily_sales) {
        const labels = data.monthly_daily_labels || [];
        const actualData = data.monthly_daily_sales || [];
        const forecastData = data.monthly_daily_forecasts || [];
        
        window.trendChart.data.labels = labels;
        window.trendChart.data.datasets[0].data = actualData;
        window.trendChart.data.datasets[1].data = forecastData;
        window.trendChart.update();
    }

    if (window.monthlyChart && data.monthly_labels && data.monthly_data) {
        window.monthlyChart.data.labels = data.monthly_labels;
        window.monthlyChart.data.datasets[0].data = data.monthly_data;
        window.monthlyChart.update();
    }
}

// ==================== FORECAST VISUALIZATION FUNCTIONS ====================

// Populate product selector for forecast visualization
async function populateForecastProductSelector() {
    try {
        const res = await fetch('/api/products');
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
        const res = await fetch(`/api/forecast-visualization?product_id=${productId}&days_back=30`);
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
        const res = await fetch('/api/model-comparison');
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


function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        document.body.style.paddingRight = getScrollbarWidth() + 'px'; // Prevent layout shift
        modal.setAttribute('aria-hidden', 'false');
        // Focus management for accessibility
        const firstInput = modal.querySelector('input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            document.body.style.overflow = 'auto'; // Restore scrolling
            document.body.style.paddingRight = '0px'; // Restore layout
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

function switchModal(targetModalId) {
    // Close all modals first
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.classList.remove('show');
        setTimeout(() => {
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
        }, 300);
    });
    // Open target modal
    setTimeout(() => {
        openModal(targetModalId);
    }, 350);
}

async function handleLogin(event) {
    event.preventDefault();

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

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showMessage('login-messages', 'Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = result.redirect || '/dashboard';
            }, 1000);
        } else {
            showMessage('login-messages', result.message || 'Login failed', 'error');
        }
    } catch (error) {
        showMessage('login-messages', 'Network error. Please try again.', 'error');
    } finally {
        // Reset button state
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

async function handleRegister(event) {
    event.preventDefault();

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
        const response = await fetch('/register', {
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

// Store chart instances globally so we can update them
let trendChart = null;
let monthlyChart = null;

// Expose charts to window for updates
window.trendChart = null;
window.monthlyChart = null;

// Chart initialization function
function initializeCharts() {
    // Initialize empty charts - will be populated with real data from API
    const labels = [];
    const emptyData = [];

    // Trend Chart (Line Chart) - Monthly Actual vs Forecasted Revenue
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        trendChart = new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Actual Revenue',
                    data: emptyData,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }, {
                    label: 'Forecasted Revenue',
                    data: emptyData,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                            text: 'Monthly Revenue: Actual vs Forecast',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + formatPHP(context.parsed.y);
                                }
                            }
                    }
                },
                scales: {
                    y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return formatPHP(value);
                                }
                            },
                            title: {
                                display: true,
                                text: 'Revenue (₱)'
                            }
                    }
                }
            }
        });
        window.trendChart = trendChart; // Expose to window
    }

    // Monthly Comparison Chart (Bar Chart)
    const monthlyCtx = document.getElementById('monthlyChart');
    if (monthlyCtx) {
        monthlyChart = new Chart(monthlyCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Monthly Sales',
                    data: [],
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                            text: 'Monthly Sales Performance (Last 6 Months)',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
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
                    y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return formatPHP(value);
                                }
                            },
                            title: {
                                display: true,
                                text: 'Revenue (₱)'
                            }
                    }
                }
            }
        });
        window.monthlyChart = monthlyChart; // Expose to window
    }

    // Fetch and update metrics dynamically from database (skip if live WS metrics enabled)
    if (!window.USE_WEBSOCKET_METRICS) {
    fetch('/api/metrics')
        .then(response => response.json())
        .then(data => {
            // Update metric cards
            const totalUnits = document.getElementById('total-units');
            const totalRevenue = document.getElementById('total-revenue');
                const totalInventoryValue = document.getElementById('total-inventory-value');
            const accuracy = document.getElementById('accuracy');
            const alertsCount = document.getElementById('alerts-count');

            if (totalUnits) totalUnits.textContent = data.total_units_sold + ' units';
                if (totalRevenue) totalRevenue.textContent = formatPHP(data.total_revenue);
                if (totalInventoryValue) totalInventoryValue.textContent = formatPHP(data.total_inventory_value || 0);
            if (accuracy) {
                // Format accuracy as percentage
                const accuracyValue = typeof data.accuracy === 'number' ? data.accuracy : parseFloat(data.accuracy) || 0;
                accuracy.textContent = accuracyValue.toFixed(1) + '%';
            }
            if (alertsCount) alertsCount.textContent = data.alerts;

            // Update change indicators (only show if data exists)
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

            // Update Month-over-Month Comparison Cards (NEW)
            updateComparisonCard(
                'current-month-revenue',
                'last-month-revenue',
                'month-revenue-change',
                data.current_month_revenue,
                data.last_month_revenue,
                data.month_revenue_change,
                true  // is currency
            );

            updateComparisonCard(
                'current-month-units',
                'last-month-units',
                'month-units-change',
                data.current_month_units,
                data.last_month_units,
                data.month_units_change,
                false  // not currency
            );

            // Update Year-over-Year Comparison Cards (NEW)
            updateComparisonCard(
                'current-year-revenue',
                'last-year-revenue',
                'year-revenue-change',
                data.current_month_revenue,  // Current month this year
                data.year_ago_revenue,
                data.year_revenue_change,
                true  // is currency
            );

            updateComparisonCard(
                'current-year-units',
                'last-year-units',
                'year-units-change',
                data.current_month_units,  // Current month this year
                data.year_ago_units,
                data.year_units_change,
                false  // not currency
            );

            // Update Trend Chart with monthly daily revenue (actual vs forecast)
            if (trendChart) {
                const labels = data.monthly_daily_labels || [];
                const actualData = data.monthly_daily_sales || [];
                const forecastData = data.monthly_daily_forecasts || [];
                
                trendChart.data.labels = labels;
                trendChart.data.datasets[0].data = actualData;
                trendChart.data.datasets[1].data = forecastData;
                trendChart.update();
            }

            // Update Monthly Chart with actual data
            if (monthlyChart) {
                monthlyChart.data.labels = data.monthly_labels;
                monthlyChart.data.datasets[0].data = data.monthly_data;
                monthlyChart.update();
            }
        })
        .catch(error => {
            console.log('Could not load metrics:', error);
            // Fallback to 0 if API fails
            const totalUnits = document.getElementById('total-units');
            const totalRevenue = document.getElementById('total-revenue');
            const accuracy = document.getElementById('accuracy');
            const alertsCount = document.getElementById('alerts-count');
            if (totalUnits) totalUnits.textContent = '0 units';
            if (totalRevenue) totalRevenue.textContent = '₱0.00';
            if (accuracy) accuracy.textContent = '0%';
            if (alertsCount) alertsCount.textContent = '0';
        });
    }

    // Fetch and display restock alerts (skip if live WS alerts enabled)
    if (!window.USE_WEBSOCKET_ALERTS) {
    fetch('/api/restock-alerts')
        .then(response => response.json())
        .then(alerts => {
            const alertsList = document.getElementById('alerts-list');
            if (!alertsList) return;
            
            if (alerts.length === 0) {
                alertsList.innerHTML = '<div class="no-alerts">No restock alerts at this time. All inventory levels are adequate.</div>';
            } else {
                alertsList.innerHTML = alerts.map(alert => {
                    const alertClass = alert.status === 'CRITICAL' ? 'critical' : 'warning';
                    return `
                        <div class="alert ${alertClass}">
                            <strong>${alert.product_name || 'Product ' + alert.product_id}:</strong> 
                            ${alert.recommendation}
                            <br><small>Current stock: ${alert.current_stock} units | 7-day demand: ${alert.demand_7d} units</small>
                        </div>
                    `;
                }).join('');
            }
        })
        .catch(error => {
            console.log('Could not load alerts:', error);
            const alertsList = document.getElementById('alerts-list');
            if (alertsList) {
                alertsList.innerHTML = '<div class="no-alerts">Unable to load alerts. Please try again later.</div>';
            }
        });
    }

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

    // Update metric cards
    const totalActual = document.getElementById('total-actual');
    const accuracy = document.getElementById('accuracy');
    const turnover = document.getElementById('turnover-rate');
    const alertsCount = document.getElementById('alerts-count');

    if (totalActual) totalActual.textContent = forecastResult.total_sales;
    if (accuracy) accuracy.textContent = forecastResult.accuracy + '%';
    if (turnover) turnover.textContent = forecastResult.turnover.toFixed(2);
    if (alertsCount) alertsCount.textContent = forecastResult.alerts_count;
}

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
            // include selected data type (supports unified_sales)
            const dataTypeSelect = document.getElementById('data-type-select');
            const dataType = dataTypeSelect ? dataTypeSelect.value : 'sales';
            formData.append('data_type', dataType);

            try {
                importStatus.innerHTML = '<div style="color: #007bff; padding: 10px; background: #e7f3ff; border-radius: 4px;"><strong>⏳ Processing CSV...</strong><br/><small>This may take several minutes if generating forecasts. Please wait...</small></div>';
                uploadCsvBtn.disabled = true;
                uploadCsvBtn.textContent = 'Processing...';
                
                const response = await fetch('/api/upload-csv', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    const rowsProcessed = (result.summary && result.summary.processed) || result.rows_processed || 0;
                    importStatus.innerHTML = `
                        <div style="color: #28a745; padding: 10px; background: #d4edda; border-radius: 4px;">
                            <strong>✓ Success!</strong><br/>
                            <small>${result.message}<br/>Rows processed: ${rowsProcessed}</small>
                        </div>
                    `;
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
                    importStatus.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px;"><strong>Error:</strong> ${result.error}</div>`;
                }
            } catch (error) {
                importStatus.innerHTML = `<div style="color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px;"><strong>Upload failed:</strong> ${error.message}</div>`;
            } finally {
                uploadCsvBtn.disabled = false;
                uploadCsvBtn.textContent = 'Import CSV';
            }
        });
    }

    // Download all data
    const downloadAllDataBtn = document.getElementById('download-all-data-btn');
    if (downloadAllDataBtn) {
        downloadAllDataBtn.addEventListener('click', async function() {
            try {
                const response = await fetch('/api/download-all-data');
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
    function loadImportsList() {
        const importsList = document.getElementById('imports-list');
        if (!importsList) return;

        fetch('/api/list-imports')
            .then(response => response.json())
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
                                    ✅ New: ${imp.rows_processed} | 
                                    ${imp.rows_skipped > 0 ? `⏭️ Skipped: ${imp.rows_skipped} | ` : ''}
                                    ${imp.rows_failed > 0 ? `❌ Failed: ${imp.rows_failed} | ` : ''}
                                    User: ${imp.username}
                                </small>
                                ${imp.validation_errors ? `<br/><small style="color: #856404; background: #fff3cd; padding: 2px 6px; border-radius: 3px;">⚠️ ${imp.validation_errors}</small>` : ''}
                                ${imp.error_message ? `<br/><small style="color: #dc3545;">❌ ${imp.error_message.substring(0, 100)}</small>` : ''}
                            </div>
                        `;
                    }).join('');
                } else {
                    importsList.innerHTML = '<p style="padding: 20px; color: #999; text-align: center;">No previous imports</p>';
                }
            })
            .catch(error => {
                importsList.innerHTML = `<p style="padding: 20px; color: #dc3545; text-align: center;">Error loading imports: ${error.message}</p>`;
            });
    }

    // Upload CSV with data type selection
    const uploadBtn = document.getElementById('upload-csv-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', async function() {
            const fileInput = document.getElementById('csv-import');
            const dataTypeSelect = document.getElementById('data-type-select');
            const statusDiv = document.getElementById('import-status');
            
            if (!fileInput.files[0]) {
                statusDiv.innerHTML = '<p style="color: #dc3545;">Please select a CSV file</p>';
                return;
            }

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('data_type', dataTypeSelect.value);

            statusDiv.innerHTML = '<p style="color: #007bff;">Uploading and validating...</p>';

            try {
                const response = await fetch('/api/upload-csv', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    const summary = result.summary;
                    statusDiv.innerHTML = `
                        <div style="color: #28a745; background: #d4edda; padding: 12px; border-radius: 4px; border: 1px solid #c3e6cb;">
                            <strong>✓ Import Successful</strong><br/>
                            <div style="margin-top: 8px; font-size: 13px; line-height: 1.6;">
                                📊 Total Rows: <strong>${summary.total_rows}</strong><br/>
                                ✅ New Records: <strong>${summary.new_records}</strong><br/>
                                ${summary.duplicates_found > 0 ? `⏭️ Duplicates Skipped: <strong>${summary.duplicates_found}</strong><br/>` : ''}
                                ${summary.failed > 0 ? `❌ Failed: <strong>${summary.failed}</strong>` : ''}
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
                    statusDiv.innerHTML = `
                        <div style="color: #dc3545; background: #f8d7da; padding: 12px; border-radius: 4px; border: 1px solid #f5c6cb;">
                            <strong>❌ Import Failed</strong><br/>
                            <div style="margin-top: 8px; font-size: 13px;">
                                ${result.error}
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                statusDiv.innerHTML = `
                    <div style="color: #dc3545; background: #f8d7da; padding: 12px; border-radius: 4px; border: 1px solid #f5c6cb;">
                        <strong>❌ Upload Error</strong><br/>
                        ${error.message}
                    </div>
                `;
            }
        });
    }

    // Product Management Functions
    let topProductsChart = null;
    let currentEditingProductId = null;
    let currentDeletingProduct = null;
    let currentInventoryProduct = null;

    // Load products with enhanced UI
    function loadProducts(searchTerm = '') {
        const productsList = document.getElementById('products-list');
        if (!productsList) return;

        const url = searchTerm ? `/api/products?search=${encodeURIComponent(searchTerm)}` : '/api/products';

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.products && data.products.length > 0) {
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
                                            <span>${product.category || 'Uncategorized'}</span>
                                            <span>₱${parseFloat(product.unit_cost || 0).toFixed(2)}</span>
                                            <span class="stock-badge ${stockClass}">${stock} units</span>
                                        </div>
                                    </div>
                                    <div class="product-actions">
                                        <button class="btn-stock" onclick="openInventoryModal(${product.id}, '${product.name.replace(/'/g, "\\'")}', ${stock})">
                                            Update
                                        </button>
                                        <button class="btn-edit" onclick="openEditProductModal(${product.id})">
                                            Edit
                                        </button>
                                        <button class="btn-delete" onclick="openDeleteModal(${product.id}, '${product.name.replace(/'/g, "\\'")}')">
                                            Delete
                                        </button>
                                    </div>
                            </div>
                        `;
                    }).join('');
                } else {
                    productsList.innerHTML = `
                        <div style="text-align: center; padding: 60px 20px;">
                            <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">📦</div>
                            <p style="color: #9ca3af; font-size: 1rem; margin: 0;">No products found</p>
                            <p style="color: #d1d5db; font-size: 0.875rem; margin-top: 8px;">Try adjusting your search or add a new product</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                productsList.innerHTML = `
                    <div style="text-align: center; padding: 60px 20px;">
                        <div style="font-size: 3rem; margin-bottom: 16px; opacity: 0.3;">⚠️</div>
                        <p style="color: #ef4444; font-size: 1rem; margin: 0;">Error loading products</p>
                        <p style="color: #fca5a5; font-size: 0.875rem; margin-top: 8px;">${error.message}</p>
                    </div>
                `;
            });
    }

    // Product Modal Functions
    window.openProductModal = function(productId = null) {
        const modal = document.getElementById('product-modal');
        const title = document.getElementById('product-modal-title');
        const form = document.getElementById('product-modal-form');
        const stockGroup = document.getElementById('modal-stock-group');
        
        // Reset form
        form.reset();
        document.getElementById('modal-product-id').value = '';
        
        if (productId) {
            title.textContent = 'Edit Product';
            stockGroup.style.display = 'none'; // Hide stock field when editing
            currentEditingProductId = productId;
            
            // Load product data
            fetch(`/api/products/${productId}`)
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
            stockGroup.style.display = 'block';
            currentEditingProductId = null;
        }
        
        modal.classList.add('show');
    };

    window.openEditProductModal = function(productId) {
        openProductModal(productId);
    };

    window.closeProductModal = function() {
        const modal = document.getElementById('product-modal');
        modal.classList.remove('show');
        currentEditingProductId = null;
    };

    // Product Modal Form Submission
    const productModalForm = document.getElementById('product-modal-form');
    if (productModalForm) {
        productModalForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const productId = document.getElementById('modal-product-id').value;
            const productData = {
                name: document.getElementById('modal-product-name').value,
                category: document.getElementById('modal-product-category').value,
                unit_cost: document.getElementById('modal-product-cost').value
            };

            // Only include stock for new products
            if (!productId) {
                productData.current_stock = document.getElementById('modal-product-stock').value;
            }

            try {
                const url = productId ? `/api/products/${productId}` : '/api/products';
                const method = productId ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productData)
                });

                const result = await response.json();

                if (result.success) {
                    closeProductModal();
                    loadProducts();
                    showNotification(result.message, 'success');
                } else {
                    showNotification(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showNotification(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Delete Modal Functions
    window.openDeleteModal = function(productId, productName) {
        const modal = document.getElementById('delete-modal');
        const message = document.getElementById('delete-modal-message');
        const warning = document.getElementById('delete-modal-warning');
        
        currentDeletingProduct = { id: productId, name: productName };
        
        message.textContent = `Are you sure you want to delete "${productName}"?`;
        
        // Check if product has sales records
        fetch(`/api/products/${productId}/sales-count`)
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    warning.style.display = 'block';
                    warning.innerHTML = `⚠️ This product has ${data.count} sales record(s). Deleting it may affect your reports.`;
                } else {
                    warning.style.display = 'none';
                }
            })
            .catch(() => {
                warning.style.display = 'none';
            });
        
        modal.classList.add('show');
    };

    window.closeDeleteModal = function() {
        const modal = document.getElementById('delete-modal');
        modal.classList.remove('show');
        currentDeletingProduct = null;
    };

    // Confirm Delete Button
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async function() {
            if (!currentDeletingProduct) return;

            try {
                const response = await fetch(`/api/products/${currentDeletingProduct.id}`, {
                    method: 'DELETE'
                });

                const result = await response.json();

                if (result.success) {
                    closeDeleteModal();
                    loadProducts();
                    showNotification(result.message, 'success');
                } else {
                    showNotification(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showNotification(`Error: ${error.message}`, 'error');
            }
        });
    }

    // Inventory Adjustment Modal Functions
    window.openInventoryModal = function(productId, productName, currentStock) {
        const modal = document.getElementById('inventory-modal');
        const form = document.getElementById('inventory-modal-form');
        
        form.reset();
        document.getElementById('inventory-product-id').value = productId;
        document.getElementById('inventory-product-name').textContent = productName;
        document.getElementById('inventory-current-stock').textContent = currentStock;
        
        currentInventoryProduct = { id: productId, name: productName, stock: currentStock };
        
        modal.classList.add('show');
    };

    window.closeInventoryModal = function() {
        const modal = document.getElementById('inventory-modal');
        modal.classList.remove('show');
        currentInventoryProduct = null;
    };

    // Inventory Modal Form Submission
    const inventoryModalForm = document.getElementById('inventory-modal-form');
    if (inventoryModalForm) {
        inventoryModalForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Updating...';
            }
            
            try {
                const productId = document.getElementById('inventory-product-id').value;
                const quantity = parseInt(document.getElementById('inventory-quantity').value);
                const operation = document.getElementById('inventory-operation').value;
                const reason = document.getElementById('inventory-reason').value;

                const response = await fetch('/api/inventory/adjust', {
                    method: 'POST',
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
                    showNotification(`Stock updated successfully! New stock: ${result.product.current_stock} units`, 'success');
                } else {
                    showNotification(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showNotification(`Error: ${error.message}`, 'error');
            } finally {
                const submitBtn = inventoryModalForm.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Adjust Inventory';
                }
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
        fetch(`/api/products/${productId}`)
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

    // Top Products Chart
    function loadTopProducts() {
        const canvas = document.getElementById('topProductsChart');
        if (!canvas) return;

        const period = document.getElementById('ranking-period')?.value || '7d';
        const metric = document.getElementById('ranking-metric')?.value || 'revenue';

        fetch(`/api/top-products?limit=10&period=${period}&metric=${metric}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.products) {
                    const labels = data.products.map(p => p.product_name);
                    const values = data.products.map(p => metric === 'revenue' ? p.total_revenue : p.total_quantity);

                    if (topProductsChart) {
                        topProductsChart.destroy();
                    }

                    // Period labels for better display
                    const periodLabels = {
                        '7d': 'Last 7 Days',
                        '30d': 'Last 30 Days',
                        '90d': 'Last 90 Days',
                        '1y': 'Last Year',
                        'all': 'All Time'
                    };

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
                                    text: `Top 10 Products by ${metric === 'revenue' ? 'Revenue' : 'Quantity'} - ${periodLabels[period] || period}`,
                                    font: {
                                        size: 16,
                                        weight: 'bold'
                                    },
                                    color: '#1f2937'
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
                }
            })
            .catch(error => {
                console.error('Error loading top products:', error);
            });
    }

    // Event listeners for ranking controls
    const rankingPeriod = document.getElementById('ranking-period');
    const rankingMetric = document.getElementById('ranking-metric');
    
    if (rankingPeriod) {
        rankingPeriod.addEventListener('change', loadTopProducts);
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
                const response = await fetch(`/api/top-products?limit=10&period=${period}&metric=${metric}`);
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
        loadTopProducts();
    }
    
    // Load products into forecast dropdown
    const forecastProductSelect = document.getElementById('forecast-product');
    if (forecastProductSelect) {
        fetch('/api/products')
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
        const response = await fetch('/api/products');
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
        const response = await fetch(url);
        
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
                    <p style="font-size: 1.1em; margin-bottom: 10px;">⚠️ Unable to load daily forecast</p>
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
                confidence_lower: null
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
                    confidence_lower: day.confidence_lower
                });
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
    
    sortedDates.forEach(dateStr => {
        const entry = dateMap.get(dateStr);
        const dayDate = new Date(entry.date);
        const dateLabel = dayDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        allDays.push(`${entry.day_name}\n${dateLabel}`);
        actualData.push(entry.actual);
        forecastData.push(entry.forecast);
        confidenceUpper.push(entry.confidence_upper);
        confidenceLower.push(entry.confidence_lower);
    });
    
    window.dailyForecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDays,
            datasets: [
                {
                    label: 'Actual Sales',
                    data: actualData,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointBackgroundColor: '#28a745',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Forecasted Sales',
                    data: forecastData,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointBackgroundColor: '#007bff',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Confidence Upper',
                    data: confidenceUpper,
                    borderColor: 'rgba(0, 123, 255, 0.3)',
                    backgroundColor: 'rgba(0, 123, 255, 0.05)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1',
                    tension: 0.4
                },
                {
                    label: 'Confidence Lower',
                    data: confidenceLower,
                    borderColor: 'rgba(0, 123, 255, 0.3)',
                    backgroundColor: 'rgba(0, 123, 255, 0.05)',
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
                    display: true,
                    text: `Daily Sales & Forecast (${data.history_start ? data.history_start + ' to ' : ''}${data.week_end})`,
                    font: { size: 16, weight: 'bold' },
                    padding: { bottom: 20 }
                },
                subtitle: {
                    display: true,
                    text: data.accuracy ? `Yesterday's Forecast Accuracy: ${data.accuracy}% • Current Week: ${data.week_start} to ${data.week_end}` : `Current Week: ${data.week_start} to ${data.week_end} • Enhanced model with seasonal patterns`,
                    font: { size: 12 },
                    color: data.accuracy && data.accuracy >= 85 ? '#28a745' : (data.accuracy && data.accuracy >= 70 ? '#007bff' : '#6b7280'),
                    padding: { bottom: 10 }
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
        const response = await fetch(url);
        
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
                    <p style="font-size: 1.1em; margin-bottom: 10px;">⚠️ Unable to load weekly forecast</p>
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
    
    window.weeklyForecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allWeeks,
            datasets: [
                {
                    label: 'Actual Sales',
                    data: actualData,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointBackgroundColor: '#28a745',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Forecasted Sales',
                    data: forecastData,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointBackgroundColor: '#007bff',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Confidence Upper',
                    data: confidenceUpper,
                    borderColor: 'rgba(0, 123, 255, 0.3)',
                    backgroundColor: 'rgba(0, 123, 255, 0.05)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1',
                    tension: 0.4
                },
                {
                    label: 'Confidence Lower',
                    data: confidenceLower,
                    borderColor: 'rgba(0, 123, 255, 0.3)',
                    backgroundColor: 'rgba(0, 123, 255, 0.05)',
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
                    display: true,
                    text: `Weekly Forecast (${data.month_name})`,
                    font: { size: 16, weight: 'bold' },
                    padding: { bottom: 20 }
                },
                subtitle: {
                    display: data.accuracy !== null,
                    text: data.accuracy ? `Last Week's Forecast Accuracy: ${data.accuracy}%` : '',
                    font: { size: 12 },
                    color: data.accuracy >= 85 ? '#28a745' : (data.accuracy >= 70 ? '#007bff' : '#ef4444'),
                    padding: { bottom: 10 }
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
                        },
                        afterLabel: function(context) {
                            // Show confidence interval for forecasts
                            if (context.dataset.label === 'Forecasted Sales' && confidenceUpper[context.dataIndex]) {
                                const lower = Math.round(confidenceLower[context.dataIndex]);
                                const upper = Math.round(confidenceUpper[context.dataIndex]);
                                return `Range: ${lower} - ${upper} units`;
                            }
                            return '';
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
        const response = await fetch('/api/preferences');
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
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        });
        
        if (response.ok) {
            messageDiv.textContent = '✓ Settings saved successfully!';
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
            messageDiv.textContent = '✗ Error: ' + (error.error || 'Failed to save settings');
            messageDiv.style.color = '#ef4444';
            messageDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error saving preferences:', error);
        messageDiv.textContent = '✗ Error: Failed to save settings';
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
        const response = await fetch('/api/products?with_forecasts=true');
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
                        <p style="font-size: 1.2em; margin-bottom: 10px;">📊 No Forecast Data Available</p>
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

