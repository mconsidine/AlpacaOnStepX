#!/usr/bin/env python3
"""
OnStepX Alpaca Bridge - Main Server
Complete implementation with Telescope + 2 Cameras + FilterWheel + Focuser
"""

from flask import Flask, request
import sys
import base64
import numpy as np
import signal

# Import configuration and helpers
import config
import alpaca_helpers as helpers

# Import device drivers
from telescope import OnStepXMount
from camera_zwo import ZWOCamera, ZWO_AVAILABLE
from camera_touptek import ToupTekCamera, TOUPTEK_AVAILABLE
from filterwheel import create_filterwheel
from focuser import create_focuser

# Import discovery service
from alpaca_discovery import AlpacaDiscovery

# Initialize Flask app
app = Flask(__name__)

# Global device instances
telescope = None
camera_zwo = None
camera_touptek = None
filterwheel = None
focuser = None
discovery = None

def init_devices():
    """Initialize all configured devices"""
    global telescope, camera_zwo, camera_touptek, filterwheel, focuser
    
    print("Initializing devices...")
    
    # Initialize telescope
    if config.DEVICES['telescope']['enabled']:
        try:
            # Get connection parameters based on type
            conn_type = config.TELESCOPE_CONFIG['connection_type']
            
            if conn_type == 'network':
                telescope = OnStepXMount(
                    connection_type='network',
                    host=config.TELESCOPE_CONFIG['network']['host'],
                    port=config.TELESCOPE_CONFIG['network']['port']
                )
                print(f"[Telescope] Configured for NETWORK: {config.TELESCOPE_CONFIG['network']['host']}:{config.TELESCOPE_CONFIG['network']['port']}")
            else:  # serial
                telescope = OnStepXMount(
                    connection_type='serial',
                    port=config.TELESCOPE_CONFIG['serial']['port'],
                    baudrate=config.TELESCOPE_CONFIG['serial']['baudrate']
                )
                print(f"[Telescope] Configured for SERIAL: {config.TELESCOPE_CONFIG['serial']['port']}")
            
            app.telescope = telescope
            print("✓ Telescope initialized")
        except Exception as e:
            print(f"✗ Telescope initialization failed: {e}")
    
    # Initialize ZWO camera
    if config.DEVICES['camera_zwo']['enabled'] and ZWO_AVAILABLE:
        try:
            camera_zwo = ZWOCamera(
                camera_id=config.DEVICES['camera_zwo']['camera_id'],
                sdk_path=config.CAMERA_CONFIG['zwo_sdk_path']
            )
            app.camera_zwo = camera_zwo
            print("✓ ZWO camera initialized")
        except Exception as e:
            print(f"✗ ZWO camera initialization failed: {e}")
    
    # Initialize ToupTek camera
    if config.DEVICES['camera_touptek']['enabled'] and TOUPTEK_AVAILABLE:
        try:
            camera_touptek = ToupTekCamera(
                camera_id=config.DEVICES['camera_touptek']['camera_id']
            )
            app.camera_touptek = camera_touptek
            print("✓ ToupTek camera initialized")
        except Exception as e:
            print(f"✗ ToupTek camera initialization failed: {e}")
    
    # Initialize filter wheel
    if config.DEVICES['filterwheel']['enabled']:
        try:
            mode = config.FILTERWHEEL_CONFIG['mode']
            print(f"[FilterWheel] Mode: {mode}")
            
            # Get parameters based on mode
            wheel_id = config.FILTERWHEEL_CONFIG.get('zwo', {}).get('wheel_id', 0)
            slot_count = config.FILTERWHEEL_CONFIG.get('mock', {}).get('slot_count', 8)
            
            # Create filterwheel with correct parameters
            filterwheel = create_filterwheel(
                mode=mode,
                wheel_id=wheel_id,
                slot_count=slot_count
            )
            
            # Apply custom filter names and offsets if configured
            if config.FILTERWHEEL_CONFIG.get('filter_names'):
                filterwheel.filter_names = config.FILTERWHEEL_CONFIG['filter_names']
            if config.FILTERWHEEL_CONFIG.get('focus_offsets'):
                filterwheel.focus_offsets = config.FILTERWHEEL_CONFIG['focus_offsets']
            
            app.filterwheel = filterwheel
            print("✓ Filter wheel initialized")
            if hasattr(filterwheel, 'slot_count'):
                print(f"  Slots: {filterwheel.slot_count}")
                if hasattr(filterwheel, 'filter_names'):
                    print(f"  Filters: {', '.join(filterwheel.filter_names[:filterwheel.slot_count])}")
        except Exception as e:
            print(f"✗ FilterWheel: {e}")
    
    # Initialize focuser
    if config.DEVICES['focuser']['enabled']:
        try:
            mode = config.FOCUSER_CONFIG['mode']
            print(f"[Focuser] Mode: {mode}")
            
            # Get parameters based on mode
            focuser_id = config.FOCUSER_CONFIG.get('zwo', {}).get('focuser_id', 0)
            max_position = config.FOCUSER_CONFIG.get('mock', {}).get('max_position', 100000)
            
            # Create focuser with correct parameters
            focuser = create_focuser(
                mode=mode,
                focuser_id=focuser_id,
                max_position=max_position
            )
            app.focuser = focuser
            print("✓ Focuser initialized")
            if hasattr(focuser, 'max_position'):
                print(f"  Max position: {focuser.max_position} steps")
                if hasattr(focuser, 'step_size'):
                    print(f"  Step size: {focuser.step_size} microns")
        except Exception as e:
            print(f"✗ Focuser: {e}")

def get_current_devices():
    """
    Get list of currently enabled devices for discovery response
    Used by discovery service to report available devices
    """
    devices = []
    
    if telescope and config.DEVICES['telescope']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['telescope']['name'],
            "DeviceType": "Telescope",
            "DeviceNumber": config.DEVICES['telescope']['device_number'],
            "UniqueID": config.DEVICES['telescope']['unique_id']
        })
    
    if camera_zwo and config.DEVICES['camera_zwo']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['camera_zwo']['name'],
            "DeviceType": "Camera",
            "DeviceNumber": config.DEVICES['camera_zwo']['device_number'],
            "UniqueID": config.DEVICES['camera_zwo']['unique_id']
        })
    
    if camera_touptek and config.DEVICES['camera_touptek']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['camera_touptek']['name'],
            "DeviceType": "Camera",
            "DeviceNumber": config.DEVICES['camera_touptek']['device_number'],
            "UniqueID": config.DEVICES['camera_touptek']['unique_id']
        })
    
    if filterwheel and config.DEVICES['filterwheel']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['filterwheel']['name'],
            "DeviceType": "FilterWheel",
            "DeviceNumber": config.DEVICES['filterwheel']['device_number'],
            "UniqueID": config.DEVICES['filterwheel']['unique_id']
        })
    
    if focuser and config.DEVICES['focuser']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['focuser']['name'],
            "DeviceType": "Focuser",
            "DeviceNumber": config.DEVICES['focuser']['device_number'],
            "UniqueID": config.DEVICES['focuser']['unique_id']
        })
    
    return devices


def get_camera(device_number):
    """Get camera by device number"""
    if device_number == 0 and camera_zwo:
        return camera_zwo
    elif device_number == 1 and camera_touptek:
        return camera_touptek
    return None

# ============================================================================
# MANAGEMENT API
# ============================================================================

@app.route('/management/apiversions')
def api_versions():
    """Get supported API versions"""
    return helpers.alpaca_response([1])

@app.route('/management/v1/description')
def server_description():
    """Get server description"""
    return helpers.alpaca_response(config.SERVER_INFO)

@app.route('/management/v1/configureddevices')
def configured_devices():
    """Get list of configured devices"""
    devices = []
    
    if telescope and config.DEVICES['telescope']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['telescope']['name'],
            "DeviceType": "Telescope",
            "DeviceNumber": config.DEVICES['telescope']['device_number'],
            "UniqueID": config.DEVICES['telescope']['unique_id']
        })
    
    if camera_zwo and config.DEVICES['camera_zwo']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['camera_zwo']['name'],
            "DeviceType": "Camera",
            "DeviceNumber": config.DEVICES['camera_zwo']['device_number'],
            "UniqueID": config.DEVICES['camera_zwo']['unique_id']
        })
    
    if camera_touptek and config.DEVICES['camera_touptek']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['camera_touptek']['name'],
            "DeviceType": "Camera",
            "DeviceNumber": config.DEVICES['camera_touptek']['device_number'],
            "UniqueID": config.DEVICES['camera_touptek']['unique_id']
        })
    
    if filterwheel and config.DEVICES['filterwheel']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['filterwheel']['name'],
            "DeviceType": "FilterWheel",
            "DeviceNumber": config.DEVICES['filterwheel']['device_number'],
            "UniqueID": config.DEVICES['filterwheel']['unique_id']
        })
    
    if focuser and config.DEVICES['focuser']['enabled']:
        devices.append({
            "DeviceName": config.DEVICES['focuser']['name'],
            "DeviceType": "Focuser",
            "DeviceNumber": config.DEVICES['focuser']['device_number'],
            "UniqueID": config.DEVICES['focuser']['unique_id']
        })
    
    return helpers.alpaca_response(devices)

# ============================================================================
# COMMON DEVICE API (ALL DEVICES)
# ============================================================================

# Telescope common endpoints
@app.route('/api/v1/telescope/0/connected', methods=['GET', 'PUT'])
def telescope_connected():
    """Get/set telescope connection"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.is_connected)
    else:
        connected = helpers.get_form_value('Connected', False, bool)
        if connected:
            telescope.connect()
        else:
            telescope.disconnect()
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/name')
def telescope_name():
    """Get telescope name"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(config.DEVICES['telescope']['name'])

@app.route('/api/v1/telescope/0/description')
def telescope_description():
    """Get telescope description"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response("OnStepX telescope mount via Alpaca")

@app.route('/api/v1/telescope/0/driverinfo')
def telescope_driverinfo():
    """Get telescope driver info"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response("OnStepX Alpaca Bridge v1.0")

@app.route('/api/v1/telescope/0/driverversion')
def telescope_driverversion():
    """Get telescope driver version"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response("1.0")

@app.route('/api/v1/telescope/0/interfaceversion')
def telescope_interfaceversion():
    """Get telescope interface version"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(4)

@app.route('/api/v1/telescope/0/supportedactions')
def telescope_supportedactions():
    """Get list of supported actions"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response([])

# ============================================================================
# TELESCOPE API - COORDINATES
# ============================================================================

@app.route('/api/v1/telescope/0/rightascension')
@helpers.require_connected('telescope')
def telescope_rightascension():
    """Get current RA"""
    return helpers.alpaca_response(telescope.right_ascension)

@app.route('/api/v1/telescope/0/declination')
@helpers.require_connected('telescope')
def telescope_declination():
    """Get current Dec"""
    return helpers.alpaca_response(telescope.declination)

@app.route('/api/v1/telescope/0/azimuth')
@helpers.require_connected('telescope')
def telescope_azimuth():
    """Get current azimuth"""
    return helpers.alpaca_response(telescope.azimuth)

@app.route('/api/v1/telescope/0/altitude')
@helpers.require_connected('telescope')
def telescope_altitude():
    """Get current altitude"""
    return helpers.alpaca_response(telescope.altitude)

# ============================================================================
# TELESCOPE API - SLEWING
# ============================================================================

@app.route('/api/v1/telescope/0/slewing')
@helpers.require_connected('telescope')
def telescope_slewing():
    """Get slewing status"""
    return helpers.alpaca_response(telescope.is_slewing())

@app.route('/api/v1/telescope/0/slewtocoordinates', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_slewtocoordinates():
    """Slew to coordinates"""
    ra = helpers.get_form_value('RightAscension', 0.0, float)
    dec = helpers.get_form_value('Declination', 0.0, float)
    telescope.slew_to_coords(ra, dec)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/slewtoaltaz', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_slewtoaltaz():
    """Slew to alt/az"""
    azimuth = helpers.get_form_value('Azimuth', 0.0, float)
    altitude = helpers.get_form_value('Altitude', 0.0, float)
    telescope.slew_to_altaz(azimuth, altitude)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/slewtotarget', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_slewtotarget():
    """Slew to target"""
    telescope.slew_to_coords(telescope.target_ra, telescope.target_dec)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/abortslew', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_abortslew():
    """Abort slew"""
    telescope.abort_slew()
    return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - TRACKING
# ============================================================================

@app.route('/api/v1/telescope/0/tracking', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_tracking():
    """Get/set tracking"""
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.tracking)
    else:
        tracking = helpers.get_form_value('Tracking', True, bool)
        telescope.set_tracking(tracking)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/trackingrate', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_trackingrate():
    """Get/set tracking rate"""
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.tracking_rate)
    else:
        rate = helpers.get_form_value('TrackingRate', 0, int)
        telescope.set_tracking_rate(rate)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/trackingrates')
def telescope_trackingrates():
    """Get available tracking rates"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response([0, 1, 2, 3])  # Sidereal, Lunar, Solar, King

# ============================================================================
# TELESCOPE API - PARK
# ============================================================================

@app.route('/api/v1/telescope/0/atpark')
@helpers.require_connected('telescope')
def telescope_atpark():
    """Get park status"""
    return helpers.alpaca_response(telescope.at_park)

@app.route('/api/v1/telescope/0/park', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_park():
    """Park telescope"""
    telescope.park()
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/unpark', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_unpark():
    """Unpark telescope"""
    telescope.unpark()
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/setpark', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_setpark():
    """Set park position"""
    telescope.set_park()
    return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - TARGET
# ============================================================================

@app.route('/api/v1/telescope/0/targetrightascension', methods=['GET', 'PUT'])
def telescope_targetrightascension():
    """Get/set target RA"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.target_ra)
    else:
        telescope.target_ra = helpers.get_form_value('TargetRightAscension', 0.0, float)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/targetdeclination', methods=['GET', 'PUT'])
def telescope_targetdeclination():
    """Get/set target Dec"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.target_dec)
    else:
        telescope.target_dec = helpers.get_form_value('TargetDeclination', 0.0, float)
        return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - SYNC
# ============================================================================

@app.route('/api/v1/telescope/0/synctocoordinates', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_synctocoordinates():
    """Sync to coordinates"""
    ra = helpers.get_form_value('RightAscension', 0.0, float)
    dec = helpers.get_form_value('Declination', 0.0, float)
    telescope.sync_to_coords(ra, dec)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/synctoaltaz', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_synctoaltaz():
    """Sync to alt/az"""
    azimuth = helpers.get_form_value('Azimuth', 0.0, float)
    altitude = helpers.get_form_value('Altitude', 0.0, float)
    telescope.sync_to_altaz(azimuth, altitude)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/synctotarget', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_synctotarget():
    """Sync to target"""
    telescope.sync_to_coords(telescope.target_ra, telescope.target_dec)
    return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - SITE CONFIGURATION
# ============================================================================

@app.route('/api/v1/telescope/0/sitelatitude', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_sitelatitude():
    """Get/set site latitude"""
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.site_latitude)
    else:
        lat = helpers.get_form_value('SiteLatitude', 0.0, float)
        telescope.set_site_latitude(lat)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/sitelongitude', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_sitelongitude():
    """Get/set site longitude"""
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.site_longitude)
    else:
        lon = helpers.get_form_value('SiteLongitude', 0.0, float)
        telescope.set_site_longitude(lon)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/siteelevation', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_siteelevation():
    """Get/set site elevation"""
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.site_elevation)
    else:
        elev = helpers.get_form_value('SiteElevation', 0.0, float)
        telescope.set_site_elevation(elev)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/canpulseguide')
def telescope_canpulseguide():
    """Pulse guide capability"""
    return helpers.alpaca_response(True)
    
# ============================================================================
# TELESCOPE API - CAPABILITIES
# ============================================================================

@app.route('/api/v1/telescope/0/canpark')
def telescope_canpark():
    """Can telescope park"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canslew')
def telescope_canslew():
    """Can telescope slew"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canslewaltaz')
def telescope_canslewaltaz():
    """Can telescope slew alt/az"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/cansync')
def telescope_cansync():
    """Can telescope sync"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/cansettracking')
def telescope_cansettracking():
    """Can set tracking"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/moveaxis', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_moveaxis():
    """Move telescope axis at specified rate"""
    axis = helpers.get_form_value('Axis', 0, int)
    rate = helpers.get_form_value('Rate', 0.0, float)
    
    # Validate axis
    if axis not in [0, 1]:  # 0=Primary/RA, 1=Secondary/Dec
        return helpers.alpaca_error(
            config.ASCOM_ERROR_CODES['INVALID_VALUE'],
            f"Invalid axis: {axis}"
        )
    
    # Move axis
    telescope.move_axis(axis, rate)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/axisrates')
@helpers.require_connected('telescope')
def telescope_axisrates():
    """Get available rates for specified axis"""
    axis = helpers.get_form_value('Axis', 0, int)
    
    rates = telescope.get_axis_rates(axis)
    return helpers.alpaca_response(rates)

@app.route('/api/v1/telescope/0/canmoveaxis', methods=['GET'])
def telescope_canmoveaxis():
    """Check if MoveAxis is supported"""
    axis = helpers.get_form_value('Axis', 0, int)
    
    # Both axes supported
    can_move = axis in [0, 1]
    return helpers.alpaca_response(can_move)
    
# ============================================================================
# CAMERA API - COMMON
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/connected', methods=['GET', 'PUT'])
def camera_connected(device_number):
    """Get/set camera connection"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.is_connected)
    else:
        connected = helpers.get_form_value('Connected', False, bool)
        if connected:
            camera.connect()
        else:
            camera.disconnect()
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/name')
def camera_name(device_number):
    """Get camera name"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not available")
    return helpers.alpaca_response(camera.camera_name)

@app.route('/api/v1/camera/<int:device_number>/description')
def camera_description(device_number):
    """Get camera description"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not available")
    return helpers.alpaca_response(camera.description)

@app.route('/api/v1/camera/<int:device_number>/driverinfo')
def camera_driverinfo(device_number):
    """Get camera driver info"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not available")
    return helpers.alpaca_response(camera.driver_info)

@app.route('/api/v1/camera/<int:device_number>/driverversion')
def camera_driverversion(device_number):
    """Get camera driver version"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not available")
    return helpers.alpaca_response(camera.driver_version)

@app.route('/api/v1/camera/<int:device_number>/interfaceversion')
def camera_interfaceversion(device_number):
    """Get camera interface version"""
    return helpers.alpaca_response(4)

# ============================================================================
# CAMERA API - PROPERTIES
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/camerastate')
def camera_camerastate(device_number):
    """Get camera state"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.camera_state)

@app.route('/api/v1/camera/<int:device_number>/cameraxsize')
def camera_cameraxsize(device_number):
    """Get camera X size"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.camera_xsize)

@app.route('/api/v1/camera/<int:device_number>/cameraysize')
def camera_cameraysize(device_number):
    """Get camera Y size"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.camera_ysize)

@app.route('/api/v1/camera/<int:device_number>/pixelsizex')
def camera_pixelsizex(device_number):
    """Get pixel size X"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.pixel_size_x)

@app.route('/api/v1/camera/<int:device_number>/pixelsizey')
def camera_pixelsizey(device_number):
    """Get pixel size Y"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.pixel_size_y)

@app.route('/api/v1/camera/<int:device_number>/sensortype')
def camera_sensortype(device_number):
    """Get sensor type"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.sensor_type)

# ============================================================================
# CAMERA API - BINNING
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/binx', methods=['GET', 'PUT'])
def camera_binx(device_number):
    """Get/set bin X"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.bin_x)
    else:
        bin_x = helpers.get_form_value('BinX', 1, int)
        if bin_x < 1 or bin_x > camera.max_bin_x:
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['INVALID_VALUE'], f"BinX must be 1-{camera.max_bin_x}")
        camera.bin_x = bin_x
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/biny', methods=['GET', 'PUT'])
def camera_biny(device_number):
    """Get/set bin Y"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.bin_y)
    else:
        bin_y = helpers.get_form_value('BinY', 1, int)
        if bin_y < 1 or bin_y > camera.max_bin_y:
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['INVALID_VALUE'], f"BinY must be 1-{camera.max_bin_y}")
        camera.bin_y = bin_y
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/maxbinx')
def camera_maxbinx(device_number):
    """Get max bin X"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.max_bin_x)

@app.route('/api/v1/camera/<int:device_number>/maxbiny')
def camera_maxbiny(device_number):
    """Get max bin Y"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.max_bin_y)

# ============================================================================
# CAMERA API - ROI
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/startx', methods=['GET', 'PUT'])
def camera_startx(device_number):
    """Get/set start X"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.start_x)
    else:
        camera.start_x = helpers.get_form_value('StartX', 0, int)
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/starty', methods=['GET', 'PUT'])
def camera_starty(device_number):
    """Get/set start Y"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.start_y)
    else:
        camera.start_y = helpers.get_form_value('StartY', 0, int)
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/numx', methods=['GET', 'PUT'])
def camera_numx(device_number):
    """Get/set num X"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.num_x)
    else:
        camera.num_x = helpers.get_form_value('NumX', camera.camera_xsize, int)
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/numy', methods=['GET', 'PUT'])
def camera_numy(device_number):
    """Get/set num Y"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.num_y)
    else:
        camera.num_y = helpers.get_form_value('NumY', camera.camera_ysize, int)
        return helpers.alpaca_response(None)

# ============================================================================
# CAMERA API - EXPOSURE
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/startexposure', methods=['PUT'])
def camera_startexposure(device_number):
    """Start exposure"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    duration = helpers.get_form_value('Duration', 1.0, float)
    is_light = helpers.get_form_value('Light', True, bool)
    
    try:
        camera.start_exposure(duration, is_light)
        return helpers.alpaca_response(None)
    except Exception as e:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], str(e))

@app.route('/api/v1/camera/<int:device_number>/abortexposure', methods=['PUT'])
def camera_abortexposure(device_number):
    """Abort exposure"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    camera.abort_exposure()
    return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/stopexposure', methods=['PUT'])
def camera_stopexposure(device_number):
    """Stop exposure"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    camera.stop_exposure()
    return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/imageready')
def camera_imageready(device_number):
    """Get image ready status"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.image_ready)

@app.route('/api/v1/camera/<int:device_number>/percentcompleted')
def camera_percentcompleted(device_number):
    """Get exposure percent completed"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.percent_completed)

# ============================================================================
# CAMERA API - IMAGE DATA
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/imagearray')
def camera_imagearray(device_number):
    """Get image as 2D array (JSON)"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    try:
        img = camera.get_image_array()
        img_list = img.tolist()
        return helpers.alpaca_response(img_list)
    except Exception as e:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], str(e))

@app.route('/api/v1/camera/<int:device_number>/imagearrayvariant')
def camera_imagearrayvariant(device_number):
    """Get image as Base64 encoded string"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    try:
        img = camera.get_image_array()
        img_bytes = img.tobytes()
        img_b64 = base64.b64encode(img_bytes).decode('ascii')
        
        result = {
            'Type': 'UInt16',
            'Rank': 2,
            'Data': img_b64,
            'Width': img.shape[1],
            'Height': img.shape[0]
        }
        return helpers.alpaca_response(result)
    except Exception as e:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], str(e))

# ============================================================================
# CAMERA API - GAIN & OFFSET
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/gain', methods=['GET', 'PUT'])
def camera_gain(device_number):
    """Get/set gain"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.gain)
    else:
        gain = helpers.get_form_value('Gain', 0, int)
        camera.gain = gain
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/gainmin')
def camera_gainmin(device_number):
    """Get min gain"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.gain_min)

@app.route('/api/v1/camera/<int:device_number>/gainmax')
def camera_gainmax(device_number):
    """Get max gain"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.gain_max)

@app.route('/api/v1/camera/<int:device_number>/offset', methods=['GET', 'PUT'])
def camera_offset(device_number):
    """Get/set offset"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.offset)
    else:
        offset = helpers.get_form_value('Offset', 0, int)
        camera.offset = offset
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/offsetmin')
def camera_offsetmin(device_number):
    """Get min offset"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.offset_min)

@app.route('/api/v1/camera/<int:device_number>/offsetmax')
def camera_offsetmax(device_number):
    """Get max offset"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.offset_max)

# ============================================================================
# CAMERA API - TEMPERATURE
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/ccdtemperature')
def camera_ccdtemperature(device_number):
    """Get CCD temperature"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.ccd_temperature)

@app.route('/api/v1/camera/<int:device_number>/cooleron', methods=['GET', 'PUT'])
def camera_cooleron(device_number):
    """Get/set cooler on"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.cooler_on)
    else:
        if not camera.can_set_ccd_temperature:
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Cooler not supported")
        
        cooler_on = helpers.get_form_value('CoolerOn', False, bool)
        camera.set_cooler(cooler_on)
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/coolerpower')
def camera_coolerpower(device_number):
    """Get cooler power"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.cooler_power)

@app.route('/api/v1/camera/<int:device_number>/setccdtemperature', methods=['GET', 'PUT'])
def camera_setccdtemperature(device_number):
    """Get/set target CCD temperature"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.set_ccd_temperature)
    else:
        if not camera.can_set_ccd_temperature:
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Temperature control not supported")
        
        temp = helpers.get_form_value('SetCCDTemperature', 0.0, float)
        camera.set_target_temperature(temp)
        return helpers.alpaca_response(None)

# ============================================================================
# CAMERA API - CAPABILITIES
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/canabortexposure')
def camera_canabortexposure(device_number):
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")
    return helpers.alpaca_response(camera.can_abort_exposure)

@app.route('/api/v1/camera/<int:device_number>/canstopexposure')
def camera_canstopexposure(device_number):
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")
    return helpers.alpaca_response(camera.can_stop_exposure)

@app.route('/api/v1/camera/<int:device_number>/cansetccdtemperature')
def camera_cansetccdtemperature(device_number):
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")
    return helpers.alpaca_response(camera.can_set_ccd_temperature)

# ============================================================================
# FILTERWHEEL API
# ============================================================================

@app.route('/api/v1/filterwheel/0/connected', methods=['GET', 'PUT'])
def filterwheel_connected():
    """Get/set filter wheel connection"""
    if not filterwheel:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "FilterWheel not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(filterwheel.is_connected)
    else:
        connected = helpers.get_form_value('Connected', False, bool)
        if connected:
            filterwheel.connect()
        else:
            filterwheel.disconnect()
        return helpers.alpaca_response(None)

@app.route('/api/v1/filterwheel/0/name')
def filterwheel_name():
    """Get filter wheel name"""
    if not filterwheel:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "FilterWheel not available")
    return helpers.alpaca_response(config.DEVICES['filterwheel']['name'])

@app.route('/api/v1/filterwheel/0/description')
def filterwheel_description():
    """Get filter wheel description"""
    if not filterwheel:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "FilterWheel not available")
    return helpers.alpaca_response("ZWO Electronic Filter Wheel")

@app.route('/api/v1/filterwheel/0/position', methods=['GET', 'PUT'])
@helpers.require_connected('filterwheel')
def filterwheel_position():
    """Get/set filter position"""
    if request.method == 'GET':
        return helpers.alpaca_response(filterwheel.get_position())
    else:
        position = helpers.get_form_value('Position', 0, int)
        filterwheel.set_position(position)
        return helpers.alpaca_response(None)

@app.route('/api/v1/filterwheel/0/names')
@helpers.require_connected('filterwheel')
def filterwheel_names():
    """Get filter names"""
    names = [filterwheel.get_filter_name(i) for i in range(filterwheel.slot_count)]
    return helpers.alpaca_response(names)

@app.route('/api/v1/filterwheel/0/focusoffsets')
@helpers.require_connected('filterwheel')
def filterwheel_focusoffsets():
    """Get focus offsets"""
    offsets = [filterwheel.get_focus_offset(i) for i in range(filterwheel.slot_count)]
    return helpers.alpaca_response(offsets)

# ============================================================================
# FOCUSER API
# ============================================================================

@app.route('/api/v1/focuser/0/connected', methods=['GET', 'PUT'])
def focuser_connected():
    """Get/set focuser connection"""
    if not focuser:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Focuser not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(focuser.is_connected)
    else:
        connected = helpers.get_form_value('Connected', False, bool)
        if connected:
            focuser.connect()
        else:
            focuser.disconnect()
        return helpers.alpaca_response(None)

@app.route('/api/v1/focuser/0/name')
def focuser_name():
    """Get focuser name"""
    if not focuser:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Focuser not available")
    return helpers.alpaca_response(config.DEVICES['focuser']['name'])

@app.route('/api/v1/focuser/0/description')
def focuser_description():
    """Get focuser description"""
    if not focuser:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Focuser not available")
    return helpers.alpaca_response("ZWO Electronic Auto Focuser")

@app.route('/api/v1/focuser/0/absolute', methods=['GET'])
def focuser_absolute():
    """Is focuser absolute"""
    if not focuser:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Focuser not available")
    return helpers.alpaca_response(True)

@app.route('/api/v1/focuser/0/ismoving')
@helpers.require_connected('focuser')
def focuser_ismoving():
    """Is focuser moving"""
    return helpers.alpaca_response(focuser.is_moving())

@app.route('/api/v1/focuser/0/maxstep')
@helpers.require_connected('focuser')
def focuser_maxstep():
    """Get max step"""
    return helpers.alpaca_response(focuser.max_position)

@app.route('/api/v1/focuser/0/position')
@helpers.require_connected('focuser')
def focuser_position():
    """Get current position"""
    return helpers.alpaca_response(focuser.get_position())

@app.route('/api/v1/focuser/0/move', methods=['PUT'])
@helpers.require_connected('focuser')
def focuser_move():
    """Move to absolute position"""
    position = helpers.get_form_value('Position', 0, int)
    focuser.move_to(position)
    return helpers.alpaca_response(None)

@app.route('/api/v1/focuser/0/halt', methods=['PUT'])
@helpers.require_connected('focuser')
def focuser_halt():
    """Halt movement"""
    focuser.halt()
    return helpers.alpaca_response(None)

@app.route('/api/v1/focuser/0/temperature')
@helpers.require_connected('focuser')
def focuser_temperature():
    """Get temperature"""
    return helpers.alpaca_response(focuser.get_temperature())

@app.route('/api/v1/focuser/0/tempcomp', methods=['GET', 'PUT'])
@helpers.require_connected('focuser')
def focuser_tempcomp():
    """Get/set temperature compensation"""
    if request.method == 'GET':
        return helpers.alpaca_response(focuser.temp_comp_enabled)
    else:
        enabled = helpers.get_form_value('TempComp', False, bool)
        focuser.set_temp_compensation(enabled)
        return helpers.alpaca_response(None)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("OnStepX Alpaca Bridge - Complete Server with Discovery")
    print("=" * 60)
    
    # Initialize devices
    init_devices()
    
    print("\n" + "=" * 60)
    print("Device initialization complete!")
    print("=" * 60)
    
    # Start discovery service
    if config.ENABLE_DISCOVERY:
        print("\nStarting UDP Discovery Service...")
        discovery = AlpacaDiscovery(
            #port=config.DISCOVERY_PORT,
            #alpaca_port=config.SERVER_PORT
            alpaca_port=config.SERVER_PORT,
            server_info=config.SERVER_INFO,
            get_devices_callback=get_current_devices
        )
        discovery.start()
        
        print(f"✓ Discovery service running on UDP port {config.DISCOVERY_PORT}")
        print("  Clients can now auto-discover this server!")

    # Setup signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n\nShutting down gracefully...")
        if discovery:
            discovery.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start HTTP server
    print("\nHTTP Server starting...")
    print(f"Host: {config.SERVER_HOST}")
    print(f"Port: {config.SERVER_PORT}")
    print(f"\nAccess from network: http://<pi-ip>:{config.SERVER_PORT}")
    if config.ENABLE_DISCOVERY:
        print("N.I.N.A. should now auto-discover this server!")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    # Run Flask app
    try:
        app.run(
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.DEBUG_MODE,
            use_reloader=False  # Disable reloader to avoid double initialization
        )
    finally:
        if discovery:
            discovery.stop()
