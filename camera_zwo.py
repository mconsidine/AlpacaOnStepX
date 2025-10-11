"""
ZWO ASI Camera Driver
Implements ASCOM ICameraV4 interface
"""

import time
import numpy as np
from threading import Lock, Thread
from enum import IntEnum

try:
    import zwoasi as asi
    ZWO_AVAILABLE = True
except ImportError:
    ZWO_AVAILABLE = False

class CameraStates(IntEnum):
    cameraIdle = 0
    cameraWaiting = 1
    cameraExposing = 2
    cameraReading = 3
    cameraDownload = 4
    cameraError = 5

class SensorType(IntEnum):
    Monochrome = 0
    Color = 1
    RGGB = 2
    CMYG = 3
    CMYG2 = 4
    LRGB = 5

class ZWOCamera:
    """ZWO ASI Camera driver"""
    
    def __init__(self, camera_id=0, sdk_path=None):
        if not ZWO_AVAILABLE:
            raise RuntimeError("ZWO SDK not available")
        
        self.camera_id = camera_id
        self.sdk_path = sdk_path or '/usr/local/lib/libASICamera2.so'
        self.camera = None
        self.is_connected = False
        self.is_connecting = False
        self.lock = Lock()
        
        # Camera state
        self.camera_state = CameraStates.cameraIdle
        self.image_ready = False
        self.image_array = None
        self.last_exposure_duration = 0
        self.last_exposure_start_time = None
        self.percent_completed = 0
        
        # Camera properties (set on connect)
        self.camera_xsize = 0
        self.camera_ysize = 0
        self.max_bin_x = 1
        self.max_bin_y = 1
        self.pixel_size_x = 0
        self.pixel_size_y = 0
        self.sensor_type = SensorType.Color
        self.sensor_name = "Unknown"
        self.bayer_offset_x = 0
        self.bayer_offset_y = 0
        self.max_adu = 65535
        self.electrons_per_adu = 1.0
        self.full_well_capacity = 0
        
        # Configurable settings
        self.bin_x = 1
        self.bin_y = 1
        self.start_x = 0
        self.start_y = 0
        self.num_x = 0
        self.num_y = 0
        self.gain = 0
        self.gain_min = 0
        self.gain_max = 300
        self.offset = 0
        self.offset_min = 0
        self.offset_max = 50
        
        # Temperature/cooling
        self.ccd_temperature = 20.0
        self.cooler_on = False
        self.cooler_power = 0
        self.heat_sink_temperature = 20.0
        self.set_ccd_temperature = 0.0
        
        # Capabilities
        self.can_abort_exposure = True
        self.can_stop_exposure = True
        self.can_pulse_guide = False
        self.can_set_ccd_temperature = True
        self.can_get_cooler_power = True
        self.has_shutter = False
        self.can_asymmetric_bin = False
        self.can_fast_readout = False
        
        # Exposure limits
        self.exposure_min = 0.000032  # 32 microseconds
        self.exposure_max = 3600.0     # 1 hour
        self.exposure_resolution = 0.001  # 1ms
    
    def connect(self):
        """Connect to ZWO camera"""
        self.is_connecting = True
        try:
            # Initialize SDK
            asi.init(self.sdk_path)
            
            num_cameras = asi.get_num_cameras()
            if num_cameras == 0:
                raise RuntimeError("No ZWO cameras found")
            
            if self.camera_id >= num_cameras:
                raise RuntimeError(f"Camera {self.camera_id} not found")
            
            # Open camera
            self.camera = asi.Camera(self.camera_id)
            camera_info = self.camera.get_camera_property()
            
            # Set properties from camera info
            self.camera_xsize = camera_info['MaxWidth']
            self.camera_ysize = camera_info['MaxHeight']
            self.pixel_size_x = camera_info.get('PixelSize', 3.75)
            self.pixel_size_y = self.pixel_size_x
            self.sensor_name = camera_info.get('Name', 'ZWO ASI Camera')
            
            # Determine sensor type
            is_color = camera_info.get('IsColorCam', False)
            if is_color:
                bayer = camera_info.get('BayerPattern', 'RGGB')
                if bayer == 'RGGB':
                    self.sensor_type = SensorType.RGGB
                else:
                    self.sensor_type = SensorType.Color
            else:
                self.sensor_type = SensorType.Monochrome
            
            # Get binning support
            supported_bins = camera_info.get('SupportedBins', [1])
            self.max_bin_x = max(supported_bins)
            self.max_bin_y = self.max_bin_x
            
            # Set default ROI to full frame
            self.num_x = self.camera_xsize
            self.num_y = self.camera_ysize
            
            # Get control ranges
            controls = self.camera.get_controls()
            if 'Gain' in controls:
                self.gain_min = controls['Gain']['MinValue']
                self.gain_max = controls['Gain']['MaxValue']
            
            if 'Offset' in controls:
                self.offset_min = controls['Offset']['MinValue']
                self.offset_max = controls['Offset']['MaxValue']
            
            # Check cooling capability
            self.can_set_ccd_temperature = 'CoolerOn' in controls
            self.can_get_cooler_power = 'CoolPowerPerc' in controls
            
            # Check pulse guide capability
            self.can_pulse_guide = camera_info.get('ST4Port', False)
            
            self.is_connected = True
            print(f"Connected to {self.sensor_name}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to ZWO camera: {e}")
            self.is_connected = False
            return False
        finally:
            self.is_connecting = False
    
    def disconnect(self):
        """Disconnect from camera"""
        if self.camera:
            try:
                self.camera.close()
            except:
                pass
        self.is_connected = False
    
    def start_exposure(self, duration, is_light):
        """Start an exposure"""
        if self.camera_state != CameraStates.cameraIdle:
            raise RuntimeError("Camera is busy")
        
        try:
            with self.lock:
                # Set image type based on sensor
                if self.sensor_type == SensorType.Monochrome:
                    img_type = asi.ASI_IMG_RAW16
                else:
                    img_type = asi.ASI_IMG_RAW16
                
                # Set ROI
                self.camera.set_roi(
                    start_x=self.start_x,
                    start_y=self.start_y,
                    width=self.num_x,
                    height=self.num_y,
                    bins=self.bin_x,
                    image_type=img_type
                )
                
                # Set gain and offset
                self.camera.set_control_value(asi.ASI_GAIN, self.gain)
                self.camera.set_control_value(asi.ASI_OFFSET, self.offset)
                
                # Start exposure
                duration_us = int(duration * 1000000)
                self.camera.start_exposure(duration_us)
                
                self.camera_state = CameraStates.cameraExposing
                self.image_ready = False
                self.image_array = None
                self.last_exposure_duration = duration
                self.last_exposure_start_time = time.time()
                self.percent_completed = 0
            
            # Start monitoring thread
            thread = Thread(target=self._exposure_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.camera_state = CameraStates.cameraError
            raise RuntimeError(f"Failed to start exposure: {e}")
    
    def _exposure_thread(self):
        """Monitor exposure progress"""
        try:
            # Wait for exposure to complete
            while self.camera_state == CameraStates.cameraExposing:
                status = self.camera.get_exposure_status()
                elapsed = time.time() - self.last_exposure_start_time
                
                if status == asi.ASI_EXP_SUCCESS:
                    self.camera_state = CameraStates.cameraReading
                    break
                elif status == asi.ASI_EXP_FAILED:
                    self.camera_state = CameraStates.cameraError
                    return
                
                # Update progress
                if self.last_exposure_duration > 0:
                    self.percent_completed = min(100, int((elapsed / self.last_exposure_duration) * 100))
                
                time.sleep(0.1)
            
            # Download image
            if self.camera_state == CameraStates.cameraReading:
                self.camera_state = CameraStates.cameraDownload
                
                with self.lock:
                    # Get image data
                    img = self.camera.get_data_after_exposure()
                    whbi = self.camera.get_roi_format()
                    
                    # Reshape to 2D array
                    width = whbi[0]
                    height = whbi[1]
                    self.image_array = np.frombuffer(img, dtype=np.uint16).reshape((height, width))
                    
                    self.image_ready = True
                    self.camera_state = CameraStates.cameraIdle
                    self.percent_completed = 100
                    
        except Exception as e:
            print(f"Exposure error: {e}")
            self.camera_state = CameraStates.cameraError
    
    def abort_exposure(self):
        """Abort current exposure"""
        if self.camera and self.camera_state in [CameraStates.cameraExposing, CameraStates.cameraReading]:
            try:
                self.camera.stop_exposure()
            except:
                pass
            self.camera_state = CameraStates.cameraIdle
            self.image_ready = False
    
    def stop_exposure(self):
        """Stop exposure and save partial data"""
        # For ZWO, abort and stop are the same
        self.abort_exposure()
    
    def get_image_array(self):
        """Get the image array"""
        if not self.image_ready or self.image_array is None:
            raise RuntimeError("No image available")
        
        with self.lock:
            return self.image_array.copy()
    
    def pulse_guide(self, direction, duration):
        """Pulse guide (if ST4 port available)"""
        if not self.can_pulse_guide:
            raise RuntimeError("Pulse guide not supported")
        
        # Implementation depends on ZWO ST4 support
        # Placeholder for now
        raise RuntimeError("Pulse guide not yet implemented")
    
    def update_temperature(self):
        """Update temperature readings"""
        if self.camera and self.is_connected:
            try:
                temp = self.camera.get_control_value(asi.ASI_TEMPERATURE)[0] / 10.0
                self.ccd_temperature = temp
                
                if self.can_get_cooler_power:
                    power = self.camera.get_control_value(asi.ASI_COOLER_POWER_PERC)[0]
                    self.cooler_power = power
            except:
                pass
    
    def set_cooler(self, enabled):
        """Enable/disable cooler"""
        if not self.can_set_ccd_temperature:
            raise RuntimeError("Cooling not supported")
        
        try:
            self.camera.set_control_value(asi.ASI_COOLER_ON, 1 if enabled else 0)
            self.cooler_on = enabled
        except Exception as e:
            raise RuntimeError(f"Failed to set cooler: {e}")
    
    def set_target_temperature(self, temperature):
        """Set target CCD temperature"""
        if not self.can_set_ccd_temperature:
            raise RuntimeError("Temperature control not supported")
        
        try:
            # Convert to int (celsius)
            temp_int = int(temperature)
            self.camera.set_control_value(asi.ASI_TARGET_TEMP, temp_int)
            self.set_ccd_temperature = temperature
        except Exception as e:
            raise RuntimeError(f"Failed to set temperature: {e}")
            
    def supported_actions(self):
        """ZWO/ToupTek specific actions"""
        return [
            "SetCoolerPower",      # Set cooler power percentage
            "GetCoolerPower",      # Get current cooler power
            "SetFanSpeed",         # Set fan speed (if supported)
            "SetUSBBandwidth",     # Adjust USB bandwidth
            "GetUSBBandwidth",     # Query USB bandwidth
            "SetHighSpeedMode"     # Toggle high speed mode
        ]

