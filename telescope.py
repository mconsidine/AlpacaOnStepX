"""
OnStepX Telescope Mount Driver - Network + USB Support
Implements ASCOM ITelescopeV4 interface
Supports both WiFi/Network (TCP/IP) and USB Serial connections
Includes enhanced IsSlewing detection, pier side prediction, and Action() methods
"""

import serial
import serial.tools.list_ports
import socket
import time
import math
from threading import Lock
from enum import IntEnum
from datetime import datetime, timezone
import alpaca_helpers as helpers

# ========================================================================
# Base Tracking Rate Constants (degrees/second)
# ========================================================================

# Sidereal rate - Earth's rotation relative to the stars
# 360 degrees / 86164.0905 seconds (one sidereal day)
SIDEREAL_RATE = 0.0041780746  # degrees/second

# Solar rate - Earth's rotation relative to the Sun
# 360 degrees / 86400 seconds (one solar day)
# Approximately 0.997269566 × sidereal
SOLAR_RATE = 0.0041666667  # degrees/second

# Lunar rate - Track the Moon
# Sidereal rate minus Moon's orbital motion
# Moon moves ~13.2° eastward per day
# Approximately 0.9636 × sidereal
LUNAR_RATE = 0.0040266670  # degrees/second

# King rate - For circumpolar objects
# Slightly faster than sidereal (approximately 1.00274 × sidereal)
# Used for objects very close to celestial pole
KING_RATE = 0.0041895210  # degrees/second

# ========================================================================
# Tracking Rate Enumeration
# ========================================================================

class TrackingRate:
    """Standard astronomical tracking rates"""
    SIDEREAL = SIDEREAL_RATE
    SOLAR = SOLAR_RATE
    LUNAR = LUNAR_RATE
    KING = KING_RATE
    
    # Ratios relative to sidereal
    SOLAR_RATIO = SOLAR_RATE / SIDEREAL_RATE      # 0.99727
    LUNAR_RATIO = LUNAR_RATE / SIDEREAL_RATE      # 0.96367
    KING_RATIO = KING_RATE / SIDEREAL_RATE        # 1.00274
    
    @staticmethod
    def get_rate_name(rate):
        """Get the name of a tracking rate"""
        if abs(rate - SIDEREAL_RATE) < 0.000001:
            return "Sidereal"
        elif abs(rate - SOLAR_RATE) < 0.000001:
            return "Solar"
        elif abs(rate - LUNAR_RATE) < 0.000001:
            return "Lunar"
        elif abs(rate - KING_RATE) < 0.000001:
            return "King"
        else:
            return f"Custom ({rate:.6f}°/s)"

# ========================================================================
# Sidereal Rate Multipliers (for manual control rates)
# ========================================================================

class SiderealMultiplier:
    """Standard movement rates as multiples of sidereal rate"""
    VERY_SLOW = 0.25   # 0.25× sidereal
    SLOW = 0.5         # 0.5× sidereal
    GUIDE = 1.0        # 1× sidereal (same as tracking)
    FAST_GUIDE = 2.0   # 2× sidereal
    CENTER = 4.0       # 4× sidereal (centering objects)
    FIND = 8.0         # 8× sidereal (finding objects)
    MOVE = 16.0        # 16× sidereal (slewing)
    SLEW = 24.0        # 24× sidereal (fast slew)
    FAST_SLEW = 40.0   # 40× sidereal
    MAX = 60.0         # 60× sidereal (maximum)


class AlignmentModes(IntEnum):
    algAltAz = 0
    algPolar = 1
    algGermanPolar = 2

class EquatorialCoordinateType(IntEnum):
    equOther = 0
    equTopocentric = 1
    equJ2000 = 2
    equJ2050 = 3
    equB1950 = 4

class PierSide(IntEnum):
    pierUnknown = -1
    pierEast = 0
    pierWest = 1

class DriveRates(IntEnum):
    driveSidereal = 0
    driveLunar = 1
    driveSolar = 2
    driveKing = 3

class GuideDirections(IntEnum):
    guideNorth = 0
    guideSouth = 1
    guideEast = 2
    guideWest = 3

class TelescopeAxes(IntEnum):
    axisPrimary = 0
    axisSecondary = 1
    axisTertiary = 2

class OnStepXMount:
    """OnStepX telescope mount driver - supports Network and USB"""
    
    def __init__(self, connection_type='network', host=None, port=9999, 
                 serial_port=None, baudrate=9600):
        """
        Initialize OnStepX mount driver
        
        Args:
            connection_type: 'network' or 'serial'
            host: IP address for network connection (e.g., '192.168.1.100')
            port: TCP port for network connection (default: 9999)
            serial_port: Serial port for USB connection (e.g., '/dev/ttyUSB0')
            baudrate: Baud rate for serial connection (default: 9600)
        """
        self.connection_type = connection_type.lower()
        
        # Network settings
        self.host = host
        self.port = port
        self.socket = None
        
        # Serial settings
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.serial = None
        
        # Connection state
        self.lock = Lock()
        self.is_connected = False
        self.is_connecting = False
        
        # Mount state
        self.target_ra = 0.0
        self.target_dec = 0.0
        self.slew_settle_time = 0
        self.tracking_rate = DriveRates.driveSidereal
        self.guide_rate_ra = 0.5
        self.guide_rate_dec = 0.5
        self.does_refraction = True
        self.pulse_guiding = False
        self.pulse_guide_end_time = 0
        self.pulse_guide_direction = None
        self.pulse_guide_duration = 0
        self.pulse_guide_start_time = 0
        
        # Slewing state tracking (for enhanced IsSlewing)
        self._slew_target = None
        self._slewing = False
        self._slew_start_time = None
        self._position_stable_since = None
        self._last_position = None
        self._slew_timeout = 120  # 2 minutes max slew time
        self._stability_threshold = 1.0  # arcminutes
        self._stability_duration = 2.0   # seconds
        
        # Mount info
        self.site_latitude = 0.0
        self.site_longitude = 0.0
        self.site_elevation = 0.0
        self.alignment_mode = AlignmentModes.algGermanPolar
        self.aperture_area = 0.0
        self.aperture_diameter = 0.0
        self.focal_length = 0.0
        self.equatorial_system = EquatorialCoordinateType.equJ2000
        
        # Pier side and meridian settings
        self.meridian_offset_east = 0.0   # Hours (from OnStepX config)
        self.meridian_offset_west = 0.0   # Hours (from OnStepX config)
        self.auto_flip_enabled = True
        self.supports_king_rate = False
        
        self._max_axis_rate = 2.0  # Default max rate, degrees/second
    
    def _find_serial_port(self):
        """Auto-detect OnStepX on USB serial ports"""
        if self.serial_port:
            return self.serial_port
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.device or 'ACM' in port.device:
                return port.device
        
        return '/dev/ttyUSB0'  # Default fallback
    
    def connect(self):
        """Connect to mount (network or serial)"""
        self.is_connecting = True
        try:
            if self.connection_type == 'network':
                return self._connect_network()
            elif self.connection_type == 'serial':
                return self._connect_serial()
            else:
                print(f"Unknown connection type: {self.connection_type}")
                return False
        finally:
            self.is_connecting = False
    
    def _connect_network(self):
        """Connect via TCP/IP (WiFi/Ethernet)"""
        try:
            if not self.host:
                print("Error: Network host not specified")
                return False
            
            print(f"Connecting to OnStepX at {self.host}:{self.port}...")
            
            # Create TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            
            # Test connection
            product = self.send_command(':GVP#')
            if product:
                self.is_connected = True
                print(f"✓ Connected to OnStepX via network: {product}")
                self._update_site_info()
                self._update_meridian_settings()
                return True
            else:
                print("✗ No response from OnStepX")
                self.disconnect()
                return False
                
        except socket.timeout:
            print(f"✗ Connection timeout to {self.host}:{self.port}")
            self.is_connected = False
            return False
        except ConnectionRefusedError:
            print(f"✗ Connection refused by {self.host}:{self.port}")
            print("  Check: Is OnStepX WiFi enabled? Is IP correct?")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"✗ Network connection failed: {e}")
            self.is_connected = False
            return False
    
    def _connect_serial(self):
        """Connect via USB serial"""
        try:
            if not self.serial_port:
                self.serial_port = self._find_serial_port()
            
            print(f"Connecting to OnStepX on {self.serial_port}...")
            
            self.serial = serial.Serial(
                self.serial_port,
                self.baudrate,
                timeout=2,
                write_timeout=2
            )
            time.sleep(2)  # Allow connection to stabilize
            
            # Test connection
            product = self.send_command(':GVP#')
            if product:
                self.is_connected = True
                print(f"✓ Connected to OnStepX via serial: {product}")
                self._update_site_info()
                self._update_meridian_settings()
                return True
            else:
                print("✗ No response from OnStepX")
                self.disconnect()
                return False
                
        except serial.SerialException as e:
            print(f"✗ Serial connection failed: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"✗ Serial connection error: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from mount"""
        if self.connection_type == 'network' and self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        elif self.connection_type == 'serial' and self.serial:
            try:
                if self.serial.is_open:
                    self.serial.close()
            except:
                pass
            self.serial = None
        
        self.is_connected = False
    
    def send_command(self, command):
        """Send command to mount and return response"""
        if not self.is_connected:
            return None
        
        with self.lock:
            try:
                if self.connection_type == 'network':
                    return self._send_network(command)
                elif self.connection_type == 'serial':
                    return self._send_serial(command)
            except Exception as e:
                print(f"Command error: {e}")
                return None
    
    def _send_network(self, command):
        """Send command via network"""
        if not self.socket:
            return None
        
        try:
            # Send command
            self.socket.sendall(command.encode('ascii'))
            
            # Receive response
            response = b''
            start_time = time.time()
            while time.time() - start_time < 2:
                try:
                    chunk = self.socket.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                    if b'#' in response:
                        break
                except socket.timeout:
                    break
            
            # Parse response
            if response:
                response_str = response.decode('ascii').strip('#').strip()
                return response_str if response_str else None
            return None
            
        except Exception as e:
            print(f"Network send error: {e}")
            return None
    
    def _send_serial(self, command):
        """Send command via serial"""
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            self.serial.reset_input_buffer()
            self.serial.write(command.encode('ascii'))
            
            response = b''
            start_time = time.time()
            while time.time() - start_time < 2:
                if self.serial.in_waiting:
                    byte = self.serial.read(1)
                    if byte == b'#':
                        break
                    response += byte
            
            if response:
                return response.decode('ascii').strip()
            return None
            
        except Exception as e:
            print(f"Serial send error: {e}")
            return None
    
    def _update_site_info(self):
        """Get site information from mount"""
        try:
            # Get latitude
            lat_str = self.send_command(':Gt#')
            if lat_str:
                self.site_latitude = helpers.parse_degrees(lat_str)
            
            # Get longitude
            lon_str = self.send_command(':Gg#')
            if lon_str:
                self.site_longitude = helpers.parse_degrees(lon_str)
            
        except Exception as e:
            print(f"Error updating site info: {e}")
    
    def _update_meridian_settings(self):
        """Query OnStepX for meridian flip settings"""
        try:
            # Get meridian limits from OnStepX
            response = self.send_command(':Gh#')
            if response:
                self.meridian_offset_east = helpers.parse_ra_hours(response) if response else 0.0
            
            # Some OnStepX versions have separate east/west offsets
            response = self.send_command(':GXE0#')
            if response:
                try:
                    self.meridian_offset_east = float(response) / 15.0
                except:
                    pass
            
            response = self.send_command(':GXE1#')
            if response:
                try:
                    self.meridian_offset_west = float(response) / 15.0
                except:
                    pass
            
            print(f"  Meridian offsets: East={self.meridian_offset_east:.2f}h, West={self.meridian_offset_west:.2f}h")
            
        except Exception as e:
            print(f"  Could not read meridian settings: {e}")
            self.meridian_offset_east = 0.0
            self.meridian_offset_west = 0.0
    
    # ========================================================================
    # Position methods
    # ========================================================================
    
    def get_right_ascension(self):
        """Get current RA in hours"""
        response = self.send_command(':GR#')
        if response:
            return helpers.parse_ra_hours(response)
        return None
    
    def get_declination(self):
        """Get current Dec in degrees"""
        response = self.send_command(':GD#')
        if response:
            return helpers.parse_degrees(response)
        return None
    
    def get_altitude(self):
        """Get current altitude in degrees"""
        response = self.send_command(':GA#')
        if response:
            return helpers.parse_degrees(response)
        return 0.0
    
    def get_azimuth(self):
        """Get current azimuth in degrees"""
        response = self.send_command(':GZ#')
        if response:
            return helpers.parse_degrees(response)
        return 0.0
    
    def get_sidereal_time(self):
        """Get local sidereal time in hours"""
        response = self.send_command(':GS#')
        if response:
            return helpers.parse_ra_hours(response)
        return None
    
    # ========================================================================
    # Tracking methods
    # ========================================================================
    
    def get_tracking(self):
        """Get tracking state"""
        response = self.send_command(':GT#')
        return response != '0' if response else False
    
    def set_tracking(self, enabled):
        """Enable/disable tracking"""
        if enabled:
            self.send_command(':Te#')
        else:
            self.send_command(':Td#')
    
    def set_tracking_rate(self, rate):
        """Set tracking rate"""
        rate_cmds = {
            DriveRates.driveSidereal: ':TQ#',
            DriveRates.driveLunar: ':TL#',
            DriveRates.driveSolar: ':TS#',
        }
        if rate in rate_cmds:
            self.send_command(rate_cmds[rate])
            self.tracking_rate = rate
    
    def get_supported_tracking_rates(self):
        """Get list of tracking rates supported by this mount"""
        rates = [
            DriveRates.driveSidereal,
            DriveRates.driveLunar,
            DriveRates.driveSolar
        ]
        
        # Check if King rate is supported
        response = self.send_command(':TK#')
        if response == '1':
            rates.append(DriveRates.driveKing)
            self.supports_king_rate = True
            self.set_tracking_rate(self.tracking_rate)  # Restore
        else:
            self.supports_king_rate = False
        
        return rates
    
    # ========================================================================
    # Slewing methods with enhanced IsSlewing detection
    # ========================================================================
    
    def _set_slew_target(self, ra_hours, dec_degrees):
        """Set target for slew tracking"""
        self._slew_target = (ra_hours, dec_degrees)
        self._slewing = True
        self._slew_start_time = time.time()
        self._position_stable_since = None
        self._last_position = None
    
    def _clear_slew_state(self):
        """Clear slewing state tracking"""
        self._slew_target = None
        self._slewing = False
        self._slew_start_time = None
        self._position_stable_since = None
        self._last_position = None
    
    def is_slewing(self):
        """
        Enhanced slewing detection using position stability
        
        OnStepX doesn't provide reliable IsSlewing status, so we:
        1. Track when we start a slew
        2. Poll position to detect when we're close to target
        3. Wait for position to stabilize (no movement for 2 seconds)
        4. Consider slew complete when stable near target
        """
        if not self.is_connected:
            return False
        
        # If no slew target was ever set, not slewing
        if self._slew_target is None:
            return False
        
        # Check for timeout (safety)
        if self._slew_start_time:
            elapsed = time.time() - self._slew_start_time
            if elapsed > self._slew_timeout:
                print(f"⚠ Slew timeout after {elapsed:.1f} seconds")
                self._clear_slew_state()
                return False
        
        # Get current position
        current_ra = self.get_right_ascension()
        current_dec = self.get_declination()
        
        if current_ra is None or current_dec is None:
            # Can't read position - assume still slewing
            return True
        
        # Calculate distance to target (in arcminutes)
        target_ra, target_dec = self._slew_target
        
        # RA difference in arcminutes (accounting for hour -> degree conversion)
        ra_diff = abs(current_ra - target_ra) * 15.0 * 60.0
        
        # Handle RA wrap around (0h = 24h)
        if ra_diff > 12.0 * 15.0 * 60.0:  # More than 12 hours
            ra_diff = 24.0 * 15.0 * 60.0 - ra_diff
        
        # Dec difference in arcminutes
        dec_diff = abs(current_dec - target_dec) * 60.0
        
        # Total angular distance
        total_distance = (ra_diff**2 + dec_diff**2)**0.5
        
        # Are we close to target?
        if total_distance < self._stability_threshold:
            # Close to target - check for stability
            
            if self._position_stable_since is None:
                # Just arrived near target
                self._position_stable_since = time.time()
                self._last_position = (current_ra, current_dec)
                return True
            
            # Check if position has moved since last check
            if self._last_position:
                last_ra, last_dec = self._last_position
                
                ra_movement = abs(current_ra - last_ra) * 15.0 * 60.0  # arcminutes
                dec_movement = abs(current_dec - last_dec) * 60.0      # arcminutes
                total_movement = (ra_movement**2 + dec_movement**2)**0.5
                
                if total_movement > 0.1:  # Moved more than 0.1 arcminutes (6 arcsec)
                    # Position is still changing - reset stability timer
                    self._position_stable_since = time.time()
                    self._last_position = (current_ra, current_dec)
                    return True
            
            # How long has position been stable?
            stable_time = time.time() - self._position_stable_since
            
            if stable_time >= self._stability_duration:
                # Position stable for required duration - slew complete!
                self._clear_slew_state()
                return False
            
            # Still waiting for stability
            return True
        
        # Still far from target - definitely slewing
        return True
    
    def slew_to_coords(self, ra_hours, dec_degrees):
        """Slew to RA/Dec coordinates"""
        ra_str = helpers.format_ra_hours(ra_hours)
        dec_str = helpers.format_dec_degrees(dec_degrees).replace(':', '*')
        
        self.send_command(f':Sr{ra_str}#')
        self.send_command(f':Sd{dec_str}#')
        
        response = self.send_command(':MS#')
        
        if response == '0':
            # Slew started successfully - track target
            self._set_slew_target(ra_hours, dec_degrees)
            return True
        else:
            # Slew failed
            self._clear_slew_state()
            return False
    
    def slew_to_altaz(self, azimuth, altitude):
        """Slew to Alt/Az coordinates"""
        az_str = helpers.format_dec_degrees(azimuth).replace(':', '*')
        alt_str = helpers.format_dec_degrees(altitude).replace(':', '*')
        
        self.send_command(f':Sz{az_str}#')
        self.send_command(f':Sa{alt_str}#')
        
        response = self.send_command(':MA#')
        
        if response == '0':
            # For Alt/Az slews, we don't have RA/Dec target
            self._slewing = True
            self._slew_start_time = time.time()
            return True
        else:
            self._clear_slew_state()
            return False
    
    def stop_slew(self):
        """Stop all slewing"""
        self.send_command(':Q#')
        self._clear_slew_state()
    
    def wait_for_slew_complete(self, timeout=120):
        """Wait for slew to complete (blocking)"""
        start = time.time()
        while self.is_slewing():
            if time.time() - start > timeout:
                return False
            time.sleep(0.5)
        return True
    
    # ========================================================================
    # Sync methods
    # ========================================================================
    
    def sync_to_coords(self, ra_hours, dec_degrees):
        """Sync mount to coordinates"""
        ra_str = helpers.format_ra_hours(ra_hours)
        dec_str = helpers.format_dec_degrees(dec_degrees).replace(':', '*')
        
        self.send_command(f':Sr{ra_str}#')
        self.send_command(f':Sd{dec_str}#')
        
        response = self.send_command(':CM#')
        return response is not None
    
    def sync_to_altaz(self, azimuth, altitude):
        """Sync to Alt/Az coordinates"""
        az_str = helpers.format_dec_degrees(azimuth).replace(':', '*')
        alt_str = helpers.format_dec_degrees(altitude).replace(':', '*')
        
        self.send_command(f':Sz{az_str}#')
        self.send_command(f':Sa{alt_str}#')
        self.send_command(':CM#')
    
    # ========================================================================
    # Park methods
    # ========================================================================
    
    def get_parked(self):
        """Check if mount is parked"""
        response = self.send_command(':h?#')
        return response == 'P' if response else False
    
    def get_at_park(self):
        """Check if mount is at park position"""
        response = self.send_command(':GU#')
        return response == 'P' if response else False
    
    def get_at_home(self):
        """Check if mount is at home position"""
        response = self.send_command(':GU#')
        return response == 'H' if response else False
    
    def park(self):
        """Park the mount"""
        response = self.send_command(':hP#')
        return response == '1'
    
    def unpark(self):
        """Unpark the mount"""
        response = self.send_command(':hR#')
        return response == '1'
    
    def find_home(self):
        """Find home position"""
        response = self.send_command(':hF#')
        return response == '1'
    
    def set_park_position(self):
        """Set current position as park position"""
        self.send_command(':hQ#')
    
    # ========================================================================
    # Pier Side methods (enhanced)
    # ========================================================================
    
    def get_side_of_pier(self):
        """Get current side of pier"""
        try:
            response = self.send_command(':Gm#')
            if response:
                if response.upper() == 'E':
                    return PierSide.pierEast
                elif response.upper() == 'W':
                    return PierSide.pierWest
            
            # Fallback: calculate from position
            ra = self.get_right_ascension()
            lst = self.get_sidereal_time()
            
            if ra is not None and lst is not None:
                ha = lst - ra
                while ha > 12.0:
                    ha -= 24.0
                while ha < -12.0:
                    ha += 24.0
                
                return PierSide.pierEast if ha < 0 else PierSide.pierWest
            
        except Exception as e:
            print(f"Error getting pier side: {e}")
        
        return PierSide.pierUnknown
    
    def destination_side_of_pier(self, ra_hours, dec_degrees):
        """Predict pier side after slewing to coordinates"""
        try:
            lst = self.get_sidereal_time()
            if lst is None:
                return PierSide.pierUnknown
            
            # Calculate hour angle
            ha = lst - ra_hours
            
            # Normalize to -12 to +12 hours
            while ha > 12.0:
                ha -= 24.0
            while ha < -12.0:
                ha += 24.0
            
            # Apply meridian offsets from OnStepX configuration
            if ha < 0:
                # East side
                if ha < -(12.0 + self.meridian_offset_east):
                    return PierSide.pierWest
                else:
                    return PierSide.pierEast
            else:
                # West side
                if ha > self.meridian_offset_west:
                    return PierSide.pierEast
                else:
                    return PierSide.pierWest
            
        except Exception as e:
            print(f"Error calculating destination pier side: {e}")
            return PierSide.pierUnknown
    
    def should_flip_after_slew(self, target_ra, target_dec):
        """Determine if mount will flip to opposite pier side"""
        current_side = self.get_side_of_pier()
        destination_side = self.destination_side_of_pier(target_ra, target_dec)
        
        will_flip = (current_side != PierSide.pierUnknown and 
                     destination_side != PierSide.pierUnknown and
                     current_side != destination_side)
        
        return (will_flip, current_side, destination_side)
    
    def can_reach_coordinates(self, ra_hours, dec_degrees):
        """Check if coordinates are physically accessible by mount"""
        # Check declination limits
        if dec_degrees < -90 or dec_degrees > 90:
            return (False, f"Declination {dec_degrees:.1f}° out of range")
        
        # Check if below horizon
        if self.site_latitude != 0:
            alt = self._calculate_altitude(ra_hours, dec_degrees)
            if alt < 0:
                return (False, f"Target below horizon (alt={alt:.1f}°)")
        
        # Check hour angle limits
        lst = self.get_sidereal_time()
        if lst is not None:
            ha = lst - ra_hours
            while ha > 12.0:
                ha -= 24.0
            while ha < -12.0:
                ha += 24.0
            
            max_ha_east = 12.0 + self.meridian_offset_east
            max_ha_west = self.meridian_offset_west
            
            if ha < -max_ha_east or ha > max_ha_west:
                return (False, f"Beyond meridian limits (HA={ha:.1f}h)")
        
        return (True, "")
    
    def _calculate_altitude(self, ra_hours, dec_degrees):
        """Calculate altitude of target"""
        lst = self.get_sidereal_time()
        if lst is None:
            return 0
        
        ha = (lst - ra_hours) * 15.0  # Convert to degrees
        
        ha_rad = math.radians(ha)
        dec_rad = math.radians(dec_degrees)
        lat_rad = math.radians(self.site_latitude)
        
        sin_alt = (math.sin(dec_rad) * math.sin(lat_rad) + 
                   math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
        
        alt = math.degrees(math.asin(sin_alt))
        return alt
    
    # ========================================================================
    # Guide methods (enhanced)
    # ========================================================================
    
    def pulse_guide(self, direction, duration_ms):
        """Pulse guide in specified direction"""
        direction_cmds = {
            GuideDirections.guideNorth: ':Mgn',
            GuideDirections.guideSouth: ':Mgs',
            GuideDirections.guideEast: ':Mge',
            GuideDirections.guideWest: ':Mgw',
        }
        
        if direction not in direction_cmds:
            return False
        
        # Format duration (milliseconds)
        cmd = f"{direction_cmds[direction]}{duration_ms:04d}#"
        
        # Send guide pulse command
        response = self.send_command(cmd)
        
        if response == '0' or response is None:
            self.pulse_guiding = True
            self.pulse_guide_direction = direction
            self.pulse_guide_duration = duration_ms
            self.pulse_guide_start_time = time.time()
            self.pulse_guide_end_time = time.time() + (duration_ms / 1000.0)
            return True
        else:
            print(f"⚠ Guide pulse command failed: {response}")
            return False
    
    def is_pulse_guiding(self):
        """Check if pulse guiding is currently active"""
        if not self.pulse_guiding:
            return False
        
        current_time = time.time()
        
        if current_time > self.pulse_guide_end_time:
            self.pulse_guiding = False
            return False
        
        # Try to query OnStepX guide status for accuracy
        try:
            response = self.send_command(':GU#')
            if response:
                if response == 'G':
                    return True
                elif response == 'N' or response == '0':
                    self.pulse_guiding = False
                    return False
        except:
            pass
        
        return True
    
    def get_guide_pulse_info(self):
        """Get information about current/last guide pulse"""
        if not hasattr(self, 'pulse_guide_direction'):
            return None
        
        remaining = 0
        if self.pulse_guiding:
            remaining = max(0, self.pulse_guide_end_time - time.time())
        
        direction_names = {
            GuideDirections.guideNorth: 'North',
            GuideDirections.guideSouth: 'South',
            GuideDirections.guideEast: 'East',
            GuideDirections.guideWest: 'West'
        }
        
        return {
            'active': self.pulse_guiding,
            'direction': direction_names.get(self.pulse_guide_direction, 'Unknown'),
            'duration_ms': self.pulse_guide_duration,
            'remaining_ms': int(remaining * 1000),
            'elapsed_ms': int((time.time() - self.pulse_guide_start_time) * 1000)
        }
    
    def stop_guide_pulse(self):
        """Emergency stop of guide pulse"""
        self.send_command(':Q#')
        self.pulse_guiding = False
        return True
    '''
    # ========================================================================
    # Move axis methods
    # ========================================================================
    
    def move_axis(self, axis, rate):
        #"""Move axis at specified rate"""
        if axis == TelescopeAxes.axisPrimary:  # RA
            if rate > 0:
                self.send_command(f':RG{abs(rate):.1f}#')
                self.send_command(':Me#')
            elif rate < 0:
                self.send_command(f':RG{abs(rate):.1f}#')
                self.send_command(':Mw#')
            else:
                self.send_command(':Qe#')
                self.send_command(':Qw#')
        elif axis == TelescopeAxes.axisSecondary:  # Dec
            if rate > 0:
                self.send_command(f':RG{abs(rate):.1f}#')
                self.send_command(':Mn#')
            elif rate < 0:
                self.send_command(f':RG{abs(rate):.1f}#')
                self.send_command(':Ms#')
            else:
                self.send_command(':Qn#')
                self.send_command(':Qs#')
    '''
    
    # ========================================================================
    # Move axis methods - CORRECTED FOR SATELLITE TRACKING
    # ========================================================================
    # 
    # This implementation supports variable-rate MoveAxis for satellite tracking
    # using OnStepX's :RAn.n# and :REn.n# commands
    #
    # Reference: OnStep variable rate guide commands
    # Used by: Satellite tracking software, advanced mount control
    # ========================================================================

    def move_axis(self, axis, rate):
        """
        Move telescope axis at specified rate (ASCOM Platform 7 compliant)
    
        This method implements asynchronous axis movement with variable rate support
        for applications like satellite tracking that require custom tracking rates
        on both RA and Dec axes simultaneously.
    
        Args:
            axis: TelescopeAxes.axisPrimary (RA) or TelescopeAxes.axisSecondary (Dec)
            rate: Rate in degrees per second
                - Positive values: East (RA) or North (Dec)
                - Negative values: West (RA) or South (Dec)
                - Zero: Stop movement
                - Range: Typically 0.0 to MaxRate (mount-dependent, usually ~2-4°/sec)
    
        Returns:
            None (method is asynchronous)
    
        Notes:
            - Movement continues until rate is changed or stopped
            - Both axes can be commanded simultaneously for satellite tracking
            - OnStepX commands: :RAn.n# (RA rate), :REn.n# (Dec rate)
            - Movement direction set by :Me#/:Mw# (RA) or :Mn#/:Ms# (Dec)
        """
        if not self.is_connected:
            return
    
        if axis == TelescopeAxes.axisPrimary:  # RA axis
            self._move_ra_axis(rate)
        elif axis == TelescopeAxes.axisSecondary:  # Dec axis
            self._move_dec_axis(rate)
        else:
            print(f"Invalid axis: {axis}")

    def _move_ra_axis(self, rate):
        """
        Move RA axis at specified rate
    
        Args:
            rate: Rate in degrees/second (positive=East, negative=West, 0=stop)
        """
        if rate == 0:
            # Stop RA movement
            self.send_command(':Qe#')
            self.send_command(':Qw#')
            return
    
        # Set variable rate in degrees/second
        # OnStepX :RAn.n# command sets RA axis guide rate
        abs_rate = abs(rate)
        response = self.send_command(f':RA{abs_rate:.4f}#')
    
        # Check if command was accepted
        if response == '0':
            print(f"⚠ Warning: RA rate {abs_rate:.4f}°/s may exceed mount limits")
    
        # Start movement in appropriate direction
        if rate > 0:
            # Move East (positive RA direction)
            self.send_command(':Me#')
        else:
            # Move West (negative RA direction)
            self.send_command(':Mw#')

    def _move_dec_axis(self, rate):
        """
        Move Dec axis at specified rate
    
        Args:
            rate: Rate in degrees/second (positive=North, negative=South, 0=stop)
        """
        if rate == 0:
            # Stop Dec movement
            self.send_command(':Qn#')
            self.send_command(':Qs#')
            return
    
        # Set variable rate in degrees/second
        # OnStepX :REn.n# command sets Dec axis guide rate
        abs_rate = abs(rate)
        response = self.send_command(f':RE{abs_rate:.4f}#')
    
        # Check if command was accepted
        if response == '0':
            print(f"⚠ Warning: Dec rate {abs_rate:.4f}°/s may exceed mount limits")
    
        # Start movement in appropriate direction
        if rate > 0:
            # Move North (positive Dec direction)
            self.send_command(':Mn#')
        else:
            # Move South (negative Dec direction)
            self.send_command(':Ms#')

    def move_axis_tracking_rate(self, axis, tracking_rate, multiplier=1.0):
        """
        Move axis at specified tracking rate
    
        Args:
            axis: TelescopeAxes.axisPrimary or TelescopeAxes.axisSecondary
            tracking_rate: One of TrackingRate constants (SIDEREAL, SOLAR, LUNAR, KING)
            multiplier: Optional multiplier (default 1.0)
                    Positive/negative for direction
    
        Examples:
            # Track at sidereal rate
            telescope.move_axis_tracking_rate(axis, TrackingRate.SIDEREAL)
        
            # Track at 2× solar rate (east)
            telescope.move_axis_tracking_rate(axis, TrackingRate.SOLAR, 2.0)
        
            # Track at lunar rate (west)
            telescope.move_axis_tracking_rate(axis, TrackingRate.LUNAR, -1.0)
        
            # Track at King rate
            telescope.move_axis_tracking_rate(axis, TrackingRate.KING)
        """
        rate_deg_per_sec = tracking_rate * multiplier
        self.move_axis(axis, rate_deg_per_sec)

    def move_axis_sidereal_rate(self, axis, sidereal_multiple):
        """
        Move axis at sidereal rate multiple
    
        Args:
            axis: TelescopeAxes.axisPrimary or TelescopeAxes.axisSecondary
            sidereal_multiple: Multiple of sidereal rate
                            Positive/negative for direction
    
        Examples:
            # Move at guide rate (1× sidereal)
            telescope.move_axis_sidereal_rate(axis, 1.0)
        
            # Move at center rate (8× sidereal)
            telescope.move_axis_sidereal_rate(axis, 8.0)
        
            # Move west at slew rate (24× sidereal)
            telescope.move_axis_sidereal_rate(axis, -24.0)
        """
        rate_deg_per_sec = sidereal_to_deg_per_sec(sidereal_multiple)
        self.move_axis(axis, rate_deg_per_sec)

    def move_axis_solar_rate(self, axis, solar_multiple=1.0):
        """
        Move axis at solar rate multiple
    
        Args:
            axis: TelescopeAxes.axisPrimary or TelescopeAxes.axisSecondary
            solar_multiple: Multiple of solar rate (default 1.0)
        """
        #rate_deg_per_sec = solar_to_deg_per_sec(solar_multiple)
        rate_deg_per_sec = solar_multiple * SOLAR_RATE
        self.move_axis(axis, rate_deg_per_sec)

    def move_axis_lunar_rate(self, axis, lunar_multiple=1.0):
        """
        Move axis at lunar rate multiple
    
        Args:
            axis: TelescopeAxes.axisPrimary or TelescopeAxes.axisSecondary
            lunar_multiple: Multiple of lunar rate (default 1.0)
        """
        #rate_deg_per_sec = lunar_to_deg_per_sec(lunar_multiple)
        rate_deg_per_sec = lunar_multiple * LUNAR_RATE
        self.move_axis(axis, rate_deg_per_sec)

    def move_axis_king_rate(self, axis, king_multiple=1.0):
        """
        Move axis at King rate multiple
    
        Args:
            axis: TelescopeAxes.axisPrimary or TelescopeAxes.axisSecondary
            king_multiple: Multiple of King rate (default 1.0)
        """
        #rate_deg_per_sec = king_to_deg_per_sec(king_multiple)
        rate_deg_per_sec = king_multiple * KING_RATE
        self.move_axis(axis, rate_deg_per_sec)

    # ========================================================================
    # Site methods
    # ========================================================================
    
    def set_site_latitude(self, latitude):
        """Set site latitude"""
        lat_str = helpers.format_dec_degrees(latitude).replace(':', '*')
        self.send_command(f':St{lat_str}#')
        self.site_latitude = latitude
    
    def set_site_longitude(self, longitude):
        """Set site longitude"""
        lon_str = helpers.format_dec_degrees(longitude).replace(':', '*')
        self.send_command(f':Sg{lon_str}#')
        self.site_longitude = longitude
    
    # ========================================================================
    # Action() methods - OnStepX-specific commands
    # ========================================================================
    
    def supported_actions(self):
        """Get list of supported Action() commands"""
        return [
            "SetHighPrecision",
            "GetHighPrecision",
            "SetPECEnabled",
            "GetPECEnabled",
            "GetAlignmentStatus",
            "SetFocusCompensation",
            "GetFocusCompensation",
            "GetFirmwareVersion",
            "SetTrackingCompensation",
            "GetTrackingCompensation",
            "ResetMount",
            "GetMountInfo"
        ]
    
    def execute_action(self, action_name, parameters=""):
        """Execute OnStepX-specific action"""
        action_name = action_name.strip()
        
        # High Precision Mode
        if action_name == "SetHighPrecision":
            enabled = parameters.lower() in ['true', '1', 'yes']
            response = self.send_command(':U#')
            return f"High precision: {response}"
        
        elif action_name == "GetHighPrecision":
            response = self.send_command(':Gu#')
            return f"High precision: {'enabled' if response == '1' else 'disabled'}"
        
        # PEC
        elif action_name == "SetPECEnabled":
            enabled = parameters.lower() in ['true', '1', 'yes']
            if enabled:
                response = self.send_command(':$QZ+#')
            else:
                response = self.send_command(':$QZ-#')
            return f"PEC: {'enabled' if enabled else 'disabled'}"
        
        elif action_name == "GetPECEnabled":
            response = self.send_command(':$QZ?#')
            return f"PEC: {response}"
        
        # Alignment
        elif action_name == "GetAlignmentStatus":
            response = self.send_command(':GW#')
            alignment_map = {
                'A': 'Altazimuth',
                'P': 'Polar',
                'G': 'German Equatorial'
            }
            return f"Alignment: {alignment_map.get(response, 'Unknown')}"
        
        # Focus Compensation
        elif action_name == "SetFocusCompensation":
            enabled = parameters.lower() in ['true', '1', 'yes']
            response = self.send_command(':Fc#')
            return f"Focus compensation toggled"
        
        elif action_name == "GetFocusCompensation":
            response = self.send_command(':FC#')
            return f"Focus compensation: {response}"
        
        # Firmware
        elif action_name == "GetFirmwareVersion":
            product = self.send_command(':GVP#')
            version = self.send_command(':GVN#')
            date = self.send_command(':GVD#')
            time_str = self.send_command(':GVT#')
            return f"{product} v{version} ({date} {time_str})"
        
        # Tracking Compensation
        elif action_name == "SetTrackingCompensation":
            try:
                rate = float(parameters)
                response = self.send_command(f':T{rate:+.2f}#')
                return f"Tracking rate adjusted by {rate} arcsec/sec"
            except ValueError:
                return "Error: Invalid rate parameter"
        
        elif action_name == "GetTrackingCompensation":
            response = self.send_command(':GT#')
            return f"Tracking: {response}"
        
        # Reset
        elif action_name == "ResetMount":
            if parameters.lower() == "confirm":
                response = self.send_command(':$R#')
                return "Mount reset command sent"
            else:
                return "Error: Requires 'confirm' parameter for safety"
        
        # Mount Info
        elif action_name == "GetMountInfo":
            info = []
            info.append(f"Product: {self.send_command(':GVP#')}")
            info.append(f"Firmware: {self.send_command(':GVN#')}")
            info.append(f"RA: {self.get_right_ascension():.4f}h")
            info.append(f"Dec: {self.get_declination():.4f}°")
            info.append(f"Tracking: {'ON' if self.get_tracking() else 'OFF'}")
            info.append(f"Pier Side: {self.get_side_of_pier().name}")
            info.append(f"Latitude: {self.site_latitude:.4f}°")
            info.append(f"Longitude: {self.site_longitude:.4f}°")
            return " | ".join(info)
        
        else:
            return None

    def get_axis_rates(self, axis):
        """
        Get available rates for axis movement (ASCOM compliance)
    
        Args:
            axis: TelescopeAxes.axisPrimary or TelescopeAxes.axisSecondary
    
        Returns:
            List of IRate objects describing available rates
    
        Notes:
            For satellite tracking, we support variable rates from 0 to MaxRate.
            ASCOM clients use this to determine valid rate ranges.
        """
        # Query mount's maximum rate at connection time if not already cached
        if not hasattr(self, '_max_axis_rate'):
            # Default to conservative value if can't query
            # Most mounts: 1-4 degrees/second max
            self._max_axis_rate = 2.0  # degrees/second
    
        # Return rate range
        # ASCOM expects: Minimum, Maximum rates in degrees/second
        return [
            {
                'Minimum': 0.0,
                'Maximum': self._max_axis_rate
            }
        ]

    # ========================================================================
    # Satellite tracking helper methods
    # ========================================================================

    def set_satellite_tracking_rates(self, ra_rate, dec_rate):
        """
        Convenience method for satellite tracking: set both axis rates simultaneously
    
        Args:
            ra_rate: RA rate in degrees/second (positive=East, negative=West)
            dec_rate: Dec rate in degrees/second (positive=North, negative=South)
    
        Example:
            # Track satellite moving east and north
            telescope.set_satellite_tracking_rates(0.5, 0.3)
        
            # Stop both axes
            telescope.set_satellite_tracking_rates(0, 0)
        """
        self.move_axis(TelescopeAxes.axisPrimary, ra_rate)
        self.move_axis(TelescopeAxes.axisSecondary, dec_rate)

    def stop_all_movement(self):
        """
        Emergency stop: halt all axis movement immediately
    
        This stops slewing, guiding, and MoveAxis operations.
        """
        self.send_command(':Q#')  # Stop all movement
        self.send_command(':Qe#')  # Ensure RA stopped
        self.send_command(':Qw#')
        self.send_command(':Qn#')  # Ensure Dec stopped
        self.send_command(':Qs#')

    # ========================================================================
    # Usage examples for satellite tracking
    # ========================================================================

    """
    Example 1: Simple satellite tracking
    -------------------------------------
    # Get satellite position and velocity from tracking software
    ra_rate = 0.35  # degrees/second eastward
    dec_rate = 0.12  # degrees/second northward

    # Command mount to track
    telescope.move_axis(TelescopeAxes.axisPrimary, ra_rate)
    telescope.move_axis(TelescopeAxes.axisSecondary, dec_rate)

    # Update rates as satellite moves (typically every second)
    while tracking:
        new_ra_rate, new_dec_rate = get_satellite_rates()
        telescope.move_axis(TelescopeAxes.axisPrimary, new_ra_rate)
        telescope.move_axis(TelescopeAxes.axisSecondary, new_dec_rate)
        time.sleep(1)

    # Stop tracking
    telescope.move_axis(TelescopeAxes.axisPrimary, 0)
    telescope.move_axis(TelescopeAxes.axisSecondary, 0)
    """

