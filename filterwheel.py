"""
Filter Wheel Driver - ZWO EFW + Mock Mode
Implements ASCOM IFilterWheelV2 interface
Supports ZWO Electronic Filter Wheel with room for expansion
"""

import time
import ctypes
import os
from threading import Lock
from enum import IntEnum

# Try to import ZWO EFW SDK
ZWO_EFW_AVAILABLE = False
try:
    # ZWO EFW SDK library path - adjust if needed
    EFW_SDK_PATH = '/usr/local/lib/libEFWFilter.so'
    if os.path.exists(EFW_SDK_PATH):
        efw_lib = ctypes.CDLL(EFW_SDK_PATH)
        ZWO_EFW_AVAILABLE = True
        print(f"✓ ZWO EFW SDK loaded from {EFW_SDK_PATH}")
except Exception as e:
    print(f"○ ZWO EFW SDK not available: {e}")
    print(f"  Filter wheel will use MOCK mode")

# ============================================================================
# ZWO EFW SDK Wrapper (if available)
# ============================================================================

if ZWO_EFW_AVAILABLE:
    class EFW_ERROR_CODE(IntEnum):
        EFW_SUCCESS = 0
        EFW_ERROR_INVALID_INDEX = 1
        EFW_ERROR_INVALID_ID = 2
        EFW_ERROR_INVALID_VALUE = 3
        EFW_ERROR_REMOVED = 4
        EFW_ERROR_MOVING = 5
        EFW_ERROR_ERROR_STATE = 6
        EFW_ERROR_GENERAL_ERROR = 7
        EFW_ERROR_NOT_SUPPORTED = 8
        EFW_ERROR_CLOSED = 9
    
    class EFW_ID(ctypes.Structure):
        _fields_ = [
            ("ID", ctypes.c_int),
            ("name", ctypes.c_char * 64)
        ]
    
    class EFW_INFO(ctypes.Structure):
        _fields_ = [
            ("ID", ctypes.c_int),
            ("name", ctypes.c_char * 64),
            ("slotNum", ctypes.c_int)
        ]
    
    # Define SDK functions
    efw_lib.EFWGetNum.restype = ctypes.c_int
    efw_lib.EFWGetNum.argtypes = []
    
    efw_lib.EFWGetID.restype = ctypes.c_int
    efw_lib.EFWGetID.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    
    efw_lib.EFWOpen.restype = ctypes.c_int
    efw_lib.EFWOpen.argtypes = [ctypes.c_int]
    
    efw_lib.EFWClose.restype = ctypes.c_int
    efw_lib.EFWClose.argtypes = [ctypes.c_int]
    
    efw_lib.EFWGetProperty.restype = ctypes.c_int
    efw_lib.EFWGetProperty.argtypes = [ctypes.c_int, ctypes.POINTER(EFW_INFO)]
    
    efw_lib.EFWGetPosition.restype = ctypes.c_int
    efw_lib.EFWGetPosition.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    
    efw_lib.EFWSetPosition.restype = ctypes.c_int
    efw_lib.EFWSetPosition.argtypes = [ctypes.c_int, ctypes.c_int]
    
    efw_lib.EFWCalibrate.restype = ctypes.c_int
    efw_lib.EFWCalibrate.argtypes = [ctypes.c_int]

# ============================================================================
# Base Filter Wheel Class
# ============================================================================

class FilterWheelBase:
    """Base class for filter wheel implementations"""
    
    def __init__(self):
        self.is_connected = False
        self.lock = Lock()
        self.moving = False
        self.current_position = 0
        self.target_position = 0
        
        # Filter configuration (override in subclass or config)
        self.slot_count = 8
        self.filter_names = [
            "Red",
            "Green", 
            "Blue",
            "Luminance",
            "H-Alpha",
            "OIII",
            "SII",
            "Clear"
        ]
        
        # Focus offsets in microns (adjust for each filter)
        self.focus_offsets = [0, 0, 0, 0, 50, 30, 40, 0]
    
    def connect(self):
        """Connect to filter wheel"""
        raise NotImplementedError
    
    def disconnect(self):
        """Disconnect from filter wheel"""
        raise NotImplementedError
    
    def get_position(self):
        """Get current filter position (0-based)"""
        raise NotImplementedError
    
    def set_position(self, position):
        """Set filter position (0-based)"""
        raise NotImplementedError
    
    def is_moving(self):
        """Check if filter wheel is moving"""
        return self.moving
    
    def get_filter_name(self, position):
        """Get name of filter at position"""
        if 0 <= position < len(self.filter_names):
            return self.filter_names[position]
        return f"Filter {position + 1}"
    
    def set_filter_name(self, position, name):
        """Set name of filter at position"""
        if 0 <= position < len(self.filter_names):
            self.filter_names[position] = name
    
    def get_focus_offset(self, position):
        """Get focus offset for filter at position"""
        if 0 <= position < len(self.focus_offsets):
            return self.focus_offsets[position]
        return 0
    
    def set_focus_offset(self, position, offset):
        """Set focus offset for filter at position"""
        if 0 <= position < len(self.focus_offsets):
            self.focus_offsets[position] = offset
    
    def supported_actions(self):
        """Get list of supported Action() commands"""
        return [
            "Calibrate",
            "GetFirmware",
            "GetSerialNumber"
        ]

# ============================================================================
# ZWO EFW Implementation
# ============================================================================

class ZWOFilterWheel(FilterWheelBase):
    """ZWO Electronic Filter Wheel driver"""
    
    def __init__(self, wheel_id=0):
        super().__init__()
        self.wheel_id = wheel_id
        self.efw_id = -1
        
        if not ZWO_EFW_AVAILABLE:
            raise Exception("ZWO EFW SDK not available")
    
    def connect(self):
        """Connect to ZWO filter wheel"""
        try:
            # Get number of connected filter wheels
            num_wheels = efw_lib.EFWGetNum()
            if num_wheels <= 0:
                print("✗ No ZWO filter wheels found")
                return False
            
            print(f"Found {num_wheels} ZWO filter wheel(s)")
            
            # Get ID of specified wheel
            wheel_id = ctypes.c_int()
            result = efw_lib.EFWGetID(self.wheel_id, ctypes.byref(wheel_id))
            if result != EFW_ERROR_CODE.EFW_SUCCESS:
                print(f"✗ Failed to get filter wheel ID: {result}")
                return False
            
            self.efw_id = wheel_id.value
            
            # Open connection
            result = efw_lib.EFWOpen(self.efw_id)
            if result != EFW_ERROR_CODE.EFW_SUCCESS:
                print(f"✗ Failed to open filter wheel: {result}")
                return False
            
            # Get properties
            info = EFW_INFO()
            result = efw_lib.EFWGetProperty(self.efw_id, ctypes.byref(info))
            if result == EFW_ERROR_CODE.EFW_SUCCESS:
                self.slot_count = info.slotNum
                name = info.name.decode('ascii')
                print(f"✓ Connected to {name} with {self.slot_count} positions")
                
                # Initialize filter names for available slots
                if len(self.filter_names) > self.slot_count:
                    self.filter_names = self.filter_names[:self.slot_count]
                if len(self.focus_offsets) > self.slot_count:
                    self.focus_offsets = self.focus_offsets[:self.slot_count]
            
            # Get initial position
            position = ctypes.c_int()
            result = efw_lib.EFWGetPosition(self.efw_id, ctypes.byref(position))
            if result == EFW_ERROR_CODE.EFW_SUCCESS:
                self.current_position = position.value
                print(f"  Current position: {self.current_position}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"✗ ZWO filter wheel connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from filter wheel"""
        if self.efw_id >= 0:
            try:
                efw_lib.EFWClose(self.efw_id)
                print("✓ ZWO filter wheel disconnected")
            except:
                pass
        self.is_connected = False
        self.efw_id = -1
    
    def get_position(self):
        """Get current filter position"""
        if not self.is_connected:
            return -1
        
        with self.lock:
            position = ctypes.c_int()
            result = efw_lib.EFWGetPosition(self.efw_id, ctypes.byref(position))
            if result == EFW_ERROR_CODE.EFW_SUCCESS:
                self.current_position = position.value
                return self.current_position
            return -1
    
    def set_position(self, position):
        """Set filter position"""
        if not self.is_connected:
            return False
        
        if position < 0 or position >= self.slot_count:
            print(f"✗ Invalid position {position} (valid: 0-{self.slot_count-1})")
            return False
        
        with self.lock:
            self.moving = True
            self.target_position = position
            
            result = efw_lib.EFWSetPosition(self.efw_id, position)
            if result == EFW_ERROR_CODE.EFW_SUCCESS:
                print(f"Moving to position {position} ({self.get_filter_name(position)})")
                
                # Wait for movement to complete
                while True:
                    time.sleep(0.1)
                    pos = ctypes.c_int()
                    result = efw_lib.EFWGetPosition(self.efw_id, ctypes.byref(pos))
                    
                    if result == EFW_ERROR_CODE.EFW_SUCCESS:
                        if pos.value == position:
                            break
                    elif result != EFW_ERROR_CODE.EFW_ERROR_MOVING:
                        print(f"✗ Error during move: {result}")
                        self.moving = False
                        return False
                
                self.current_position = position
                self.moving = False
                print(f"✓ Moved to position {position}")
                return True
            else:
                print(f"✗ Failed to set position: {result}")
                self.moving = False
                return False
    
    def calibrate(self):
        """Calibrate filter wheel (find home position)"""
        if not self.is_connected:
            return False
        
        print("Calibrating filter wheel...")
        result = efw_lib.EFWCalibrate(self.efw_id)
        if result == EFW_ERROR_CODE.EFW_SUCCESS:
            time.sleep(5)  # Calibration takes a few seconds
            print("✓ Calibration complete")
            return True
        else:
            print(f"✗ Calibration failed: {result}")
            return False

# ============================================================================
# Mock Filter Wheel Implementation (for testing without hardware)
# ============================================================================

class MockFilterWheel(FilterWheelBase):
    """Mock filter wheel for testing without hardware"""
    
    def __init__(self, slot_count=8):
        super().__init__()
        self.slot_count = slot_count
        print(f"○ Mock filter wheel created with {slot_count} positions")
    
    def connect(self):
        """Simulate connection"""
        print("○ Mock filter wheel connecting...")
        time.sleep(0.5)
        self.is_connected = True
        self.current_position = 0
        print(f"✓ Mock filter wheel connected ({self.slot_count} positions)")
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        print("○ Mock filter wheel disconnected")
        self.is_connected = False
    
    def get_position(self):
        """Get current position"""
        return self.current_position
    
    def set_position(self, position):
        """Simulate moving to position"""
        if not self.is_connected:
            return False
        
        if position < 0 or position >= self.slot_count:
            print(f"✗ Invalid position {position} (valid: 0-{self.slot_count-1})")
            return False
        
        print(f"○ Mock: Moving to position {position} ({self.get_filter_name(position)})")
        
        self.moving = True
        self.target_position = position
        
        # Simulate movement time (1 second per position)
        move_time = abs(position - self.current_position) * 1.0
        time.sleep(move_time)
        
        self.current_position = position
        self.moving = False
        
        print(f"✓ Mock: At position {position}")
        return True
    
    def calibrate(self):
        """Simulate calibration"""
        print("○ Mock: Calibrating...")
        time.sleep(2)
        self.current_position = 0
        print("✓ Mock: Calibration complete")
        return True

# ============================================================================
# Factory Function (selects ZWO or Mock based on availability and config)
# ============================================================================

def create_filterwheel(mode='auto', wheel_id=0, slot_count=8):
    """
    Factory function to create appropriate filter wheel instance
    
    Args:
        mode: 'auto', 'zwo', or 'mock'
        wheel_id: ZWO wheel ID (if multiple wheels)
        slot_count: Number of filter slots (for mock mode)
    
    Returns:
        FilterWheel instance
    """
    if mode == 'mock':
        return MockFilterWheel(slot_count)
    elif mode == 'zwo':
        if not ZWO_EFW_AVAILABLE:
            print("⚠ ZWO SDK not available, falling back to mock mode")
            return MockFilterWheel(slot_count)
        return ZWOFilterWheel(wheel_id)
    elif mode == 'auto':
        # Auto-select: ZWO if available, otherwise mock
        if ZWO_EFW_AVAILABLE:
            return ZWOFilterWheel(wheel_id)
        else:
            return MockFilterWheel(slot_count)
    else:
        raise ValueError(f"Unknown mode: {mode}")

# ============================================================================
# Legacy FilterWheel class (for backward compatibility)
# ============================================================================

class FilterWheel:
    """
    Legacy placeholder - redirects to factory function
    Use create_filterwheel() for new code
    """
    def __init__(self):
        print("⚠ Using legacy FilterWheel class")
        print("  Please update to use create_filterwheel() factory function")
        self.impl = create_filterwheel(mode='mock')
    
    def __getattr__(self, name):
        return getattr(self.impl, name)

# ============================================================================
# Test Code
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Filter Wheel Test")
    print("=" * 60)
    
    # Test mock mode
    print("\n--- Testing Mock Mode ---")
    fw = create_filterwheel(mode='mock', slot_count=8)
    fw.connect()
    
    print(f"\nCurrent position: {fw.get_position()}")
    print(f"Filter name: {fw.get_filter_name(fw.get_position())}")
    
    # Display all filters
    print("\n--- All Filters ---")
    for i in range(fw.slot_count):
        print(f"  Position {i}: {fw.get_filter_name(i)} (offset: {fw.get_focus_offset(i)} µm)")
    
    # Test movement
    print("\n--- Testing Movement ---")
    for pos in [3, 7, 0]:
        fw.set_position(pos)
        print(f"Position: {fw.get_position()}, Filter: {fw.get_filter_name(pos)}")
        print(f"Focus offset: {fw.get_focus_offset(pos)} microns")
    
    # Test custom filter names
    print("\n--- Testing Custom Filter Names ---")
    fw.set_filter_name(0, "Custom Red")
    fw.set_filter_name(1, "Custom Green")
    print(f"Position 0: {fw.get_filter_name(0)}")
    print(f"Position 1: {fw.get_filter_name(1)}")
    
    # Test focus offsets
    print("\n--- Testing Focus Offsets ---")
    fw.set_focus_offset(4, 100)
    print(f"Position 4 offset: {fw.get_focus_offset(4)} µm")
    
    # Test calibration
    print("\n--- Testing Calibration ---")
    fw.calibrate()
    
    fw.disconnect()
    
    # Test ZWO mode if available
    if ZWO_EFW_AVAILABLE:
        print("\n--- Testing ZWO Mode ---")
        fw_zwo = create_filterwheel(mode='zwo')
        if fw_zwo.connect():
            print(f"Position: {fw_zwo.get_position()}")
            print(f"Slot count: {fw_zwo.slot_count}")
            fw_zwo.disconnect()
    
    print("\n✓ Filter wheel tests complete")
