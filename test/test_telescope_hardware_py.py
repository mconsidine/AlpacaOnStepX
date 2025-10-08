#!/usr/bin/env python3
"""Test telescope with actual OnStepX hardware"""

import sys
sys.path.insert(0, '..')

from telescope import OnStepXMount
import time

def test_connection():
    print("Testing telescope connection...")
    
    mount = OnStepXMount()
    success = mount.connect()
    
    if not success:
        print("✗ Connection failed - check USB connection")
        print("  Tips:")
        print("  - Check cable is connected")
        print("  - Try: ls -l /dev/ttyUSB* /dev/ttyACM*")
        print("  - Check permissions: groups | grep dialout")
        return False
    
    print(f"✓ Connected on {mount.port}")
    print(f"  Site Latitude: {mount.site_latitude:.4f}°")
    print(f"  Site Longitude: {mount.site_longitude:.4f}°")
    
    return mount

def test_position_reading(mount):
    print("\nTesting position reading...")
    
    ra = mount.get_ra()
    dec = mount.get_dec()
    alt = mount.get_altitude()
    az = mount.get_azimuth()
    lst = mount.get_sidereal_time()
    pier = mount.get_pier_side()
    
    print(f"  RA:  {ra:.4f} hours")
    print(f"  Dec: {dec:.4f} degrees")
    print(f"  Alt: {alt:.4f} degrees")
    print(f"  Az:  {az:.4f} degrees")
    print(f"  LST: {lst:.4f} hours")
    print(f"  Pier Side: {pier}")
    
    # Basic validation
    assert 0 <= ra < 24, f"RA should be 0-24 hours, got {ra}"
    assert -90 <= dec <= 90, f"Dec should be -90 to 90, got {dec}"
    assert 0 <= alt <= 90, f"Alt should be 0-90, got {alt}"
    assert 0 <= az < 360, f"Az should be 0-360, got {az}"
    
    print("✓ Position reading OK\n")

def test_tracking(mount):
    print("Testing tracking...")
    
    is_tracking = mount.get_tracking()
    print(f"  Current tracking: {is_tracking}")
    
    # Toggle tracking off
    print("  Turning tracking OFF...")
    mount.set_tracking(False)
    time.sleep(1)
    new_tracking = mount.get_tracking()
    print(f"  Tracking now: {new_tracking}")
    
    # Toggle tracking on
    print("  Turning tracking ON...")
    mount.set_tracking(True)
    time.sleep(1)
    final_tracking = mount.get_tracking()
    print(f"  Tracking now: {final_tracking}")
    
    # Restore original state
    mount.set_tracking(is_tracking)
    
    print("✓ Tracking control OK\n")

def test_park_status(mount):
    print("Testing park status...")
    
    at_park = mount.get_at_park()
    at_home = mount.get_at_home()
    
    print(f"  At park: {at_park}")
    print(f"  At home: {at_home}")
    
    if at_park:
        print("  ⚠️  Mount is parked - some operations may be limited")
    
    print("✓ Park status OK\n")

def test_site_configuration(mount):
    print("Testing site configuration...")
    
    # Read current values
    lat = mount.site_latitude
    lon = mount.site_longitude
    elev = mount.site_elevation
    
    print(f"  Latitude:  {lat:.4f}°")
    print(f"  Longitude: {lon:.4f}°")
    print(f"  Elevation: {elev:.1f}m")
    
    print("✓ Site configuration OK\n")

def test_tracking_rates(mount):
    print("Testing tracking rates...")
    
    current_rate = mount.tracking_rate
    print(f"  Current rate: {current_rate} (0=Sidereal, 1=Lunar, 2=Solar)")
    
    # Try setting different rates
    from telescope import DriveRates
    
    print("  Testing Sidereal rate...")
    mount.set_tracking_rate(DriveRates.driveSidereal)
    time.sleep(0.5)
    
    print("  Testing Lunar rate...")
    mount.set_tracking_rate(DriveRates.driveLunar)
    time.sleep(0.5)
    
    print("  Testing Solar rate...")
    mount.set_tracking_rate(DriveRates.driveSolar)
    time.sleep(0.5)
    
    # Restore original
    mount.set_tracking_rate(current_rate)
    
    print("✓ Tracking rates OK\n")

if __name__ == '__main__':
    print("=" * 60)
    print("TELESCOPE HARDWARE TEST")
    print("=" * 60)
    print("⚠️  Ensure OnStepX is connected via USB")
    print("⚠️  Mount should be powered and initialized")
    print("=" * 60 + "\n")
    
    mount = test_connection()
    if mount:
        try:
            test_position_reading(mount)
            test_tracking(mount)
            test_park_status(mount)
            test_site_configuration(mount)
            test_tracking_rates(mount)
            
            print("=" * 60)
            print("✅ ALL TELESCOPE HARDWARE TESTS PASSED")
            print("=" * 60 + "\n")
        except AssertionError as e:
            print(f"\n✗ Assertion failed: {e}\n")
        except Exception as e:
            print(f"\n✗ Test error: {e}\n")
        finally:
            mount.disconnect()
            print("Disconnected from mount\n")
    else:
        print("✗ Tests aborted - no connection\n")
        sys.exit(1)
