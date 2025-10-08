#!/usr/bin/env python3
"""Test configuration module"""

import sys
sys.path.insert(0, '..')

import config

def test_config():
    print("Testing configuration...")
    
    # Test server config
    assert config.SERVER_PORT == 5555
    assert config.SERVER_HOST == '0.0.0.0'
    print("✓ Server config OK")
    
    # Test device config
    assert 'telescope' in config.DEVICES
    assert 'camera_zwo' in config.DEVICES
    assert 'camera_touptek' in config.DEVICES
    print("✓ Device config OK")
    
    # Test error codes
    assert config.ASCOM_ERROR_CODES['NOT_CONNECTED'] == 1031
    assert config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'] == 1024
    assert config.ASCOM_ERROR_CODES['INVALID_VALUE'] == 1025
    print("✓ Error codes OK")
    
    # Test telescope config
    assert 'serial_port' in config.TELESCOPE_CONFIG
    assert 'baud_rate' in config.TELESCOPE_CONFIG
    print("✓ Telescope config OK")
    
    # Test camera config
    assert 'zwo_sdk_path' in config.CAMERA_CONFIG
    print("✓ Camera config OK")
    
    print("\n✅ Configuration module PASSED\n")

if __name__ == '__main__':
    test_config()
