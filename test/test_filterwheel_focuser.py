#!/usr/bin/env python3
"""
Test script for Filter Wheel and Focuser
Tests both mock and real hardware modes
"""

import sys
import time

from filterwheel import create_filterwheel, ZWO_EFW_AVAILABLE
from focuser import create_focuser, ZWO_EAF_AVAILABLE

def test_filterwheel(mode='auto'):
    """Test filter wheel functionality"""
    print("=" * 60)
    print(f"Testing Filter Wheel ({mode} mode)")
    print("=" * 60)
    
    try:
        # Create filter wheel
        print(f"\nCreating filter wheel in '{mode}' mode...")
        fw = create_filterwheel(mode=mode, slot_count=8)
        
        # Connect
        print("\nConnecting...")
        if not fw.connect():
            print("✗ Failed to connect")
            return False
        
        print("\n--- Filter Wheel Properties ---")
        print(f"Slot count: {fw.slot_count}")
        print(f"Current position: {fw.get_position()}")
        print(f"Filter name: {fw.get_filter_name(fw.get_position())}")
        
        print("\n--- All Filters ---")
        for i in range(fw.slot_count):
            print(f"  Position {i}: {fw.get_filter_name(i)} (offset: {fw.get_focus_offset(i)} µm)")
        
        # Test movements
        print("\n--- Testing Movement ---")
        test_positions = [0, 3, 7, 4]
        for pos in test_positions:
            if pos >= fw.slot_count:
                continue
            
            print(f"\nMoving to position {pos} ({fw.get_filter_name(pos)})...")
            if fw.set_position(pos):
                current = fw.get_position()
                print(f"✓ At position {current} ({fw.get_filter_name(current)})")
                print(f"  Focus offset: {fw.get_focus_offset(current)} µm")
            else:
                print("✗ Move failed")
        
        # Test custom filter names
        print("\n--- Testing Custom Filter Names ---")
        fw.set_filter_name(0, "Custom Red")
        fw.set_filter_name(1, "Custom Green")
        print(f"Position 0: {fw.get_filter_name(0)}")
        print(f"Position 1: {fw.get_filter_name(1)}")
        
        # Test focus offsets
        print("\n--- Testing Focus Offsets ---")
        fw.set_focus_offset(4, 100)
        print(f"Position 4 offset: {fw.get_focus_offset(4)} µm")
        
        # Disconnect
        print("\nDisconnecting...")
        fw.disconnect()
        print("✓ Disconnected")
        
        print("\n✓ All filter wheel tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_focuser(mode='auto'):
    """Test focuser functionality"""
    print("=" * 60)
    print(f"Testing Focuser ({mode} mode)")
    print("=" * 60)
    
    try:
        # Create focuser
        print(f"\nCreating focuser in '{mode}' mode...")
        foc = create_focuser(mode=mode, max_position=100000)
        
        # Connect
        print("\nConnecting...")
        if not foc.connect():
            print("✗ Failed to connect")
            return False
        
        print("\n--- Focuser Properties ---")
        print(f"Max position: {foc.max_position} steps")
        print(f"Max increment: {foc.max_increment} steps")
        print(f"Step size: {foc.step_size} µm")
        print(f"Current position: {foc.get_position()}")
        print(f"Temperature: {foc.get_temperature():.1f}°C")
        print(f"Temp comp available: {foc.temp_comp_available}")
        print(f"Temp comp enabled: {foc.temp_comp}")
        
        # Test absolute movements
        print("\n--- Testing Absolute Movement ---")
        test_positions = [60000, 40000, 50000]
        for pos in test_positions:
            if pos > foc.max_position:
                continue
            
            print(f"\nMoving to position {pos}...")
            if foc.move_to(pos):
                current = foc.get_position()
                print(f"✓ At position {current}")
                print(f"  Temperature: {foc.get_temperature():.1f}°C")
            else:
                print("✗ Move failed")
        
        # Test relative movements
        print("\n--- Testing Relative Movement ---")
        start_pos = foc.get_position()
        print(f"Starting position: {start_pos}")
        
        print("\nMoving +5000 steps...")
        foc.move_relative(5000)
        print(f"Position: {foc.get_position()} (expected: {start_pos + 5000})")
        
        print("\nMoving -3000 steps...")
        foc.move_relative(-3000)
        print(f"Position: {foc.get_position()} (expected: {start_pos + 2000})")
        
        # Test halt
        print("\n--- Testing Halt ---")
        print("Starting long move...")
        import threading
        def long_move():
            foc.move_to(80000)
        
        thread = threading.Thread(target=long_move)
        thread.start()
        
        time.sleep(0.5)  # Let it start moving
        print("Halting...")
        foc.halt()
        time.sleep(0.5)
        
        print(f"Position after halt: {foc.get_position()}")
        print(f"Is moving: {foc.is_moving()}")
        
        # Test temperature compensation
        print("\n--- Testing Temperature Compensation ---")
        print(f"Temperature: {foc.get_temperature():.1f}°C")
        foc.temp_comp = True
        print(f"Temp comp enabled: {foc.temp_comp}")
        
        # Disconnect
        print("\nDisconnecting...")
        foc.disconnect()
        print("✓ Disconnected")
        
        print("\n✓ All focuser tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hardware_detection():
    """Test hardware detection"""
    print("=" * 60)
    print("Hardware Detection")
    print("=" * 60)
    
    print(f"\nZWO EFW SDK: {'✓ Available' if ZWO_EFW_AVAILABLE else '✗ Not found'}")
    print(f"ZWO EAF SDK: {'✓ Available' if ZWO_EAF_AVAILABLE else '✗ Not found'}")
    
    if ZWO_EFW_AVAILABLE:
        print("\n--- Detecting ZWO Filter Wheels ---")
        try:
            from filterwheel import efw_lib
            num_wheels = efw_lib.EFWGetNum()
            print(f"Found {num_wheels} filter wheel(s)")
        except Exception as e:
            print(f"Error detecting wheels: {e}")
    
    if ZWO_EAF_AVAILABLE:
        print("\n--- Detecting ZWO Focusers ---")
        try:
            from focuser import eaf_lib
            num_focusers = eaf_lib.EAFGetNum()
            print(f"Found {num_focusers} focuser(s)")
        except Exception as e:
            print(f"Error detecting focusers: {e}")

def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("Filter Wheel & Focuser Test Suite")
    print("=" * 60 + "\n")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_filterwheel_focuser.py detect")
        print("  python test_filterwheel_focuser.py filterwheel [mode]")
        print("  python test_filterwheel_focuser.py focuser [mode]")
        print("  python test_filterwheel_focuser.py both [mode]")
        print("\nModes: auto, zwo, mock")
        print("\nExamples:")
        print("  python test_filterwheel_focuser.py detect")
        print("  python test_filterwheel_focuser.py filterwheel mock")
        print("  python test_filterwheel_focuser.py focuser zwo")
        print("  python test_filterwheel_focuser.py both auto")
        return
    
    command = sys.argv[1].lower()
    mode = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    
    if command == 'detect':
        test_hardware_detection()
    
    elif command == 'filterwheel' or command == 'fw':
        test_filterwheel(mode)
    
    elif command == 'focuser' or command == 'foc':
        test_focuser(mode)
    
    elif command == 'both' or command == 'all':
        print("\n")
        test_hardware_detection()
        print("\n\n")
        test_filterwheel(mode)
        print("\n\n")
        test_focuser(mode)
    
    else:
        print(f"Unknown command: {command}")
        print("Use: detect, filterwheel, focuser, or both")

if __name__ == '__main__':
    main()
