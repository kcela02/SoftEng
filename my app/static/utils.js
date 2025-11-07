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
