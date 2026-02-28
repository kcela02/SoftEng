/**
 * Philippine Peso Currency Formatting Utilities
 * Predictive Sales & Restocking Dashboard
 */

/**
 * Format value as Philippine Peso currency
 * @param {number} value - Numeric value
 * @returns {string} Formatted currency (₱1,234.56)
 */
function formatPHP(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '₱0.00';
    }
    
    return '₱' + parseFloat(value).toLocaleString('en-PH', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Format large PHP values with K/M suffixes
 * @param {number} value - Numeric value
 * @returns {string} Formatted currency (₱1.2M, ₱45.3K)
 */
function formatPHPShort(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '₱0';
    }
    
    const absValue = Math.abs(value);
    
    if (absValue >= 1000000) {
        return '₱' + (value / 1000000).toFixed(1) + 'M';
    } else if (absValue >= 1000) {
        return '₱' + (value / 1000).toFixed(1) + 'K';
    } else {
        return '₱' + value.toFixed(2);
    }
}

/**
 * Format number without currency symbol
 * @param {number} value - Numeric value
 * @returns {string} Formatted number (1,234.56)
 */
function formatNumber(value, decimals = 0) {
    if (value === null || value === undefined || isNaN(value)) {
        return '0';
    }
    
    return parseFloat(value).toLocaleString('en-PH', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Parse PHP currency string to number
 * @param {string} phpString - Currency string (₱1,234.56)
 * @returns {number} Numeric value
 */
function parsePHP(phpString) {
    if (!phpString) return 0;
    
    // Remove ₱ symbol and commas
    const cleaned = phpString.replace(/[₱,]/g, '');
    const value = parseFloat(cleaned);
    
    return isNaN(value) ? 0 : value;
}

/**
 * Security: Redirect URL Validation
 * Prevents open redirect vulnerabilities
 */

// Allowlist of safe redirect paths
const ALLOWED_REDIRECT_PATHS = [
    '/',
    '/dashboard',
    '/forecasting',
    '/products',
    '/reports',
    '/settings',
    '/websocket-test',
    '/login',
    '/logout',
    '/register'
];

/**
 * Check if a URL is safe for redirect
 * @param {string} url - The URL to validate
 * @returns {boolean} True if the URL is safe
 */
function isSafeRedirectUrl(url) {
    if (!url) return false;
    
    try {
        // Parse the URL
        const urlObj = new URL(url, window.location.origin);
        
        // Check if it's the same origin
        if (urlObj.origin !== window.location.origin) {
            return false;
        }
        
        // Strip trailing slash and check against allowlist
        const path = urlObj.pathname.replace(/\/$/, '') || '/';
        return ALLOWED_REDIRECT_PATHS.includes(path);
    } catch (e) {
        // If URL parsing fails, check if it's a relative path
        if (url.startsWith('/')) {
            const path = url.split('?')[0].split('#')[0].replace(/\/$/, '') || '/';
            return ALLOWED_REDIRECT_PATHS.includes(path);
        }
        return false;
    }
}

/**
 * Get a safe redirect URL with fallback
 * @param {string} url - The requested redirect URL
 * @param {string} fallback - Fallback URL (default: '/dashboard')
 * @returns {string} A safe URL to redirect to
 */
function getSafeRedirectUrl(url, fallback = '/dashboard') {
    if (url && isSafeRedirectUrl(url)) {
        return url;
    }
    return fallback;
}

/**
 * Safely redirect to a URL after validation
 * @param {string} url - The URL to redirect to
 * @param {string} fallback - Fallback URL if validation fails
 */
function safeRedirect(url, fallback = '/dashboard') {
    const safeUrl = getSafeRedirectUrl(url, fallback);
    window.location.href = safeUrl;
}
