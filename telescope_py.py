"""
OnStepX Telescope Mount Driver
Implements ASCOM ITelescopeV4 interface
"""

import serial
import serial.tools.list_ports
import time
from threading import Lock
from enum import IntEnum
from datetime import datetime, timezone
import alpaca_helpers as helpers

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
    """OnStepX telescope mount driver"""
    
    def __init__(self, port=None, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
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
        
        # Mount info
        self.site_latitude = 0.0
        self.site_longitude = 0.0
        self.site_elevation = 0.0
        self.alignment_mode = AlignmentModes.algGermanPolar
        self.aperture_area = 0.0
        self.aperture_diameter = 0.0
        self.focal_length = 0.0
        self.equatorial_system = EquatorialCoordinateType.equJ2000
    
    def _find_port(self):
        """Auto-detect OnStepX on USB serial ports"""
        if self.port:
            return self.port
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.device or 'ACM' in port.device:
                return port.device
        
        return '/dev/ttyUSB0'  # Default fallback
    
    def connect(self):
        """Connect to mount"""
        self.is_connecting = True
        try:
            if not self.port:
                self.port = self._find_port()
            
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=2,
                write_timeout=2
            )
            time.sleep(2)  # Allow connection to stabilize
            
            # Test connection
            product = self.send_command(':GVP#')
            if product:
                self.is_connected = True
                print(f"Connected to OnStepX on {self.port}: {product}")
                
                # Get site info
                self._update_site_info()
                return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.is_connected = False
        finally:
            self.is_connecting = False
        
        return False
    
    def disconnect(self):
        """Disconnect from mount"""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.is_connected = False
    
    def send_command(self, command):
        """Send command to mount and return response"""
        if not self.serial or not self.serial.is_open:
            return None
        
        with self.lock:
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
                
                return response.decode('ascii').strip()
            except Exception as e:
                print(f"Command error: {e}")
                return None
    
    def _update_site_info(self):
        """Update site latitude/longitude from mount"""
        try:
            lat_str = self.send_command(':Gt#')
            if lat_str:
                self.site_latitude = helpers.parse_dec_to_degrees(lat_str)
            
            lon_str = self.send_command(':Gg#')
            if lon_str:
                self.site_longitude = helpers.parse_dec_to_degrees(lon_str)
        except:
            pass
    
    # Position methods
    def get_ra(self):
        """Get Right Ascension in decimal hours"""
        response = self.send_command(':GR#')
        if response:
            return helpers.parse_ra_to_hours(response)
        return 0.0
    
    def get_dec(self):
        """Get Declination in decimal degrees"""
        response = self.send_command(':GD#')
        if response:
            return helpers.parse_dec_to_degrees(response)
        return 0.0
    
    def get_altitude(self):
        """Get altitude in degrees"""
        response = self.send_command(':GA#')
        if response:
            return helpers.parse_dec_to_degrees(response)
        return 0.0
    
    def get_azimuth(self):
        """Get azimuth in degrees"""
        response = self.send_command(':GZ#')
        if response:
            return helpers.parse_dec_to_degrees(response)
        return 0.0
    
    def get_sidereal_time(self):
        """Get local sidereal time in hours"""
        response = self.send_command(':GS#')
        if response:
            return helpers.parse_ra_to_hours(response)
        return 0.0
    
    def get_pier_side(self):
        """Get pier side"""
        response = self.send_command(':Gm#')
        if response and response in ['E', 'W']:
            return PierSide.pierEast if response == 'E' else PierSide.pierWest
        return PierSide.pierUnknown
    
    def is_slewing(self):
        """Check if mount is slewing"""
        # OnStepX doesn't provide reliable slewing status
        # This is a limitation - return False for now
        return False
    
    # Tracking methods
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
    
    # Slewing methods
    def slew_to_coords(self, ra_hours, dec_degrees):
        """Slew to RA/Dec coordinates"""
        ra_str = helpers.format_ra_hours(ra_hours)
        dec_str = helpers.format_dec_degrees(dec_degrees).replace(':', '*')
        
        self.send_command(f':Sr{ra_str}#')
        self.send_command(f':Sd{dec_str}#')
        
        response = self.send_command(':MS#')
        return response == '0'
    
    def slew_to_altaz(self, azimuth, altitude):
        """Slew to Alt/Az coordinates"""
        az_str = helpers.format_dec_degrees(azimuth).replace(':', '*')
        alt_str = helpers.format_dec_degrees(altitude).replace(':', '*')
        
        self.send_command(f':Sz{az_str}#')
        self.send_command(f':Sa{alt_str}#')
        
        response = self.send_command(':MA#')
        return response == '0'
    
    def stop_slew(self):
        """Stop all slewing"""
        self.send_command(':Q#')
    
    # Sync methods
    def sync_to_coords(self, ra_hours, dec_degrees):
        """Sync mount to coordinates"""
        ra_str = helpers.format_ra_hours(ra_hours)
        dec_str = helpers.format_dec_degrees(dec_degrees).replace(':', '*')
        
        self.send_command(f':Sr{ra_str}#')
        self.send_command(f':Sd{dec_str}#')
        self.send_command(':CM#')
    
    def sync_to_altaz(self, azimuth, altitude):
        """Sync to Alt/Az coordinates"""
        az_str = helpers.format_dec_degrees(azimuth).replace(':', '*')
        alt_str = helpers.format_dec_degrees(altitude).replace(':', '*')
        
        self.send_command(f':Sz{az_str}#')
        self.send_command(f':Sa{alt_str}#')
        self.send_command(':CM#')
    
    # Park methods
    def get_at_park(self):
        """Check if mount is parked"""
        response = self.send_command(':GU#')
        return response == 'P' if response else False
    
    def get_at_home(self):
        """Check if mount is at home"""
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
    
    def set_park(self):
        """Set current position as park"""
        self.send_command(':hQ#')
    
    # Pulse guide methods
    def pulse_guide(self, direction, duration_ms):
        """Pulse guide in specified direction"""
        dir_cmds = {
            GuideDirections.guideNorth: 'Mgn',
            GuideDirections.guideSouth: 'Mgs',
            GuideDirections.guideEast: 'Mge',
            GuideDirections.guideWest: 'Mgw'
        }
        
        if direction not in dir_cmds:
            return False
        
        cmd = f':{dir_cmds[direction]}{duration_ms:04d}#'
        self.send_command(cmd)
        
        self.pulse_guiding = True
        self.pulse_guide_end_time = time.time() + (duration_ms / 1000.0)
        return True
    
    def is_pulse_guiding(self):
        """Check if pulse guiding is active"""
        if self.pulse_guiding and time.time() >= self.pulse_guide_end_time:
            self.pulse_guiding = False
        return self.pulse_guiding
    
    # Move axis methods
    def move_axis(self, axis, rate):
        """Move axis at specified rate"""
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
    
    # Site methods
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
    
    # Utility methods
    def destination_side_of_pier(self, ra_hours, dec_degrees):
        """Calculate destination pier side"""
        lst = self.get_sidereal_time()
        ha = lst - ra_hours
        
        if ha < 0:
            ha += 24
        
        return PierSide.pierEast if ha < 12 else PierSide.pierWest
