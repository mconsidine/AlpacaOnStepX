#!/usr/bin/env python3
"""
OnStepX Alpaca Bridge - Main Server
Complete implementation with Telescope + 2 Cameras + Placeholders for FilterWheel & Focuser
"""

from flask import Flask, request
import sys
import base64
import numpy as np

# Import configuration and helpers
import config
import alpaca_helpers as helpers

# Import device drivers
from telescope import OnStepXMount
from camera_zwo import ZWOCamera, ZWO_AVAILABLE
from camera_touptek import ToupTekCamera, TOUPTEK_AVAILABLE
from filterwheel import FilterWheel
from focuser import Focuser

# Initialize Flask app
app = Flask(__name__)

# Global device instances
telescope = None
camera_zwo = None
camera_touptek = None
filterwheel = None
focuser = None

def init_devices():
    """Initialize all configured devices"""
    global telescope, camera_zwo, camera_touptek, filterwheel, focuser
    
    print("Initializing devices...")
    
    # Initialize telescope
    if config.DEVICES['telescope']['enabled']:
        try:
            telescope = OnStepXMount(
                port=config.TELESCOPE_CONFIG['serial_port'],
                baudrate=config.TELESCOPE_CONFIG['baud_rate']
            )
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
    
    # Filter wheel placeholder
    if config.DEVICES['filterwheel']['enabled']:
        try:
            filterwheel = FilterWheel()
            app.filterwheel = filterwheel
            print("○ FilterWheel placeholder initialized")
        except Exception as e:
            print(f"○ FilterWheel: {e}")
    
    # Focuser placeholder
    if config.DEVICES['focuser']['enabled']:
        try:
            focuser = Focuser()
            app.focuser = focuser
            print("○ Focuser placeholder initialized")
        except Exception as e:
            print(f"○ Focuser: {e}")

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
# TELESCOPE API - COMMON PROPERTIES
# ============================================================================

@app.route('/api/v1/telescope/0/connected', methods=['GET', 'PUT'])
def telescope_connected():
    """Connect/disconnect telescope"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.is_connected)
    else:
        should_connect = helpers.get_form_value('Connected', False, bool)
        if should_connect and not telescope.is_connected:
            telescope.connect()
        elif not should_connect and telescope.is_connected:
            telescope.disconnect()
        return helpers.alpaca_response(telescope.is_connected)

@app.route('/api/v1/telescope/0/connecting')
def telescope_connecting():
    """Get telescope connecting status"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    return helpers.alpaca_response(telescope.is_connecting)

@app.route('/api/v1/telescope/0/description')
def telescope_description():
    """Get telescope description"""
    return helpers.alpaca_response("OnStepX Telescope Mount")

@app.route('/api/v1/telescope/0/driverinfo')
def telescope_driverinfo():
    """Get telescope driver info"""
    return helpers.alpaca_response("OnStepX Alpaca Bridge Driver v2.0")

@app.route('/api/v1/telescope/0/driverversion')
def telescope_driverversion():
    """Get telescope driver version"""
    return helpers.alpaca_response("2.0.0")

@app.route('/api/v1/telescope/0/interfaceversion')
def telescope_interfaceversion():
    """Get telescope interface version"""
    return helpers.alpaca_response(4)  # ITelescopeV4

@app.route('/api/v1/telescope/0/name')
def telescope_name():
    """Get telescope name"""
    return helpers.alpaca_response(config.DEVICES['telescope']['name'])

@app.route('/api/v1/telescope/0/supportedactions')
def telescope_supportedactions():
    """Get telescope supported actions"""
    return helpers.alpaca_response([])

# ============================================================================
# TELESCOPE API - POSITION PROPERTIES
# ============================================================================

@app.route('/api/v1/telescope/0/rightascension')
@helpers.require_connected('telescope')
def telescope_rightascension():
    """Get right ascension"""
    ra = telescope.get_ra()
    return helpers.alpaca_response(ra)

@app.route('/api/v1/telescope/0/declination')
@helpers.require_connected('telescope')
def telescope_declination():
    """Get declination"""
    dec = telescope.get_dec()
    return helpers.alpaca_response(dec)

@app.route('/api/v1/telescope/0/altitude')
@helpers.require_connected('telescope')
def telescope_altitude():
    """Get altitude"""
    alt = telescope.get_altitude()
    return helpers.alpaca_response(alt)

@app.route('/api/v1/telescope/0/azimuth')
@helpers.require_connected('telescope')
def telescope_azimuth():
    """Get azimuth"""
    az = telescope.get_azimuth()
    return helpers.alpaca_response(az)

@app.route('/api/v1/telescope/0/siderealtime')
@helpers.require_connected('telescope')
def telescope_siderealtime():
    """Get local sidereal time"""
    lst = telescope.get_sidereal_time()
    return helpers.alpaca_response(lst)

@app.route('/api/v1/telescope/0/sideofpier', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_sideofpier():
    """Get/set side of pier"""
    if request.method == 'GET':
        pier = telescope.get_pier_side()
        return helpers.alpaca_response(int(pier))
    else:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Setting pier side not supported")

# ============================================================================
# TELESCOPE API - TRACKING
# ============================================================================

@app.route('/api/v1/telescope/0/tracking', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_tracking():
    """Get/set tracking"""
    if request.method == 'GET':
        is_tracking = telescope.get_tracking()
        return helpers.alpaca_response(is_tracking)
    else:
        enable = helpers.get_form_value('Tracking', False, bool)
        telescope.set_tracking(enable)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/trackingrate', methods=['GET', 'PUT'])
@helpers.require_connected('telescope')
def telescope_trackingrate():
    """Get/set tracking rate"""
    if request.method == 'GET':
        return helpers.alpaca_response(int(telescope.tracking_rate))
    else:
        rate = helpers.get_form_value('TrackingRate', 0, int)
        telescope.set_tracking_rate(rate)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/trackingrates')
@helpers.require_connected('telescope')
def telescope_trackingrates():
    """Get supported tracking rates"""
    return helpers.alpaca_response([0, 1, 2])  # Sidereal, Lunar, Solar

# ============================================================================
# TELESCOPE API - SLEWING
# ============================================================================

@app.route('/api/v1/telescope/0/slewing')
@helpers.require_connected('telescope')
def telescope_slewing():
    """Get slewing status"""
    is_slewing = telescope.is_slewing()
    return helpers.alpaca_response(is_slewing)

@app.route('/api/v1/telescope/0/slewtocoordinatesasync', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_slewtocoordinatesasync():
    """Slew to coordinates asynchronously"""
    ra = helpers.get_form_value('RightAscension', 0.0, float)
    dec = helpers.get_form_value('Declination', 0.0, float)
    
    if not telescope.get_tracking():
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['INVALID_OPERATION'], "Tracking must be enabled")
    
    success = telescope.slew_to_coords(ra, dec)
    if not success:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], "Slew failed")
    
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/slewtoaltazasync', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_slewtoaltazasync():
    """Slew to alt/az coordinates asynchronously"""
    azimuth = helpers.get_form_value('Azimuth', 0.0, float)
    altitude = helpers.get_form_value('Altitude', 0.0, float)
    
    success = telescope.slew_to_altaz(azimuth, altitude)
    if not success:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], "Slew failed")
    
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/slewtotargetasync', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_slewtotargetasync():
    """Slew to target coordinates"""
    if not telescope.get_tracking():
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['INVALID_OPERATION'], "Tracking must be enabled")
    
    success = telescope.slew_to_coords(telescope.target_ra, telescope.target_dec)
    if not success:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], "Slew failed")
    
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/abortslew', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_abortslew():
    """Abort slew"""
    telescope.stop_slew()
    return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - TARGET COORDINATES
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

# (Continue in Part 2 for park, pulse guide, site config, capabilities, and all camera endpoints...)
