"""
Configuration for OnStepX Alpaca Bridge
Complete configuration with all devices
"""

# Server Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5555
DEBUG_MODE = False

# Discovery Configuration
DISCOVERY_ENABLED = True
ENABLE_DISCOVERY = DISCOVERY_ENABLED
DISCOVERY_PORT = 32227

# Device Configuration
DEVICES = {
    'telescope': {
        'enabled': True,
        'device_number': 0,
        'name': 'OnStepX Mount',
        'unique_id': 'onstepx-telescope-001'
    },
    'camera_zwo': {
        'enabled': True,
        'device_number': 0,
        'name': 'ZWO ASI Camera',
        'unique_id': 'zwo-camera-001',
        'camera_id': 0  # Index if multiple ZWO cameras
    },
    'camera_touptek': {
        'enabled': True,
        'device_number': 1,
        'name': 'ToupTek Camera',
        'unique_id': 'touptek-camera-001',
        'camera_id': 0  # Index if multiple ToupTek cameras
    },
    'filterwheel': {
        'enabled': True,              # ← ENABLE THIS!
        'device_number': 0,
        'name': 'ZWO Filter Wheel',
        'unique_id': 'filterwheel-001'
    },
    'focuser': {
        'enabled': True,              # ← ENABLE THIS!
        'device_number': 0,
        'name': 'ZWO Focuser',
        'unique_id': 'focuser-001'
    }
}

# ============================================================================
# TELESCOPE CONFIGURATION
# ============================================================================

TELESCOPE_CONFIG = {
    # Connection Type: 'network' or 'serial'
    'connection_type': 'network',
    
    # NETWORK CONNECTION (WiFi/Ethernet)
    'network': {
        #'host': '192.168.1.100',  # ← SET YOUR ONSTEPX IP
        #'port': 9999,
        'host': '192.168.5.140',  # ← TEST w Seestar to see if Alpaca id'd
        'port': 32323,
    },
    
    # SERIAL CONNECTION (USB)
    'serial': {
        'port': '/dev/ttyUSB0',
        'baudrate': 9600,
        'timeout': 2,
        'auto_detect_port': True
    }
}

# ============================================================================
# CAMERA CONFIGURATION
# ============================================================================

CAMERA_CONFIG = {
    'zwo_sdk_path': '/usr/local/lib/libASICamera2.so',
    'default_exposure_min': 0.000032,  # 32 microseconds
    'default_exposure_max': 3600.0,     # 1 hour
    'default_gain': 0,
    'default_offset': 0,
    'image_format': 'uint16'  # 16-bit images
}

# ============================================================================
# FILTER WHEEL CONFIGURATION
# ============================================================================

FILTERWHEEL_CONFIG = {
    # Mode: 'auto' (try ZWO, fall back to mock), 'zwo', or 'mock'
    'mode': 'auto',
    
    # ZWO EFW Settings
    'zwo': {
        'wheel_id': 0,              # Index if multiple filter wheels
        'sdk_path': '/usr/local/lib/libEFWFilter.so',
    },
    
    # Mock Mode Settings (for testing without hardware)
    'mock': {
        'slot_count': 8,            # Number of filter positions
    },
    
    # Filter Names (customize for your filters)
    'filter_names': [
        "Red",
        "Green",
        "Blue",
        "Luminance",
        "H-Alpha",
        "OIII",
        "SII",
        "Clear"
    ],
    
    # Focus Offsets (microns, adjust for each filter)
    # These compensate for different filter thicknesses
    'focus_offsets': [
        0,      # Red
        0,      # Green
        0,      # Blue
        0,      # Luminance
        50,     # H-Alpha (typically thicker)
        30,     # OIII
        40,     # SII
        0       # Clear
    ]
}

# ============================================================================
# FOCUSER CONFIGURATION
# ============================================================================

FOCUSER_CONFIG = {
    # Mode: 'auto' (try ZWO, fall back to mock), 'zwo', or 'mock'
    'mode': 'auto',
    
    # ZWO EAF Settings
    'zwo': {
        'focuser_id': 0,            # Index if multiple focusers
        'sdk_path': '/usr/local/lib/libEAFFocuser.so',
    },
    
    # Mock Mode Settings (for testing without hardware)
    'mock': {
        'max_position': 100000,     # Maximum steps
        'step_size': 1.0,           # Microns per step
    },
    
    # Focuser Settings
    'max_increment': 10000,         # Maximum single move
    'backlash_compensation': 0,     # Steps (0 = disabled)
    'temperature_compensation': {
        'enabled': False,           # Auto temperature compensation
        'coefficient': 0.0,         # Steps per degree C
    }
}

# ============================================================================
# SERVER INFORMATION
# ============================================================================

SERVER_INFO = {
    'server_name': 'OnStepX Alpaca Bridge',
    'manufacturer': 'Custom',
    'manufacturer_version': '2.0.0',
    'location': 'Raspberry Pi'
}

# ============================================================================
# LOGGING
# ============================================================================

LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_to_file': True,
    'log_file': '/var/log/onstepx-alpaca.log'
}

# ============================================================================
# ASCOM ERROR CODES
# ============================================================================

ASCOM_ERROR_CODES = {
    'OK': 0,
    'NOT_IMPLEMENTED': 1024,
    'INVALID_VALUE': 1025,
    'VALUE_NOT_SET': 1026,
    'NOT_CONNECTED': 1031,
    'INVALID_WHILE_PARKED': 1032,
    'INVALID_WHILE_SLAVED': 1033,
    'INVALID_OPERATION': 1034,
    'UNSPECIFIED_ERROR': 1035
}

# ============================================================================
# CONFIGURATION NOTES
# ============================================================================
#
# QUICK START:
# 1. Set your OnStepX IP address in TELESCOPE_CONFIG
# 2. Enable devices you have in DEVICES section
# 3. For ZWO hardware:
#    - Install ZWO SDK libraries
#    - Set mode='auto' (will detect hardware automatically)
# 4. For testing without hardware:
#    - Set mode='mock' for filterwheel/focuser
#
# SWITCHING BETWEEN REAL AND MOCK:
#   FILTERWHEEL_CONFIG['mode'] = 'auto'  # Try ZWO, use mock if not found
#   FILTERWHEEL_CONFIG['mode'] = 'zwo'   # ZWO only (error if not found)
#   FILTERWHEEL_CONFIG['mode'] = 'mock'  # Always use mock
#
# Same pattern for FOCUSER_CONFIG['mode']
#
# ============================================================================
