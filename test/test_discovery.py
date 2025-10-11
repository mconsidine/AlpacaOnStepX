#!/usr/bin/env python3
"""
Test Script for Alpaca Discovery Service

Run this on the same machine or another machine on the network
to verify that the discovery service is working properly.

Usage:
    python test_discovery.py              # Test localhost
    python test_discovery.py <ip>         # Test specific IP
    python test_discovery.py broadcast    # Test broadcast
"""

import socket
import json
import sys
import time

DISCOVERY_PORT = 32227
DISCOVERY_MESSAGE = "alpacadiscovery1"

def send_discovery_request(target_ip='127.0.0.1', timeout=3.0):
    """
    Send Alpaca discovery request and wait for response
    
    Args:
        target_ip: IP address to send to (or '255.255.255.255' for broadcast)
        timeout: Seconds to wait for response
    
    Returns:
        dict: Discovery response or None if no response
    """
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        print(f"Sending discovery request to {target_ip}:{DISCOVERY_PORT}...")
        
        # Send discovery message
        message = DISCOVERY_MESSAGE.encode('ascii')
        sock.sendto(message, (target_ip, DISCOVERY_PORT))
        
        print("Waiting for response...\n")
        
        # Wait for response
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                response = json.loads(data.decode('utf-8'))
                responses.append((addr, response))
                
                # Print response
                print("=" * 60)
                print(f"✓ Response from {addr[0]}:{addr[1]}")
                print("=" * 60)
                print(f"Alpaca Port: {response.get('AlpacaPort', 'N/A')}")
                
                if 'ServerName' in response:
                    print(f"Server Name: {response['ServerName']}")
                if 'Manufacturer' in response:
                    print(f"Manufacturer: {response['Manufacturer']}")
                if 'ManufacturerVersion' in response:
                    print(f"Version: {response['ManufacturerVersion']}")
                if 'Location' in response:
                    print(f"Location: {response['Location']}")
                
                print(f"\nDevices ({len(response.get('AlpacaDevices', []))}):")
                for device in response.get('AlpacaDevices', []):
                    print(f"  • {device['DeviceType']} #{device['DeviceNumber']}: {device['DeviceName']}")
                    print(f"    UniqueID: {device.get('UniqueID', 'N/A')}")
                
                print("\nFull JSON Response:")
                print(json.dumps(response, indent=2))
                print("=" * 60)
                print()
                
            except socket.timeout:
                break
            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON response: {e}")
            except Exception as e:
                print(f"✗ Error receiving response: {e}")
        
        sock.close()
        
        if not responses:
            print("✗ No response received")
            print("\nTroubleshooting:")
            print("1. Is the Alpaca server running?")
            print("2. Check firewall: sudo ufw allow 32227/udp")
            print("3. Verify server address is correct")
            print("4. Try broadcast mode: python test_discovery.py broadcast")
            return None
        
        return responses
        
    except Exception as e:
        print(f"✗ Discovery test failed: {e}")
        return None

def scan_network(subnet='192.168.1', timeout=0.5):
    """
    Scan a subnet for Alpaca servers
    
    Args:
        subnet: First three octets of subnet (e.g., '192.168.1')
        timeout: Timeout per IP (seconds)
    """
    print(f"Scanning {subnet}.0/24 for Alpaca servers...")
    print("This may take a minute...\n")
    
    found_servers = []
    
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        sys.stdout.write(f"\rScanning {ip}...")
        sys.stdout.flush()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            message = DISCOVERY_MESSAGE.encode('ascii')
            sock.sendto(message, (ip, DISCOVERY_PORT))
            
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            found_servers.append((ip, response))
            print(f"\r✓ Found server at {ip}")
            
        except socket.timeout:
            pass
        except Exception:
            pass
        finally:
            sock.close()
    
    print("\n")
    
    if found_servers:
        print(f"Found {len(found_servers)} Alpaca server(s):\n")
        for ip, response in found_servers:
            print(f"  • {ip}:{response.get('AlpacaPort', 'N/A')}")
            print(f"    {response.get('ServerName', 'Unknown Server')}")
            print(f"    Devices: {len(response.get('AlpacaDevices', []))}")
            print()
    else:
        print("No Alpaca servers found on this subnet")

def main():
    """Main test function"""
    print("=== Alpaca Discovery Test Client ===\n")
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == 'help' or arg == '-h' or arg == '--help':
            print("Usage:")
            print("  python test_discovery.py              # Test localhost")
            print("  python test_discovery.py <ip>         # Test specific IP")
            print("  python test_discovery.py broadcast    # Test broadcast")
            print("  python test_discovery.py scan         # Scan local network")
            print("  python test_discovery.py scan <subnet># Scan specific subnet")
            return
        
        elif arg == 'broadcast':
            send_discovery_request('255.255.255.255', timeout=5.0)
        
        elif arg == 'scan':
            subnet = sys.argv[2] if len(sys.argv) > 2 else '192.168.1'
            scan_network(subnet)
        
        else:
            # Specific IP
            send_discovery_request(sys.argv[1])
    else:
        # Default: test localhost
        result = send_discovery_request('127.0.0.1')
        
        if not result:
            print("\nTrying broadcast...")
            send_discovery_request('255.255.255.255', timeout=5.0)

if __name__ == '__main__':
    main()
