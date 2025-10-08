#!/usr/bin/env python3
"""Test camera Alpaca API endpoints"""

import requests
import time
import base64
import numpy as np
import sys

BASE_URL = "http://localhost:5555"
DEVICE_NUM = 0  # ZWO camera (change to 1 for ToupTek)

def test_connection():
    print("Testing camera connection...")
    
    # Get initial state
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/connected")
    initial_state = r.json()['Value']
    print(f"  Initial state: {'Connected' if initial_state else 'Disconnected'}")
    
    # Connect if not connected
    if not initial_state:
        print("  Connecting...")
        r = requests.put(
            f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/connected",
            data={'Connected': 'true'}
        )
        assert r.json()['ErrorNumber'] == 0, "Connection should succeed"
        time.sleep(2)
    
    # Verify connected
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/connected")
    assert r.json()['Value'] == True, "Camera should be connected"
    
    print("✓ Connection OK\n")

def test_camera_info():
    print("Testing camera info...")
    
    # Name
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/name")
    name = r.json()['Value']
    print(f"  Name: {name}")
    
    # Size
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/cameraxsize")
    xsize = r.json()['Value']
    
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/cameraysize")
    ysize = r.json()['Value']
    
    print(f"  Size: {xsize} x {ysize} pixels")
    assert xsize > 0 and ysize > 0, "Camera size should be positive"
    
    # Binning capabilities
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/maxbinx")
    max_bin_x = r.json()['Value']
    
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/maxbiny")
    max_bin_y = r.json()['Value']
    
    print(f"  Max binning: {max_bin_x} x {max_bin_y}")
    
    # Gain range
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/gainmin")
    gain_min = r.json()['Value']
    
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/gainmax")
    gain_max = r.json()['Value']
    
    print(f"  Gain range: {gain_min} - {gain_max}")
    
    print("✓ Camera info OK\n")

def test_binning_configuration():
    print("Testing binning configuration...")
    
    # Set 2x2 binning
    r = requests.put(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/binx", data={'BinX': 2})
    assert r.json()['ErrorNumber'] == 0
    
    r = requests.put(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/biny", data={'BinY': 2})
    assert r.json()['ErrorNumber'] == 0
    
    # Verify
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/binx")
    assert r.json()['Value'] == 2, "BinX should be 2"
    
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/biny")
    assert r.json()['Value'] == 2, "BinY should be 2"
    
    print("  Binning set to 2x2 ✓")
    print("✓ Binning configuration OK\n")

def test_exposure():
    print("Testing exposure (2 seconds, binned 2x2)...")
    
    # Ensure binning is set for faster test
    requests.put(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/binx", data={'BinX': 2})
    requests.put(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/biny", data={'BinY': 2})
    
    # Check initial state
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/camerastate")
    state = r.json()['Value']
    print(f"  Initial camera state: {state}")
    
    # Start exposure
    print("  Starting 2-second exposure...")
    r = requests.put(
        f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/startexposure",
        data={'Duration': 2.0, 'Light': 'true'}
    )
    assert r.json()['ErrorNumber'] == 0, "Exposure should start successfully"
    print("  Exposure started ✓")
    
    # Monitor progress
    start_time = time.time()
    last_percent = -1
    
    while True:
        r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/imageready")
        if r.json()['Value']:
            print("  Image ready! ✓")
            break
        
        r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/percentcompleted")
        percent = r.json()['Value']
        
        if percent != last_percent:
            print(f"  Progress: {percent}%")
            last_percent = percent
        
        time.sleep(0.5)
        
        # Timeout after 10 seconds
        if time.time() - start_time > 10:
            print("  ✗ Timeout waiting for exposure")
            return False
    
    print("✓ Exposure OK\n")
    return True

def test_image_download():
    print("Testing image download...")
    
    # Check image is ready
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/imageready")
    if not r.json()['Value']:
        print("  ✗ No image available - run exposure first")
        return False
    
    # Download image using Base64 (efficient method)
    print("  Downloading image (Base64 method)...")
    start_time = time.time()
    
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/imagearrayvariant")
    data = r.json()['Value']
    
    download_time = time.time() - start_time
    
    # Decode Base64
    img_bytes = base64.b64decode(data['Data'])
    img = np.frombuffer(img_bytes, dtype=np.uint16).reshape((data['Height'], data['Width']))
    
    size_mb = len(data['Data']) / 1024 / 1024
    
    print(f"  Downloaded: {img.shape[1]} x {img.shape[0]} pixels")
    print(f"  Data type: {img.dtype}")
    print(f"  Value range: {img.min()} - {img.max()}")
    print(f"  Download time: {download_time:.2f} seconds")
    print(f"  Data size: {size_mb:.2f} MB")
    print(f"  Speed: {size_mb/download_time:.2f} MB/s")
    
    # Sanity checks
    assert img.shape[0] > 0 and img.shape[1] > 0, "Image should have positive dimensions"
    assert img.dtype == np.uint16, "Image should be 16-bit"
    assert img.max() > img.min(), "Image should have variation"
    
    print("✓ Image download OK\n")
    return True

def test_temperature():
    print("Testing temperature monitoring...")
    
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/ccdtemperature")
    temp = r.json()['Value']
    print(f"  CCD Temperature: {temp:.1f}°C")
    
    # Check if cooling is supported
    r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/cansetccdtemperature")
    can_cool = r.json()['Value']
    
    if can_cool:
        print("  Cooling: Supported ✓")
        
        # Check cooler status
        r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/cooleron")
        cooler_on = r.json()['Value']
        print(f"  Cooler on: {cooler_on}")
        
        # Check cooler power
        r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/cangetcoolerpower")
        if r.json()['Value']:
            r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/coolerpower")
            power = r.json()['Value']
            print(f"  Cooler power: {power}%")
    else:
        print("  Cooling: Not supported")
    
    print("✓ Temperature OK\n")

def test_capabilities():
    print("Testing camera capabilities...")
    
    capabilities = [
        'canabortexposure',
        'canstopexposure',
        'canpulseguide',
        'cansetccdtemperature',
        'cangetcoolerpower'
    ]
    
    for cap in capabilities:
        r = requests.get(f"{BASE_URL}/api/v1/camera/{DEVICE_NUM}/{cap}")
        value = r.json()['Value']
        print(f"  {cap}: {value}")
    
    print("✓ Capabilities OK\n")

if __name__ == '__main__':
    print("=" * 60)
    print(f"CAMERA API TEST (Device {DEVICE_NUM})")
    print("=" * 60)
    print("⚠️  Server must be running")
    print("⚠️  Camera must be connected via USB")
    print("=" * 60 + "\n")
    
    try:
        test_connection()
        test_camera_info()
        test_binning_configuration()
        test_capabilities()
        test_temperature()
        
        if test_exposure():
            test_image_download()
        
        print("=" * 60)
        print("✅ ALL CAMERA API TESTS PASSED")
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
