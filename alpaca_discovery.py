"""
Alpaca Discovery Protocol (UDP)
Implements UDP broadcast discovery for ASCOM Alpaca devices

Listens on port 32227 for discovery requests and responds with device list.
This allows clients like N.I.N.A. to automatically find the server.
"""

import socket
import threading
import json
import time
import logging

logger = logging.getLogger(__name__)

class AlpacaDiscovery:
    """
    Alpaca UDP Discovery Service
    
    Listens for "alpacadiscovery1" on UDP port 32227
    Responds with JSON containing server port and device list
    """
    
    DISCOVERY_PORT = 32227
    DISCOVERY_MESSAGE = "alpacadiscovery1"
    
    def __init__(self, alpaca_port, server_info, get_devices_callback):
        """
        Initialize discovery service
        
        Args:
            alpaca_port: Port where Alpaca HTTP server is running (e.g., 5555)
            server_info: Server information dict from config
            get_devices_callback: Function that returns current device list
        """
        self.alpaca_port = alpaca_port
        self.server_info = server_info
        self.get_devices = get_devices_callback
        self.running = False
        self.thread = None
        self.socket = None
    
    def start(self):
        """Start the discovery service in a background thread"""
        if self.running:
            logger.warning("Discovery service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.thread.start()
        logger.info(f"Alpaca Discovery service started on UDP port {self.DISCOVERY_PORT}")
    
    def stop(self):
        """Stop the discovery service"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Alpaca Discovery service stopped")
    
    def _discovery_loop(self):
        """Main discovery loop - listens for UDP broadcasts"""
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Allow broadcasts
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Bind to discovery port on all interfaces
            self.socket.bind(('', self.DISCOVERY_PORT))
            self.socket.settimeout(1.0)  # 1 second timeout for clean shutdown
            
            logger.info(f"Listening for Alpaca discovery on UDP port {self.DISCOVERY_PORT}")
            
            while self.running:
                try:
                    # Wait for discovery request
                    data, addr = self.socket.recvfrom(1024)
                    message = data.decode('ascii').strip()
                    
                    # Check if it's an Alpaca discovery request
                    if message.lower() == self.DISCOVERY_MESSAGE.lower():
                        logger.info(f"Discovery request from {addr[0]}:{addr[1]}")
                        self._send_discovery_response(addr)
                    else:
                        logger.debug(f"Unknown discovery message: {message}")
                        
                except socket.timeout:
                    # Timeout is normal - allows checking self.running
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error in discovery loop: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to start discovery service: {e}")
        finally:
            if self.socket:
                self.socket.close()
    
    def _send_discovery_response(self, addr):
        """
        Send discovery response to client
        
        Args:
            addr: Tuple of (ip, port) to send response to
        """
        try:
            # Get current device list
            devices = self.get_devices()
            
            # Build response
            response = {
                "AlpacaPort": self.alpaca_port
            }
            
            # Add server identification (optional but helpful)
            if self.server_info:
                response["ServerName"] = self.server_info.get('server_name', 'Unknown')
                response["Manufacturer"] = self.server_info.get('manufacturer', 'Unknown')
                response["ManufacturerVersion"] = self.server_info.get('manufacturer_version', '1.0')
                response["Location"] = self.server_info.get('location', 'Unknown')
            
            # Add device list in Alpaca format
            # Note: Some clients expect this format, others expect full device objects
            alpaca_devices = []
            for device in devices:
                alpaca_devices.append({
                    "DeviceName": device.get('DeviceName', 'Unknown'),
                    "DeviceType": device.get('DeviceType', 'Unknown'),
                    "DeviceNumber": device.get('DeviceNumber', 0),
                    "UniqueID": device.get('UniqueID', '')
                })
            
            response["AlpacaDevices"] = alpaca_devices
            
            # Convert to JSON
            response_json = json.dumps(response)
            
            # Send response back to requester
            self.socket.sendto(response_json.encode('utf-8'), addr)
            
            logger.info(f"Sent discovery response to {addr[0]}:{addr[1]} with {len(alpaca_devices)} devices")
            logger.debug(f"Response: {response_json}")
            
        except Exception as e:
            logger.error(f"Error sending discovery response: {e}")
    
    def test_discovery(self, target_ip='127.0.0.1'):
        """
        Test function to send a discovery request to a specific IP
        
        Args:
            target_ip: IP address to send discovery to (default: localhost)
        
        Returns:
            Response dict or None
        """
        try:
            # Create test socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            test_socket.settimeout(2.0)
            
            # Send discovery request
            message = self.DISCOVERY_MESSAGE.encode('ascii')
            test_socket.sendto(message, (target_ip, self.DISCOVERY_PORT))
            
            print(f"Sent discovery request to {target_ip}:{self.DISCOVERY_PORT}")
            
            # Wait for response
            data, addr = test_socket.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            print(f"\nReceived response from {addr[0]}:{addr[1]}:")
            print(json.dumps(response, indent=2))
            
            test_socket.close()
            return response
            
        except socket.timeout:
            print("No response received (timeout)")
            return None
        except Exception as e:
            print(f"Test failed: {e}")
            return None


# Standalone test function
def test_discovery_client():
    """Test the discovery protocol by sending a request"""
    print("=== Alpaca Discovery Test Client ===\n")
    
    # Try localhost first
    print("Testing localhost...")
    discovery = AlpacaDiscovery(5555, {}, lambda: [])
    response = discovery.test_discovery('127.0.0.1')
    
    if not response:
        # Try broadcast
        print("\nTrying broadcast to 255.255.255.255...")
        response = discovery.test_discovery('255.255.255.255')
    
    return response


if __name__ == '__main__':
    # Run test client
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_discovery_client()
    else:
        # Simple server test
        print("Starting test discovery server...")
        print("Press Ctrl+C to stop\n")
        
        # Mock device list
        def get_test_devices():
            return [
                {
                    'DeviceName': 'Test Telescope',
                    'DeviceType': 'Telescope',
                    'DeviceNumber': 0,
                    'UniqueID': 'test-telescope-001'
                },
                {
                    'DeviceName': 'Test Camera',
                    'DeviceType': 'Camera',
                    'DeviceNumber': 0,
                    'UniqueID': 'test-camera-001'
                }
            ]
        
        server_info = {
            'server_name': 'Test Alpaca Server',
            'manufacturer': 'Test',
            'manufacturer_version': '1.0',
            'location': 'Test Lab'
        }
        
        discovery = AlpacaDiscovery(5555, server_info, get_test_devices)
        discovery.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            discovery.stop()
