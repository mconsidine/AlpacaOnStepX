#!/usr/bin/env python3
"""
Test script for OnStepX telescope connection
Tests both network and serial connections
"""

import sys
import time

# Import the telescope driver
from telescope import OnStepXMount

def test_network_connection(host, port=9999):
    """Test network connection to OnStepX"""
    print("=" * 60)
    print("Testing NETWORK Connection")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print()
    
    try:
        # Create telescope instance
        telescope = OnStepXMount(
            connection_type='network',
            host=host,
            port=port
        )
        
        # Try to connect
        print("Attempting connection...")
        if telescope.connect():
            print("\n✓ CONNECTION SUCCESSFUL!\n")
            
            # Test basic commands
            print("Testing basic commands:")
            print("-" * 40)
            
            # Get product info
            product = telescope.send_command(':GVP#')
            print(f"Product:    {product}")
            
            # Get firmware version
            firmware = telescope.send_command(':GVN#')
            print(f"Firmware:   {firmware}")
            
            # Get RA
            ra = telescope.get_right_ascension()
            print(f"RA:         {ra:.4f} hours")
            
            # Get Dec
            dec = telescope.get_declination()
            print(f"Dec:        {dec:.4f} degrees")
            
            # Get tracking status
            tracking = telescope.get_tracking()
            print(f"Tracking:   {'ON' if tracking else 'OFF'}")
            
            # Get site info
            print(f"Latitude:   {telescope.site_latitude:.4f} degrees")
            print(f"Longitude:  {telescope.site_longitude:.4f} degrees")
            
            print("\n✓ All tests passed!")
            
            # Disconnect
            telescope.disconnect()
            print("✓ Disconnected cleanly")
            
            return True
        else:
            print("\n✗ CONNECTION FAILED")
            print("\nTroubleshooting:")
            print("1. Check OnStepX IP address is correct")
            print("2. Verify OnStepX WiFi is enabled")
            print("3. Ping the OnStepX: ping", host)
            print("4. Check if port 9999 is open")
            print("5. Try OnStepX web interface: http://{}".format(host))
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

def test_serial_connection(port='/dev/ttyUSB0', baudrate=9600):
    """Test serial connection to OnStepX"""
    print("=" * 60)
    print("Testing SERIAL Connection")
    print("=" * 60)
    print(f"Port:     {port}")
    print(f"Baudrate: {baudrate}")
    print()
    
    try:
        # Create telescope instance
        telescope = OnStepXMount(
            connection_type='serial',
            serial_port=port,
            baudrate=baudrate
        )
        
        # Try to connect
        print("Attempting connection...")
        if telescope.connect():
            print("\n✓ CONNECTION SUCCESSFUL!\n")
            
            # Test basic commands
            print("Testing basic commands:")
            print("-" * 40)
            
            # Get product info
            product = telescope.send_command(':GVP#')
            print(f"Product:    {product}")
            
            # Get firmware version
            firmware = telescope.send_command(':GVN#')
            print(f"Firmware:   {firmware}")
            
            # Get RA
            ra = telescope.get_right_ascension()
            print(f"RA:         {ra:.4f} hours")
            
            # Get Dec
            dec = telescope.get_declination()
            print(f"Dec:        {dec:.4f} degrees")
            
            print("\n✓ All tests passed!")
            
            # Disconnect
            telescope.disconnect()
            print("✓ Disconnected cleanly")
            
            return True
        else:
            print("\n✗ CONNECTION FAILED")
            print("\nTroubleshooting:")
            print("1. Check USB cable is connected")
            print("2. Verify port:", port)
            print("3. List available ports: ls /dev/ttyUSB* /dev/ttyACM*")
            print("4. Check permissions: sudo usermod -a -G dialout $USER")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

def find_onstepx_on_network(subnet='192.168.1'):
    """Scan network for OnStepX (port 9999)"""
    import socket
    
    print("=" * 60)
    print("Scanning Network for OnStepX")
    print("=" * 60)
    print(f"Subnet: {subnet}.0/24")
    print(f"Port:   9999")
    print("\nThis may take a few minutes...\n")
    
    found = []
    
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        sys.stdout.write(f"\rScanning {ip}...")
        sys.stdout.flush()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)
            result = sock.connect_ex((ip, 9999))
            sock.close()
            
            if result == 0:
                print(f"\r✓ Found OnStepX at {ip}")
                found.append(ip)
        except:
            pass
    
    print("\n")
    
    if found:
        print(f"Found {len(found)} OnStepX device(s):")
        for ip in found:
            print(f"  • {ip}:9999")
            print(f"    Web interface: http://{ip}")
    else:
        print("No OnStepX devices found on this subnet")
        print("\nTry:")
        print("1. Check OnStepX WiFi is enabled")
        print("2. Verify you're on the same network")
        print("3. Try a different subnet (e.g., 192.168.0)")
    
    return found

def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("OnStepX Connection Test Utility")
    print("=" * 60 + "\n")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_telescope_connection.py network <ip>")
        print("  python test_telescope_connection.py serial [port]")
        print("  python test_telescope_connection.py scan [subnet]")
        print("\nExamples:")
        print("  python test_telescope_connection.py network 192.168.1.100")
        print("  python test_telescope_connection.py serial /dev/ttyUSB0")
        print("  python test_telescope_connection.py scan 192.168.1")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == 'network':
        if len(sys.argv) < 3:
            print("Error: IP address required")
            print("Usage: python test_telescope_connection.py network <ip>")
            return
        host = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
        test_network_connection(host, port)
        
    elif mode == 'serial':
        port = sys.argv[2] if len(sys.argv) > 2 else '/dev/ttyUSB0'
        baudrate = int(sys.argv[3]) if len(sys.argv) > 3 else 9600
        test_serial_connection(port, baudrate)
        
    elif mode == 'scan':
        subnet = sys.argv[2] if len(sys.argv) > 2 else '192.168.1'
        found = find_onstepx_on_network(subnet)
        
        if found and len(found) == 1:
            print("\nWould you like to test this connection? (y/n): ", end='')
            if input().lower() == 'y':
                test_network_connection(found[0])
    else:
        print(f"Unknown mode: {mode}")
        print("Use: network, serial, or scan")

if __name__ == '__main__':
    main()
