"""
Helper functions for ASCOM Alpaca API
"""

from flask import jsonify, request
from functools import wraps
import config

# Global server transaction counter
_server_transaction_id = 0

def get_next_transaction_id():
    """Get next server transaction ID"""
    global _server_transaction_id
    _server_transaction_id += 1
    return _server_transaction_id

def get_client_transaction_id():
    """Extract client transaction ID from request"""
    if request.method == 'GET':
        return int(request.args.get('ClientTransactionID', 0))
    else:
        data = request.form if request.form else request.json
        if data:
            return int(data.get('ClientTransactionID', 0))
        return 0

def alpaca_response(value=None, client_id=None, error_number=0, error_message=""):
    """
    Format standard ASCOM Alpaca response
    
    Args:
        value: The return value (omitted if None)
        client_id: Client transaction ID (auto-detected if None)
        error_number: ASCOM error code
        error_message: Error description
    """
    if client_id is None:
        client_id = get_client_transaction_id()
    
    response = {
        "ClientTransactionID": int(client_id),
        "ServerTransactionID": get_next_transaction_id(),
        "ErrorNumber": error_number,
        "ErrorMessage": error_message
    }
    
    if value is not None:
        response["Value"] = value
    
    return jsonify(response)

def alpaca_error(error_code, error_message, client_id=None):
    """Create an Alpaca error response"""
    return alpaca_response(
        value=None,
        client_id=client_id,
        error_number=error_code,
        error_message=error_message
    )

def require_connected(device_attr):
    """
    Decorator to check if device is connected before executing endpoint
    
    Args:
        device_attr: Name of the device attribute (e.g., 'telescope', 'camera')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get device from the app context
            from flask import current_app
            device = getattr(current_app, device_attr, None)
            
            if device is None:
                return alpaca_error(
                    config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'],
                    "Device not available"
                )
            
            if not device.is_connected:
                return alpaca_error(
                    config.ASCOM_ERROR_CODES['NOT_CONNECTED'],
                    "Device is not connected"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_form_value(key, default=None, value_type=str):
    """
    Get value from form data or JSON with type conversion
    
    Args:
        key: Parameter name
        default: Default value if not found
        value_type: Type to convert to (str, int, float, bool)
    """
    data = request.form if request.form else request.json
    if not data or key not in data:
        return default
    
    value = data.get(key)
    
    if value_type == bool:
        return str(value).lower() in ('true', '1', 'yes')
    elif value_type in (int, float):
        try:
            return value_type(value)
        except (ValueError, TypeError):
            return default
    else:
        return value

def parse_device_number(device_type, device_number):
    """
    Validate device number against configuration
    
    Returns:
        tuple: (is_valid, error_message)
    """
    for device_key, device_config in config.DEVICES.items():
        if device_key.startswith(device_type):
            if device_config['enabled'] and device_config['device_number'] == device_number:
                return True, None
    
    return False, f"{device_type.capitalize()} device {device_number} not found"

def format_ra_hours(ra_hours):
    """Convert decimal hours to HH:MM:SS format"""
    hours = int(ra_hours)
    minutes = int((ra_hours - hours) * 60)
    seconds = ((ra_hours - hours) * 60 - minutes) * 60
    return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"

def format_dec_degrees(dec_degrees):
    """Convert decimal degrees to sDD:MM:SS format"""
    sign = '+' if dec_degrees >= 0 else '-'
    dec_degrees = abs(dec_degrees)
    degrees = int(dec_degrees)
    minutes = int((dec_degrees - degrees) * 60)
    seconds = ((dec_degrees - degrees) * 60 - minutes) * 60
    return f"{sign}{degrees:02d}:{minutes:02d}:{seconds:05.2f}"

def parse_ra_to_hours(ra_string):
    """Parse RA string (HH:MM:SS) to decimal hours"""
    try:
        parts = ra_string.replace(':', ' ').split()
        hours = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[2]) if len(parts) > 2 else 0
        return hours + minutes/60.0 + seconds/3600.0
    except (ValueError, IndexError):
        return 0.0

def parse_dec_to_degrees(dec_string):
    """Parse Dec string (sDD:MM:SS or sDD*MM:SS) to decimal degrees"""
    try:
        dec_string = dec_string.replace('*', ':')
        sign = -1 if dec_string[0] == '-' else 1
        dec_string = dec_string.lstrip('+-')
        
        parts = dec_string.split(':')
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[2]) if len(parts) > 2 else 0
        
        return sign * (degrees + minutes/60.0 + seconds/3600.0)
    except (ValueError, IndexError):
        return 0.0

def validate_range(value, min_val, max_val, param_name):
    """
    Validate value is within range
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if value < min_val or value > max_val:
        return False, f"{param_name} must be between {min_val} and {max_val}"
    return True, None

def clamp(value, min_val, max_val):
    """Clamp value to range"""
    return max(min_val, min(max_val, value))
