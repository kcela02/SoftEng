# utils/redirect_validator.py
"""
Redirect URL validator to prevent open redirect vulnerabilities.
Only allows redirects to pre-approved internal routes.
"""

from urllib.parse import urlparse, urljoin
from flask import request, url_for


# Allowlist of safe redirect endpoints (route names)
ALLOWED_ENDPOINTS = {
    'main.home',
    'main.dashboard',
    'main.forecasting',
    'main.products_page',
    'main.reports',
    'main.settings',
    'main.websocket_test',
    'auth.login',
    'auth.logout',
    'auth.register',
}

# Allowlist of safe redirect paths (for direct path checking)
ALLOWED_PATHS = {
    '/',
    '/dashboard',
    '/forecasting',
    '/products',
    '/reports',
    '/settings',
    '/websocket-test',
    '/login',
    '/logout',
    '/register',
}


def is_safe_url(target):
    """
    Check if a target URL is safe for redirect.
    
    Args:
        target: The redirect target URL to validate
        
    Returns:
        bool: True if the URL is safe, False otherwise
    """
    if not target:
        return False
    
    # Parse the target URL
    try:
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
    except:
        # If URL parsing fails, consider it unsafe
        return False
    
    # Check that the scheme and netloc match (same origin)
    # and that the path is in the allowlist
    is_same_origin = (test_url.scheme in ('http', 'https') and 
                      ref_url.netloc == test_url.netloc)
    
    if not is_same_origin:
        return False
    
    # Check if the path is in the allowlist
    path = test_url.path.rstrip('/')
    if not path:
        path = '/'
    
    return path in ALLOWED_PATHS


def get_safe_redirect_url(target, fallback='main.dashboard'):
    """
    Get a safe redirect URL from a target, with fallback to a safe default.
    
    Args:
        target: The requested redirect target
        fallback: The fallback endpoint name if target is unsafe (default: 'main.dashboard')
        
    Returns:
        str: A safe URL to redirect to
    """
    if target and is_safe_url(target):
        return target
    
    # Return the fallback URL
    try:
        return url_for(fallback)
    except:
        # If url_for fails, return root
        return '/'


def validate_endpoint(endpoint_name):
    """
    Check if an endpoint name is in the allowlist.
    
    Args:
        endpoint_name: The Flask endpoint name (e.g., 'main.dashboard')
        
    Returns:
        bool: True if the endpoint is allowed, False otherwise
    """
    return endpoint_name in ALLOWED_ENDPOINTS


def get_safe_endpoint_url(endpoint_name, fallback='main.dashboard', **values):
    """
    Get a URL for an endpoint only if it's in the allowlist.
    
    Args:
        endpoint_name: The Flask endpoint name
        fallback: The fallback endpoint if the requested one is not allowed
        **values: Additional arguments to pass to url_for
        
    Returns:
        str: A safe URL to redirect to
    """
    if validate_endpoint(endpoint_name):
        try:
            return url_for(endpoint_name, **values)
        except:
            pass
    
    # Use fallback
    try:
        return url_for(fallback, **values)
    except:
        return '/'
