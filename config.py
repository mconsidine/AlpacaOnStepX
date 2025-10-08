"""
Configuration for OnStepX Alpaca Bridge
"""

# Server Configuration
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5555
DEBUG_MODE = False

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
        'enabled': False,  # Placeholder - not yet implemented
        'device_number': 0,
        'name': 'Filter Wheel',
        'unique_id': 'filterwheel-001'
    },
    'focuser': {
        'enabled': False,  # Placeholder - not yet implemented
        'device_number': 0,
        'name': 'Focuser',
        'unique_id': 'focuser-001'
    }
}

# Telescope Configuration
TELESCOPE_CONFIG = {
    'serial_port': '/dev/ttyUSB0',
    'baud_rate': 9600,
    'timeout': 2,
    'auto_detect_port': True
}

# Camera Configuration
CAMERA_CONFIG = {
    'zwo_sdk_path': '/usr/local/lib/libASICamera2.so',
    'default_exposure_min': 0.000032,  # 32 microseconds
    'default_exposure_max': 3600.0,     # 1 hour
    'default_gain': 0,
    'default_offset': 0,
    'image_format': 'uint16'  # 16-bit images
}

# Server Information
SERVER_INFO = {
    'server_name': 'OnStepX Alpaca Bridge',
    'manufacturer': 'Custom',
    'manufacturer_version': '2.0.0',
    'location': 'Raspberry Pi'
}

# Logging
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_to_file': True,
    'log_file': '/var/log/onstepx-alpaca.log'
}

# ASCOM Error Codes
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
