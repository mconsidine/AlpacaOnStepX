"""
ToupTek Camera Driver
Implements ASCOM ICameraV4 interface
"""

import time
import numpy as np
from threading import Lock, Thread
from enum import IntEnum

try:
    from toupcam import Toupcam as toupcam
    TOUPTEK_AVAILABLE = True
except ImportError:
    TOUPTEK_AVAILABLE = False

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

class ToupTekCamera:
    """ToupTek Camera driver"""
    
    def __init__(self, camera_id=0):
        if not TOUPTEK_AVAILABLE:
            raise RuntimeError("ToupTek SDK not available")
        
        self.camera_id = camera_id
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
        
        # Camera properties
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
        self.gain = 100
        self.gain_min = 0
        self.gain_max = 100
        self.offset = 0
        self.offset_min = 0
        self.offset_max = 0
        
        # Temperature
        self.ccd_temperature = 20.0
        self.cooler_on = False
        self.cooler_power = 0
        self.heat_sink_temperature = 20.0
        self.set_ccd_temperature = 0.0
        
        # Capabilities
        self.can_abort_exposure = True
        self.can_stop_exposure = True
        self.can_pulse_guide = False
        self.can_set_ccd_temperature = False
        self.can_get_cooler_power = False
        self.has_shutter = False
        self.can_asymmetric_bin = False
        self.can_fast_readout = False
        
        # Exposure limits
        self.exposure_min = 0.001  # 1ms
        self.exposure_max = 3600.0  # 1 hour
        self.exposure_resolution = 0.001
    
    def connect(self):
        """Connect to ToupTek camera"""
        self.is_connecting = True
        try:
            # Enumerate cameras
            arr = toupcam.Toupcam.EnumV2()
            if len(arr) == 0:
                raise RuntimeError("No ToupTek cameras found")
            
            if self.camera_id >= len(arr):
                raise RuntimeError(f"Camera {self.camera_id} not found")
            
            # Open camera
            self.camera = toupcam.Toupcam.Open(arr[self.camera_id].id)
            if self.camera is None:
                raise RuntimeError("Failed to open camera")
            
            # Get camera properties
            self.camera_xsize, self.camera_ysize = self.camera.get_Size()
            self.pixel_size_x = self.camera.get_PixelSize() / 1000.0  # Convert to microns
            self.pixel_size_y = self.pixel_size_x
            
            # Get model info
            model = self.camera.get_Model()
            self.sensor_name = model.name if hasattr(model, 'name') else "ToupTek Camera"
            
            # Determine sensor type
            if 'C' in self.sensor_name or 'Color' in self.sensor_name:
                self.sensor_type = SensorType.Color
            else:
                self.sensor_type = SensorType.Monochrome
            
            # Set default ROI
            self.num_x = self.camera_xsize
            self.num_y = self.camera_ysize
            
            # Set to 16-bit mode
            self.camera.put_Option(toupcam.TOUPCAM_OPTION_RGB, 48)
            
            # Check for cooling
            try:
                temp = self.camera.get_Temperature()
                if temp is not None:
                    self.can_set_ccd_temperature = True
            except:
                self.can_set_ccd_temperature = False
            
            self.is_connected = True
            print(f"Connected to {self.sensor_name}")
            return True
            
        except Exception as e:
            print(f"Failed to connect to ToupTek camera: {e}")
            self.is_connected = False
            return False
        finally:
            self.is_connecting = False
    
    def disconnect(self):
        """Disconnect from camera"""
        if self.camera:
            try:
                self.camera.Close()
            except:
                pass
        self.is_connected = False
    
    def _image_callback(self, event, ctx):
        """Callback when image is ready"""
        if event == toupcam.TOUPCAM_EVENT_IMAGE:
            self.camera_state = CameraStates.cameraDownload
            try:
                # Get image dimensions
                width, height = self.camera.PullImageV2(None, 16, None)
                
                # Allocate buffer
                buf = bytes(width * height * 2)  # 16-bit
                self.camera.PullImageV2(buf, 16, None)
                
                # Convert to numpy array
                with self.lock:
                    self.image_array = np.frombuffer(buf, dtype=np.uint16).reshape((height, width))
                    
                    self.image_ready = True
                    self.camera_state = CameraStates.cameraIdle
                    self.percent_completed = 100
                    
            except Exception as e:
                print(f"Image download error: {e}")
                self.camera_state = CameraStates.cameraError
    
    def start_exposure(self, duration, is_light):
        """Start an exposure"""
        if self.camera_state != CameraStates.cameraIdle:
            raise RuntimeError("Camera is busy")
        
        try:
            with self.lock:
                # Set exposure time (microseconds)
                exp_time_us = int(duration * 1000000)
                self.camera.put_ExpoTime(exp_time_us)
                
                # Set gain
                self.camera.put_ExpoAGain(self.gain)
                
                # Start pull mode with callback
                self.camera.StartPullModeWithCallback(self._image_callback, None)
                
                # Trigger snap
                self.camera.Snap(0)
                
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
        while self.camera_state == CameraStates.cameraExposing:
            elapsed = time.time() - self.last_exposure_start_time
            if self.last_exposure_duration > 0:
                self.percent_completed = min(100, int((elapsed / self.last_exposure_duration) * 100))
            time.sleep(0.1)
    
    def abort_exposure(self):
        """Abort current exposure"""
        if self.camera and self.camera_state in [CameraStates.cameraExposing, CameraStates.cameraReading]:
            try:
                self.camera.Stop()
            except:
                pass
            self.camera_state = CameraStates.cameraIdle
            self.image_ready = False
    
    def stop_exposure(self):
        """Stop exposure"""
        self.abort_exposure()
    
    def get_image_array(self):
        """Get the image array"""
        if not self.image_ready or self.image_array is None:
            raise RuntimeError("No image available")
        
        with self.lock:
            return self.image_array.copy()
    
    def pulse_guide(self, direction, duration):
        """Pulse guide (not supported)"""
        raise RuntimeError("Pulse guide not supported on ToupTek cameras")
    
    def update_temperature(self):
        """Update temperature readings"""
        if self.camera and self.is_connected and self.can_set_ccd_temperature:
            try:
                temp = self.camera.get_Temperature()
                if temp is not None:
                    self.ccd_temperature = temp / 10.0  # Convert to celsius
            except:
                pass
    
    def set_cooler(self, enabled):
        """Enable/disable cooler (if supported)"""
        if not self.can_set_ccd_temperature:
            raise RuntimeError("Cooling not supported on this camera")
        
        # ToupTek cooling control varies by model
        # This is a placeholder
        self.cooler_on = enabled
    
    def set_target_temperature(self, temperature):
        """Set target CCD temperature (if supported)"""
        if not self.can_set_ccd_temperature:
            raise RuntimeError("Temperature control not supported on this camera")
        
        # ToupTek temperature control varies by model
        # This is a placeholder
        self.set_ccd_temperature = temperature

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

