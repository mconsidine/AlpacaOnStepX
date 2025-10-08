#!/usr/bin/env python3
"""Test Alpaca management API"""

import requests
import json
import sys

BASE_URL = "http://localhost:5555"

def test_api_versions():
    print("Testing /management/apiversions...")
    
    r = requests.get(f"{BASE_URL}/management/apiversions")
    data = r.json()
    
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert 'Value' in data, "Response should have 'Value' field"
    assert 1 in data['Value'], "Should support API version 1"
    assert 'ClientTransactionID' in data, "Should have ClientTransactionID"
    assert 'ServerTransactionID' in data, "Should have ServerTransactionID"
    
    print(f"  API versions: {data['Value']}")
    print("✓ API versions OK\n")

def test_description():
    print("Testing /management/v1/description...")
    
    r = requests.get(f"{BASE_URL}/management/v1/description")
    data = r.json()
    
    assert r.status_code == 200
    assert 'Value' in data
    assert 'ServerName' in data['Value'], "Should have ServerName"
    assert 'Manufacturer' in data['Value'], "Should have Manufacturer"
    assert 'ManufacturerVersion' in data['Value'], "Should have ManufacturerVersion"
    
    print(f"  Server: {data['Value']['ServerName']}")
    print(f"  Manufacturer: {data['Value']['Manufacturer']}")
    print(f"  Version: {data['Value']['ManufacturerVersion']}")
    print("✓ Description OK\n")

def test_configured_devices():
    print("Testing /management/v1/configureddevices...")
    
    r = requests.get(f"{BASE_URL}/management/v1/configureddevices")
    data = r.json()
    
    assert r.status_code == 200
    assert 'Value' in data
    assert isinstance(data['Value'], list), "Value should be a list"
    
    devices = data['Value']
    print(f"  Devices found: {len(devices)}")
    
    for device in devices:
        assert 'DeviceName' in device, "Device should have DeviceName"
        assert 'DeviceType' in device, "Device should have DeviceType"
        assert 'DeviceNumber' in device, "Device should have DeviceNumber"
        assert 'UniqueID' in device, "Device should have UniqueID"
        
        print(f"    - {device['DeviceType']} #{device['DeviceNumber']}: {device['DeviceName']}")
        print(f"      ID: {device['UniqueID']}")
    
    print("✓ Configured devices OK\n")
    return devices

def test_error_response_format():
    print("Testing error response format...")
    
    # Try to access non-existent device
    r = requests.get(f"{BASE_URL}/api/v1/telescope/99/connected")
    data = r.json()
    
    # Even errors should have proper format
    assert 'ClientTransactionID' in data
    assert 'ServerTransactionID' in data
    assert 'ErrorNumber' in data
    assert 'ErrorMessage' in data
    
    if data['ErrorNumber'] != 0:
        print(f"  Error format correct: {data['ErrorMessage']}")
    
    print("✓ Error response format OK\n")

if __name__ == '__main__':
    print("=" * 60)
    print("MANAGEMENT API TEST")
    print("=" * 60)
    print("⚠️  Server must be running:")
    print("    Terminal 1: cd ~/onstepx-alpaca && python3 main.py")
    print("    Terminal 2: cd ~/onstepx-alpaca/tests && python3 test_api_management.py")
    print("=" * 60 + "\n")
    
    try:
        test_api_versions()
        test_description()
        devices = test_configured_devices()
        test_error_response_format()
        
        print("=" * 60)
        print("✅ ALL MANAGEMENT API TESTS PASSED")
        print("=" * 60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server")
        print("  Start server: cd ~/onstepx-alpaca && python3 main.py\n")
        sys.exit(1)
    except AssertionError as e:
        print(f"✗ Test failed: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
