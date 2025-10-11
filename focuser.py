"""
Focuser Driver - ZWO EAF + Mock Mode
Implements ASCOM IFocuserV3 interface
Supports ZWO Electronic Auto Focuser with room for expansion
Includes backlash compensation
"""

import time
import ctypes
import os
from threading import Lock
from enum import IntEnum

# Try to import ZWO EAF SDK
ZWO_EAF_AVAILABLE = False
try:
    # ZWO EAF SDK library path - adjust if needed
    EAF_SDK_PATH = '/usr/local/lib/libEAFFocuser.so'
    if os.path.exists(EAF_SDK_PATH):
        eaf_lib = ctypes.CDLL(EAF_SDK_PATH)
        ZWO_EAF_AVAILABLE = True
        print(f"✓ ZWO EAF SDK loaded from {EAF_SDK_PATH}")
except Exception as e:
    print(f"○ ZWO EAF SDK not available: {e}")
    print(f"  Focuser will use MOCK mode")

# ============================================================================
# ZWO EAF SDK Wrapper (if available)
# ============================================================================

if ZWO_EAF_AVAILABLE:
    class EAF_ERROR_CODE(IntEnum):
        EAF_SUCCESS = 0
        EAF_ERROR_INVALID_INDEX = 1
        EAF_ERROR_INVALID_ID = 2
        EAF_ERROR_INVALID_VALUE = 3
        EAF_ERROR_REMOVED = 4
        EAF_ERROR_MOVING = 5
        EAF_ERROR_ERROR_STATE = 6
        EAF_ERROR_GENERAL_ERROR = 7
        EAF_ERROR_NOT_SUPPORTED = 8
        EAF_ERROR_CLOSED = 9
        EAF_ERROR_END = 10
    
    class EAF_ID(ctypes.Structure):
        _fields_ = [
            ("ID", ctypes.c_int),
            ("name", ctypes.c_char * 64)
        ]
    
    class EAF_INFO(ctypes.Structure):
        _fields_ = [
            ("ID", ctypes.c_int),
            ("name", ctypes.c_char * 64),
            ("MaxStep", ctypes.c_int),
            ("reserved", ctypes.c_char * 32)
        ]
    
    # Define SDK functions
    eaf_lib.EAFGetNum.restype = ctypes.c_int
    eaf_lib.EAFGetNum.argtypes = []
    
    eaf_lib.EAFGetID.restype = ctypes.c_int
    eaf_lib.EAFGetID.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    
    eaf_lib.EAFOpen.restype = ctypes.c_int
    eaf_lib.EAFOpen.argtypes = [ctypes.c_int]
    
    eaf_lib.EAFClose.restype = ctypes.c_int
    eaf_lib.EAFClose.argtypes = [ctypes.c_int]
    
    eaf_lib.EAFGetProperty.restype = ctypes.c_int
    eaf_lib.EAFGetProperty.argtypes = [ctypes.c_int, ctypes.POINTER(EAF_INFO)]
    
    eaf_lib.EAFGetPosition.restype = ctypes.c_int
    eaf_lib.EAFGetPosition.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    
    eaf_lib.EAFMove.restype = ctypes.c_int
    eaf_lib.EAFMove.argtypes = [ctypes.c_int, ctypes.c_int]
    
    eaf_lib.EAFStop.restype = ctypes.c_int
    eaf_lib.EAFStop.argtypes = [ctypes.c_int]
    
    eaf_lib.EAFIsMoving.restype = ctypes.c_int
    eaf_lib.EAFIsMoving.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_bool)]
    
    eaf_lib.EAFGetTemp.restype = ctypes.c_int
    eaf_lib.EAFGetTemp.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
    
    eaf_lib.EAFResetPostion.restype = ctypes.c_int  # Note: SDK has typo "Postion"
    eaf_lib.EAFResetPostion.argtypes = [ctypes.c_int, ctypes.c_int]

# ============================================================================
# Base Focuser Class
# ============================================================================

class FocuserBase:
    """Base class for focuser implementations"""
    
    def __init__(self):
        self.is_connected = False
        self.lock = Lock()
        self.moving = False
        self.current_position = 0
        self.target_position = 0
        
        # Focuser configuration
        self.max_position = 100000  # Maximum steps
        self.max_increment = 10000   # Maximum single move
        self.step_size = 1.0         # Microns per step (adjust for your focuser)
        self.temperature = 20.0      # Current temperature in Celsius
        self.temp_comp = False       # Temperature compensation enabled
        self.temp_comp_available = True
        
        # Backlash compensation
        self.backlash_steps = 0        # Steps of backlash (0 = disabled)
        self.last_direction = None     # 'in' or 'out'
        self.backlash_enabled = False
    
    def connect(self):
        """Connect to focuser"""
        raise NotImplementedError
    
    def disconnect(self):
        """Disconnect from focuser"""
        raise NotImplementedError
    
    def get_position(self):
        """Get current position"""
        raise NotImplementedError
    
    def set_backlash_compensation(self, steps):
        """
        Set backlash compensation amount
        
        Args:
            steps: Number of steps to compensate (0 = disabled)
                   Positive value compensates for gear backlash
        """
        self.backlash_steps = abs(steps)
        self.backlash_enabled = steps > 0
        print(f"Backlash compensation: {self.backlash_steps} steps ({'enabled' if self.backlash_enabled else 'disabled'})")
    
    def move_to(self, position):
        """
        Move to absolute position with backlash compensation
        
        Backlash compensation strategy:
        1. Determine direction of move
        2. If direction changed, overshoot by backlash amount
        3. Always approach final position from same direction
        """
        if not self.is_connected:
            return False
        
        # Validate position
        if position < 0 or position > self.max_position:
            print(f"✗ Position {position} out of range (0-{self.max_position})")
            return False
        
        current = self.get_position()
        
        # Determine move direction
        if position > current:
            direction = 'out'
        elif position < current:
            direction = 'in'
        else:
            # Already at position
            return True
        
        # Apply backlash compensation if enabled
        if self.backlash_enabled and self.backlash_steps > 0:
            # Check if direction changed
            if self.last_direction is not None and self.last_direction != direction:
                print(f"⚙ Backlash compensation: direction changed {self.last_direction} → {direction}")
                
                # Overshoot, then approach from consistent direction
                if direction == 'out':
                    # Moving outward: overshoot inward first, then move out
                    overshoot_pos = max(0, position - self.backlash_steps)
                    print(f"  Step 1: Overshoot to {overshoot_pos}")
                    self._move_without_backlash(overshoot_pos)
                    print(f"  Step 2: Approach target {position}")
                    result = self._move_without_backlash(position)
                else:
                    # Moving inward: overshoot outward first, then move in
                    overshoot_pos = min(self.max_position, position + self.backlash_steps)
                    print(f"  Step 1: Overshoot to {overshoot_pos}")
                    self._move_without_backlash(overshoot_pos)
                    print(f"  Step 2: Approach target {position}")
                    result = self._move_without_backlash(position)
            else:
                # Same direction or first move - no compensation needed
                result = self._move_without_backlash(position)
        else:
            # No backlash compensation
            result = self._move_without_backlash(position)
        
        # Remember direction for next move
        if result:
            self.last_direction = direction
        
        return result
    
    def _move_without_backlash(self, position):
        """
        Internal method: move to position without backlash logic
        Subclasses should override this instead of move_to()
        """
        raise NotImplementedError
    
    def move_relative(self, steps):
        """Move relative number of steps"""
        target = self.current_position + steps
        target = max(0, min(target, self.max_position))
        return self.move_to(target)
    
    def halt(self):
        """Stop movement"""
        raise NotImplementedError
    
    def is_moving(self):
        """Check if focuser is moving"""
        return self.moving
    
    def get_temperature(self):
        """Get temperature reading"""
        return self.temperature

# ============================================================================
# ZWO EAF Implementation
# ============================================================================

class ZWOFocuser(FocuserBase):
    """ZWO Electronic Auto Focuser driver"""
    
    def __init__(self, focuser_id=0):
        super().__init__()
        self.focuser_id = focuser_id
        self.eaf_id = -1
        
        if not ZWO_EAF_AVAILABLE:
            raise Exception("ZWO EAF SDK not available")
    
    def connect(self):
        """Connect to ZWO focuser"""
        try:
            # Get number of connected focusers
            num_focusers = eaf_lib.EAFGetNum()
            if num_focusers <= 0:
                print("✗ No ZWO focusers found")
                return False
            
            print(f"Found {num_focusers} ZWO focuser(s)")
            
            # Get ID of specified focuser
            focuser_id = ctypes.c_int()
            result = eaf_lib.EAFGetID(self.focuser_id, ctypes.byref(focuser_id))
            if result != EAF_ERROR_CODE.EAF_SUCCESS:
                print(f"✗ Failed to get focuser ID: {result}")
                return False
            
            self.eaf_id = focuser_id.value
            
            # Open connection
            result = eaf_lib.EAFOpen(self.eaf_id)
            if result != EAF_ERROR_CODE.EAF_SUCCESS:
                print(f"✗ Failed to open focuser: {result}")
                return False
            
            # Get properties
            info = EAF_INFO()
            result = eaf_lib.EAFGetProperty(self.eaf_id, ctypes.byref(info))
            if result == EAF_ERROR_CODE.EAF_SUCCESS:
                self.max_position = info.MaxStep
                name = info.name.decode('ascii')
                print(f"✓ Connected to {name}")
                print(f"  Max position: {self.max_position} steps")
            
            # Get initial position
            position = ctypes.c_int()
            result = eaf_lib.EAFGetPosition(self.eaf_id, ctypes.byref(position))
            if result == EAF_ERROR_CODE.EAF_SUCCESS:
                self.current_position = position.value
                print(f"  Current position: {self.current_position}")
            
            # Get temperature
            self._update_temperature()
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"✗ ZWO focuser connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from focuser"""
        if self.eaf_id >= 0:
            try:
                eaf_lib.EAFClose(self.eaf_id)
                print("✓ ZWO focuser disconnected")
            except:
                pass
        self.is_connected = False
        self.eaf_id = -1
    
    def get_position(self):
        """Get current position"""
        if not self.is_connected:
            return -1
        
        with self.lock:
            position = ctypes.c_int()
            result = eaf_lib.EAFGetPosition(self.eaf_id, ctypes.byref(position))
            if result == EAF_ERROR_CODE.EAF_SUCCESS:
                self.current_position = position.value
                return self.current_position
            return -1
    
    def _move_without_backlash(self, position):
        """
        Move to position (called by move_to with backlash logic)
        This is the low-level move that doesn't apply backlash compensation
        """
        if not self.is_connected:
            return False
        
        with self.lock:
            self.moving = True
            self.target_position = position
            
            result = eaf_lib.EAFMove(self.eaf_id, position)
            if result == EAF_ERROR_CODE.EAF_SUCCESS:
                # Wait for movement to complete
                while True:
                    time.sleep(0.05)
                    
                    # Check if still moving
                    is_moving = ctypes.c_bool()
                    result = eaf_lib.EAFIsMoving(self.eaf_id, ctypes.byref(is_moving))
                    
                    if result == EAF_ERROR_CODE.EAF_SUCCESS:
                        if not is_moving.value:
                            break
                    else:
                        print(f"✗ Error checking movement: {result}")
                        self.moving = False
                        return False
                
                # Get final position
                self.current_position = self.get_position()
                self.moving = False
                return True
            else:
                print(f"✗ Failed to move: {result}")
                self.moving = False
                return False
    
    def halt(self):
        """Stop movement immediately"""
        if not self.is_connected:
            return False
        
        result = eaf_lib.EAFStop(self.eaf_id)
        self.moving = False
        return result == EAF_ERROR_CODE.EAF_SUCCESS
    
    def is_moving(self):
        """Check if focuser is currently moving"""
        if not self.is_connected:
            return False
        
        is_moving = ctypes.c_bool()
        result = eaf_lib.EAFIsMoving(self.eaf_id, ctypes.byref(is_moving))
        if result == EAF_ERROR_CODE.EAF_SUCCESS:
            return is_moving.value
        return False
    
    def get_temperature(self):
        """Get temperature reading from focuser"""
        self._update_temperature()
        return self.temperature
    
    def _update_temperature(self):
        """Update temperature reading"""
        if not self.is_connected:
            return
        
        temp = ctypes.c_float()
        result = eaf_lib.EAFGetTemp(self.eaf_id, ctypes.byref(temp))
        if result == EAF_ERROR_CODE.EAF_SUCCESS:
            self.temperature = temp.value
    
    def reset_position(self, new_position=0):
        """Reset current position to new value (without moving)"""
        if not self.is_connected:
            return False
        
        result = eaf_lib.EAFResetPostion(self.eaf_id, new_position)
        if result == EAF_ERROR_CODE.EAF_SUCCESS:
            self.current_position = new_position
            print(f"✓ Position reset to {new_position}")
            return True
        return False
    
    def supported_actions(self):
        """ZWO EAF specific actions"""
        return [
            "Calibrate",           # Run calibration
            "GetFirmware",         # Get firmware version
            "SetMaxSpeed",         # Set maximum speed
            "GetMaxSpeed",         # Get maximum speed
            "ResetPosition"        # Reset position to zero
        ]

# ============================================================================
# Mock Focuser Implementation (for testing without hardware)
# ============================================================================

class MockFocuser(FocuserBase):
    """Mock focuser for testing without hardware"""
    
    def __init__(self, max_position=100000):
        super().__init__()
        self.max_position = max_position
        print(f"○ Mock focuser created (0-{max_position} steps)")
    
    def connect(self):
        """Simulate connection"""
        print("○ Mock focuser connecting...")
        time.sleep(0.5)
        self.is_connected = True
        self.current_position = self.max_position // 2  # Start at middle
        print(f"✓ Mock focuser connected")
        print(f"  Position: {self.current_position}")
        print(f"  Range: 0-{self.max_position}")
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        print("○ Mock focuser disconnected")
        self.is_connected = False
    
    def get_position(self):
        """Get current position"""
        return self.current_position
    
    def _move_without_backlash(self, position):
        """
        Simulate moving to position
        This is the low-level move that doesn't apply backlash compensation
        """
        if not self.is_connected:
            return False
        
        self.moving = True
        self.target_position = position
        
        # Simulate movement time (100 steps per second)
        steps = abs(position - self.current_position)
        move_time = steps / 100.0
        time.sleep(min(move_time, 5.0))  # Cap at 5 seconds for testing
        
        self.current_position = position
        self.moving = False
        
        return True
    
    def halt(self):
        """Stop movement"""
        if self.moving:
            print("○ Mock: Movement halted")
            self.moving = False
        return True
    
    def get_temperature(self):
        """Simulate temperature reading"""
        # Simulate slight temperature drift
        import random
        self.temperature = 20.0 + random.uniform(-0.5, 0.5)
        return self.temperature
    
    def supported_actions(self):
        """Mock focuser actions"""
        return [
            "Calibrate",
            "GetFirmware",
            "ResetPosition"
        ]

# ============================================================================
# Factory Function (selects ZWO or Mock based on availability and config)
# ============================================================================

def create_focuser(mode='auto', focuser_id=0, max_position=100000):
    """
    Factory function to create appropriate focuser instance
    
    Args:
        mode: 'auto', 'zwo', or 'mock'
        focuser_id: ZWO focuser ID (if multiple focusers)
        max_position: Maximum position for mock mode
    
    Returns:
        Focuser instance
    """
    if mode == 'mock':
        return MockFocuser(max_position)
    elif mode == 'zwo':
        if not ZWO_EAF_AVAILABLE:
            print("⚠ ZWO SDK not available, falling back to mock mode")
            return MockFocuser(max_position)
        return ZWOFocuser(focuser_id)
    elif mode == 'auto':
        # Auto-select: ZWO if available, otherwise mock
        if ZWO_EAF_AVAILABLE:
            return ZWOFocuser(focuser_id)
        else:
            return MockFocuser(max_position)
    else:
        raise ValueError(f"Unknown mode: {mode}")

# ============================================================================
# Legacy Focuser class (for backward compatibility)
# ============================================================================

class Focuser:
    """
    Legacy placeholder - redirects to factory function
    Use create_focuser() for new code
    """
    def __init__(self):
        print("⚠ Using legacy Focuser class")
        print("  Please update to use create_focuser() factory function")
        self.impl = create_focuser(mode='mock')
    
    def __getattr__(self, name):
        return getattr(self.impl, name)

# ============================================================================
# Test Code
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Focuser Test")
    print("=" * 60)
    
    # Test mock mode
    print("\n--- Testing Mock Mode ---")
    focuser = create_focuser(mode='mock', max_position=100000)
    focuser.connect()
    
    print(f"\nCurrent position: {focuser.get_position()}")
    print(f"Temperature: {focuser.get_temperature():.1f}°C")
    print(f"Max position: {focuser.max_position}")
    
    # Test backlash compensation
    print("\n--- Testing Backlash Compensation ---")
    focuser.set_backlash_compensation(100)
    
    start_pos = focuser.get_position()
    print(f"Starting position: {start_pos}")
    
    # Move outward
    print("\n1. Moving OUT...")
    focuser.move_to(start_pos + 5000)
    print(f"   Position: {focuser.get_position()}")
    
    # Move inward (direction change)
    print("\n2. Moving IN (direction change)...")
    focuser.move_to(focuser.get_position() - 3000)
    print(f"   Position: {focuser.get_position()}")
    
    # Move outward (direction change)
    print("\n3. Moving OUT (direction change)...")
    focuser.move_to(focuser.get_position() + 2000)
    print(f"   Position: {focuser.get_position()}")
    
    # Return to start
    print("\n4. Returning to start...")
    focuser.move_to(start_pos)
    print(f"   Final position: {focuser.get_position()}")
    
    # Test relative move
    print("\n--- Testing Relative Move ---")
    focuser.move_relative(5000)
    print(f"Position: {focuser.get_position()}")
    
    focuser.move_relative(-3000)
    print(f"Position: {focuser.get_position()}")
    
    focuser.disconnect()
    
    # Test ZWO mode if available
    if ZWO_EAF_AVAILABLE:
        print("\n--- Testing ZWO Mode ---")
        focuser_zwo = create_focuser(mode='zwo')
        if focuser_zwo.connect():
            print(f"Position: {focuser_zwo.get_position()}")
            print(f"Temperature: {focuser_zwo.get_temperature():.1f}°C")
            print(f"Max position: {focuser_zwo.max_position}")
            focuser_zwo.disconnect()
    
    print("\n✓ Focuser tests complete")
