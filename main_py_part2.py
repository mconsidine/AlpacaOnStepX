# CONTINUATION OF main.py - Part 2

# ============================================================================
# TELESCOPE API - PARK/HOME
# ============================================================================

@app.route('/api/v1/telescope/0/atpark')
@helpers.require_connected('telescope')
def telescope_atpark():
    """Get at park status"""
    at_park = telescope.get_at_park()
    return helpers.alpaca_response(at_park)

@app.route('/api/v1/telescope/0/athome')
@helpers.require_connected('telescope')
def telescope_athome():
    """Get at home status"""
    at_home = telescope.get_at_home()
    return helpers.alpaca_response(at_home)

@app.route('/api/v1/telescope/0/park', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_park():
    """Park telescope"""
    success = telescope.park()
    if not success:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], "Park failed")
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/unpark', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_unpark():
    """Unpark telescope"""
    success = telescope.unpark()
    if not success:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], "Unpark failed")
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/findhome', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_findhome():
    """Find home position"""
    success = telescope.find_home()
    if not success:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['UNSPECIFIED_ERROR'], "Find home failed")
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/setpark', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_setpark():
    """Set current position as park"""
    telescope.set_park()
    return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - PULSE GUIDE
# ============================================================================

@app.route('/api/v1/telescope/0/pulseguide', methods=['PUT'])
@helpers.require_connected('telescope')
def telescope_pulseguide():
    """Pulse guide"""
    direction = helpers.get_form_value('Direction', 0, int)
    duration = helpers.get_form_value('Duration', 0, int)
    
    if not telescope.get_tracking():
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['INVALID_OPERATION'], "Tracking must be enabled")
    
    telescope.pulse_guide(direction, duration)
    return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/ispulseguiding')
@helpers.require_connected('telescope')
def telescope_ispulseguiding():
    """Get pulse guiding status"""
    is_guiding = telescope.is_pulse_guiding()
    return helpers.alpaca_response(is_guiding)

# ============================================================================
# TELESCOPE API - SITE CONFIGURATION
# ============================================================================

@app.route('/api/v1/telescope/0/sitelatitude', methods=['GET', 'PUT'])
def telescope_sitelatitude():
    """Get/set site latitude"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.site_latitude)
    else:
        if not telescope.is_connected:
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Not connected")
        latitude = helpers.get_form_value('SiteLatitude', 0.0, float)
        telescope.set_site_latitude(latitude)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/sitelongitude', methods=['GET', 'PUT'])
def telescope_sitelongitude():
    """Get/set site longitude"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.site_longitude)
    else:
        if not telescope.is_connected:
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Not connected")
        longitude = helpers.get_form_value('SiteLongitude', 0.0, float)
        telescope.set_site_longitude(longitude)
        return helpers.alpaca_response(None)

@app.route('/api/v1/telescope/0/siteelevation', methods=['GET', 'PUT'])
def telescope_siteelevation():
    """Get/set site elevation"""
    if not telescope:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Telescope not available")
    
    if request.method == 'GET':
        return helpers.alpaca_response(telescope.site_elevation)
    else:
        telescope.site_elevation = helpers.get_form_value('SiteElevation', 0.0, float)
        return helpers.alpaca_response(None)

# ============================================================================
# TELESCOPE API - CAPABILITIES
# ============================================================================

@app.route('/api/v1/telescope/0/canfindhome')
def telescope_canfindhome():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canpark')
def telescope_canpark():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canpulseguide')
def telescope_canpulseguide():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/cansettracking')
def telescope_cansettracking():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canslew')
def telescope_canslew():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canslewaltaz')
def telescope_canslewaltaz():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canslewasync')
def telescope_canslewasync():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/cansync')
def telescope_cansync():
    return helpers.alpaca_response(True)

@app.route('/api/v1/telescope/0/canunpark')
def telescope_canunpark():
    return helpers.alpaca_response(True)

# ============================================================================
# CAMERA API - CONNECTION & INFO
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/connected', methods=['GET', 'PUT'])
def camera_connected(device_number):
    """Connect/disconnect camera"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")
    
    if request.method == 'GET':
        return helpers.alpaca_response(camera.is_connected)
    else:
        should_connect = helpers.get_form_value('Connected', False, bool)
        if should_connect and not camera.is_connected:
            camera.connect()
        elif not should_connect and camera.is_connected:
            camera.disconnect()
        return helpers.alpaca_response(camera.is_connected)

@app.route('/api/v1/camera/<int:device_number>/connecting')
def camera_connecting(device_number):
    """Get camera connecting status"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")
    return helpers.alpaca_response(camera.is_connecting)

@app.route('/api/v1/camera/<int:device_number>/description')
def camera_description(device_number):
    """Get camera description"""
    if device_number == 0:
        return helpers.alpaca_response("ZWO ASI Camera")
    elif device_number == 1:
        return helpers.alpaca_response("ToupTek Camera")
    return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")

@app.route('/api/v1/camera/<int:device_number>/name')
def camera_name(device_number):
    """Get camera name"""
    camera = get_camera(device_number)
    if not camera:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Camera not found")
    if camera.is_connected:
        return helpers.alpaca_response(camera.sensor_name)
    return camera_description(device_number)

@app.route('/api/v1/camera/<int:device_number>/interfaceversion')
def camera_interfaceversion(device_number):
    """Get camera interface version"""
    return helpers.alpaca_response(4)  # ICameraV4

# ============================================================================
# CAMERA API - STATE & SIZE
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/camerastate')
def camera_camerastate(device_number):
    """Get camera state"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(int(camera.camera_state))

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
    """Get image as Base64 encoded string (more efficient)"""
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
        camera.gain = helpers.clamp(gain, camera.gain_min, camera.gain_max)
        return helpers.alpaca_response(None)

@app.route('/api/v1/camera/<int:device_number>/gainmin')
def camera_gainmin(device_number):
    """Get minimum gain"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.gain_min)

@app.route('/api/v1/camera/<int:device_number>/gainmax')
def camera_gainmax(device_number):
    """Get maximum gain"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    return helpers.alpaca_response(camera.gain_max)

# ============================================================================
# CAMERA API - TEMPERATURE & COOLING
# ============================================================================

@app.route('/api/v1/camera/<int:device_number>/ccdtemperature')
def camera_ccdtemperature(device_number):
    """Get CCD temperature"""
    camera = get_camera(device_number)
    if not camera or not camera.is_connected:
        return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_CONNECTED'], "Camera not connected")
    
    camera.update_temperature()
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
            return helpers.alpaca_error(config.ASCOM_ERROR_CODES['NOT_IMPLEMENTED'], "Cooling not supported")
        
        enabled = helpers.get_form_value('CoolerOn', False, bool)
        camera.set_cooler(enabled)
        return helpers.alpaca_response(None)

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
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("OnStepX Alpaca Bridge - Complete Server")
    print("=" * 60)
    
    # Initialize devices
    init_devices()
    
    print("\nServer starting...")
    print(f"Host: {config.SERVER_HOST}")
    print(f"Port: {config.SERVER_PORT}")
    print(f"\nAccess from network: http://<pi-ip>:{config.SERVER_PORT}")
    print("=" * 60)
    
    # Run Flask app
    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=config.DEBUG_MODE
    )
