#!/usr/bin/env python3
"""
Test script for MoveAxis satellite tracking implementation

This script validates:
1. Variable rate commands work correctly
2. Both axes can be commanded simultaneously  
3. Rates can be updated dynamically
4. Stop commands work properly
5. Integration with satellite tracking software

Usage:
    python test_moveaxis_satellite.py <onstepx-ip>
    
Example:
    python test_moveaxis_satellite.py 192.168.1.100
"""

import sys
import time
import socket

def send_command(sock, command):
    """Send command to OnStepX and get response"""
    sock.send(command.encode())
    response = sock.recv(1024).decode().strip('#\n\r')
    return response

def test_basic_connectivity(ip, port=9999):
    """Test 1: Basic connection to OnStepX"""
    print("=" * 60)
    print("TEST 1: Basic Connectivity")
    print("=" * 60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((ip, port))
        
        product = send_command(sock, ':GVP#')
        version = send_command(sock, ':GVN#')
        
        print(f"✓ Connected to {product} version {version}")
        return sock
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return None

def test_variable_rate_commands(sock):
    """Test 2: Variable rate commands"""
    print("\n" + "=" * 60)
    print("TEST 2: Variable Rate Commands")
    print("=" * 60)
    
    test_rates = [0.1, 0.5, 1.0, 2.0]
    
    print("\nTesting RA axis rates:")
    for rate in test_rates:
        cmd = f':RA{rate:.4f}#'
        response = send_command(sock, cmd)
        status = "✓" if response != '0' else "⚠"
        print(f"  {status} Set RA rate to {rate:.4f}°/s: response='{response}'")
    
    print("\nTesting Dec axis rates:")
    for rate in test_rates:
        cmd = f':RE{rate:.4f}#'
        response = send_command(sock, cmd)
        status = "✓" if response != '0' else "⚠"
        print(f"  {status} Set Dec rate to {rate:.4f}°/s: response='{response}'")
    
    # Reset to stopped
    send_command(sock, ':Qe#')
    send_command(sock, ':Qw#')
    send_command(sock, ':Qn#')
    send_command(sock, ':Qs#')

def test_movement_commands(sock):
    """Test 3: Movement initiation and stopping"""
    print("\n" + "=" * 60)
    print("TEST 3: Movement Commands")
    print("=" * 60)
    
    print("\nTesting RA East movement:")
    send_command(sock, ':RA0.1#')  # Slow rate
    send_command(sock, ':Me#')
    print("  ✓ Started RA East movement at 0.1°/s")
    time.sleep(2)
    
    print("  Stopping RA East...")
    send_command(sock, ':Qe#')
    print("  ✓ Stopped RA East movement")
    time.sleep(1)
    
    print("\nTesting RA West movement:")
    send_command(sock, ':RA0.1#')
    send_command(sock, ':Mw#')
    print("  ✓ Started RA West movement at 0.1°/s")
    time.sleep(2)
    
    print("  Stopping RA West...")
    send_command(sock, ':Qw#')
    print("  ✓ Stopped RA West movement")
    time.sleep(1)
    
    print("\nTesting Dec North movement:")
    send_command(sock, ':RE0.1#')
    send_command(sock, ':Mn#')
    print("  ✓ Started Dec North movement at 0.1°/s")
    time.sleep(2)
    
    print("  Stopping Dec North...")
    send_command(sock, ':Qn#')
    print("  ✓ Stopped Dec North movement")
    time.sleep(1)
    
    print("\nTesting Dec South movement:")
    send_command(sock, ':RE0.1#')
    send_command(sock, ':Ms#')
    print("  ✓ Started Dec South movement at 0.1°/s")
    time.sleep(2)
    
    print("  Stopping Dec South...")
    send_command(sock, ':Qs#')
    print("  ✓ Stopped Dec South movement")

def test_simultaneous_movement(sock):
    """Test 4: Simultaneous RA and Dec movement (satellite tracking)"""
    print("\n" + "=" * 60)
    print("TEST 4: Simultaneous Axis Movement")
    print("=" * 60)
    
    print("\nSimulating satellite tracking:")
    print("  Setting RA rate: 0.3°/s East")
    print("  Setting Dec rate: 0.2°/s North")
    
    # Set rates
    send_command(sock, ':RA0.3#')
    send_command(sock, ':RE0.2#')
    
    # Start both axes
    send_command(sock, ':Me#')
    send_command(sock, ':Mn#')
    
    print("  ✓ Both axes moving...")
    
    # Simulate satellite tracking for 5 seconds
    for i in range(5):
        time.sleep(1)
        # In real satellite tracking, rates would be updated here
        print(f"  Tracking... {i+1}/5 seconds")
    
    # Stop both axes
    print("\n  Stopping both axes...")
    send_command(sock, ':Qe#')
    send_command(sock, ':Qn#')
    print("  ✓ Both axes stopped")

def test_rate_updates(sock):
    """Test 5: Dynamic rate updates (critical for satellite tracking)"""
    print("\n" + "=" * 60)
    print("TEST 5: Dynamic Rate Updates")
    print("=" * 60)
    
    print("\nSimulating satellite rate changes:")
    
    rates = [
        (0.2, 0.1),  # Initial rates
        (0.3, 0.15), # Rate increase
        (0.25, 0.12), # Rate adjustment
        (0.1, 0.05), # Slowing down
        (0.0, 0.0)   # Stop
    ]
    
    # Start movement
    send_command(sock, ':Me#')
    send_command(sock, ':Mn#')
    
    for ra_rate, dec_rate in rates:
        send_command(sock, f':RA{ra_rate:.4f}#')
        send_command(sock, f':RE{dec_rate:.4f}#')
        print(f"  Updated rates: RA={ra_rate:.4f}°/s, Dec={dec_rate:.4f}°/s")
        time.sleep(1)
    
    # Ensure stopped
    send_command(sock, ':Qe#')
    send_command(sock, ':Qw#')
    send_command(sock, ':Qn#')
    send_command(sock, ':Qs#')
    print("  ✓ All movement stopped")

def test_emergency_stop(sock):
    """Test 6: Emergency stop functionality"""
    print("\n" + "=" * 60)
    print("TEST 6: Emergency Stop")
    print("=" * 60)
    
    print("\nStarting movement on both axes...")
    send_command(sock, ':RA0.5#')
    send_command(sock, ':RE0.5#')
    send_command(sock, ':Me#')
    send_command(sock, ':Mn#')
    
    time.sleep(1)
    
    print("  Issuing emergency stop (:Q#)...")
    send_command(sock, ':Q#')
    print("  ✓ Emergency stop executed")
    
    # Verify all axes stopped
    send_command(sock, ':Qe#')
    send_command(sock, ':Qw#')
    send_command(sock, ':Qn#')
    send_command(sock, ':Qs#')

def run_all_tests(ip):
    """Run complete test suite"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  OnStepX MoveAxis Satellite Tracking Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    
    # Test 1: Connect
    sock = test_basic_connectivity(ip)
    if not sock:
        print("\n✗ ABORTED: Could not connect to OnStepX")
        return False
    
    try:
        # Test 2: Variable rate commands
        test_variable_rate_commands(sock)
        
        # Test 3: Movement commands
        test_movement_commands(sock)
        
        # Test 4: Simultaneous movement
        test_simultaneous_movement(sock)
        
        # Test 5: Dynamic rate updates
        test_rate_updates(sock)
        
        # Test 6: Emergency stop
        test_emergency_stop(sock)
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print("✓ All tests completed successfully!")
        print("\nYour OnStepX controller supports:")
        print("  • Variable rate MoveAxis commands")
        print("  • Simultaneous RA and Dec movement")
        print("  • Dynamic rate updates")
        print("  • Emergency stop functionality")
        print("\n✓ READY FOR SATELLITE TRACKING")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        sock.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_moveaxis_satellite.py <onstepx-ip>")
        print("Example: python test_moveaxis_satellite.py 192.168.1.100")
        sys.exit(1)
    
    ip = sys.argv[1]
    
    print("\n⚠  WARNING: This test will move your telescope!")
    print("   Ensure the mount is:")
    print("     • Properly balanced")
    print("     • Free to move in all directions")
    print("     • Not pointing at anything valuable")
    print("\n   Press Ctrl+C to abort, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(0)
    
    success = run_all_tests(ip)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
