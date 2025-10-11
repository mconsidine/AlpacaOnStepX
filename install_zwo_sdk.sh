#!/bin/bash
# install_zwo_sdk.sh
# ZWO ASI SDK installation for ARM64 (Raspberry Pi 5)

set -e

echo "=================================="
echo "ZWO ASI SDK Installation"
echo "=================================="

# Check architecture
ARCH=$(uname -m)
if [ "$ARCH" != "aarch64" ]; then
    echo "Warning: This script is designed for ARM64 (aarch64) architecture"
    echo "Current architecture: $ARCH"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create SDK directory
SDK_DIR="$HOME/Downloads/camera_sdks/zwo"
echo "Creating SDK directory: $SDK_DIR"
mkdir -p "$SDK_DIR"
cd "$SDK_DIR"

# Download ZWO ASI SDK
echo "Downloading ZWO ASI SDK..."

# ZWO SDK download URL (check https://astronomy-imaging-camera.com/software for latest version)
# SDK_URL="https://astronomy-imaging-camera.com/software/ZWO_ASI_Linux_Mac_SDK_V1.36.tar.bz2"
SDK_URL="https://dl.zwoastro.com/software?app=DeveloperCameraSdk&platform=linux&region=Overseas"

if command -v wget >/dev/null 2>&1; then
#    wget "$SDK_URL" -O zwo_asi_sdk.tar.bz2 || {
    wget --user-agent="Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36" \
         --content-disposition \
         --trust-server-names \
         "$SDK_URL" \
         -O zwo_asi_sdk.zip || { 
        echo "Failed to download SDK automatically."
        echo "Please manually download the ZWO ASI SDK from:"
        echo "https://astronomy-imaging-camera.com/software"
        echo "Save it as zwo_asi_sdk.tar.bz2 in $SDK_DIR"
        read -p "Press Enter when you have downloaded the file..."
    }
elif command -v curl >/dev/null 2>&1; then
#    curl -L "$SDK_URL" -o zwo_asi_sdk.tar.bz2 || {
    curl -L \
         -H "User-Agent: Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36" \
         -H "Accept: application/octet-stream,*/*" \
         -o zwo_asi_sdk.zip \
         "$SDK_URL" || {
        echo "Failed to download SDK automatically."
        echo "Please manually download the ZWO ASI SDK from:"
        echo "https://astronomy-imaging-camera.com/software"
        echo "Save it as zwo_asi_sdk.tar.bz2 in $SDK_DIR"
        read -p "Press Enter when you have downloaded the file..."
    }
else
    echo "Neither wget nor curl found."
    echo "Please manually download the ZWO ASI SDK from:"
    echo "https://astronomy-imaging-camera.com/software"
    echo "Save it as zwo_asi_sdk.tar.bz2 in $SDK_DIR"
    read -p "Press Enter when you have downloaded the file..."
fi

# Verify download
# if [ ! -f "zwo_asi_sdk.tar.bz2" ]; then
if [ ! -f "zwo_asi_sdk.zip" ]; then
    echo "Error: zwo_asi_sdk.tar.bz2 not found in $SDK_DIR"
    echo "Please download the SDK manually and try again."
    exit 1
fi

# Extract SDK
echo "Extracting ZWO ASI SDK..."
# tar -xjf zwo_asi_sdk.tar.bz2
unzip zwo_asi_sdk.zip

# Find the extracted directory (name may vary)
 SDK_EXTRACTED_DIR=$(find . -name "*ASI*SDK*" -type d | head -n 1)
#SDK_EXTRACTED_DIR=$(find ~ -name "*ASI_linux*SDK_V*" -type d | head -n 1)
if [ -z "$SDK_EXTRACTED_DIR" ]; then
    echo "Error: Could not find extracted SDK directory"
    echo "Looking for directories..."
    find . -type d -name "*ASI*" -o -name "*ZWO*" -o -name "*SDK*"
    exit 1
fi

echo "Found SDK directory: $SDK_EXTRACTED_DIR"
cd "$SDK_EXTRACTED_DIR"

# Install libraries for ARM64
echo "Installing ZWO ASI libraries..."

LINUX_ARCHIVE=$(find . -name "*ASI_linux*SDK_V*" -type f | head -n 1)
tar -xjf $LINUX_ARCHIVE
LINUX_FOLDER=$(find . -name "*ASI_linux*SDK_V*" -type d | head -n 1)
cd $LINUX_FOLDER

# Check for ARM64 libraries
if [ -d "lib/arm64" ]; then
    ARM64_LIB_DIR="lib/arm64"
elif [ -d "lib/armv8" ]; then
    ARM64_LIB_DIR="lib/armv8"
elif [ -d "lib/aarch64" ]; then
    ARM64_LIB_DIR="lib/aarch64"
elif [ -d "lib/linux/arm64" ]; then
    ARM64_LIB_DIR="lib/linux/arm64"
else
    echo "Error: ARM64 libraries not found in SDK"
    echo "Available library directories:"
    find . -name "lib" -type d -exec find {} -type d \;
    exit 1
fi

echo "Using library directory: $ARM64_LIB_DIR"

# Copy libraries to system directory
sudo cp "$ARM64_LIB_DIR"/libASICamera2.so* /usr/local/lib/ 2>/dev/null || {
    echo "Warning: Could not copy .so files, trying alternative patterns..."
    sudo cp "$ARM64_LIB_DIR"/*ASI* /usr/local/lib/ 2>/dev/null || {
        echo "Error: Could not find ASI library files"
        echo "Contents of $ARM64_LIB_DIR:"
        ls -la "$ARM64_LIB_DIR"
        exit 1
    }
}

# Install header files
echo "Installing ZWO ASI header files..."

if [ -f "include/ASICamera2.h" ]; then
    sudo cp include/ASICamera2.h /usr/local/include/
elif [ -f "inc/ASICamera2.h" ]; then
    sudo cp inc/ASICamera2.h /usr/local/include/
else
    echo "Error: ASICamera2.h header file not found"
    echo "Looking for header files..."
    find . -name "*.h" -type f
    exit 1
fi

# Update library cache
echo "Updating library cache..."
sudo ldconfig

# Install udev rules for USB permissions
echo "Installing udev rules..."

# Check if SDK includes udev rules
if [ -f "asi.rules" ]; then
    sudo cp asi.rules /etc/udev/rules.d/99-asi.rules
elif [ -f "udev/asi.rules" ]; then
    sudo cp udev/asi.rules /etc/udev/rules.d/99-asi.rules
else
    echo "Creating udev rules for ZWO ASI cameras..."
    # Create udev rule for ZWO ASI cameras
    sudo tee /etc/udev/rules.d/99-asi.rules << 'EOF'
# ZWO ASI camera USB permissions
# ZWO vendor ID: 03c3
SUBSYSTEM=="usb", ATTR{idVendor}=="03c3", MODE="0666", GROUP="plugdev"

# ZWO cameras by product name
SUBSYSTEM=="usb", ATTR{product}=="*ASI*", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{product}=="*ZWO*", MODE="0666", GROUP="plugdev"

# Specific ZWO ASI camera models
SUBSYSTEM=="usb", ATTR{idVendor}=="03c3", ATTR{idProduct}=="120*", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="03c3", ATTR{idProduct}=="174*", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="03c3", ATTR{idProduct}=="183*", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="03c3", ATTR{idProduct}=="224*", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="03c3", ATTR{idProduct}=="294*", MODE="0666", GROUP="plugdev"
EOF
fi

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add user to plugdev group
sudo usermod -a -G plugdev $USER

# Create test program
echo "Creating test program..."

tee "$HOME/test_zwo_asi.cpp" << 'EOF'
#include <iostream>
#include <ASICamera2.h>

int main() {
    std::cout << "Testing ZWO ASI SDK..." << std::endl;
    
    // Get number of connected cameras
    int numCameras = ASIGetNumOfConnectedCameras();
    std::cout << "Found " << numCameras << " ZWO ASI camera(s)" << std::endl;
    
    if (numCameras > 0) {
        for (int i = 0; i < numCameras; i++) {
            ASI_CAMERA_INFO cameraInfo;
            if (ASIGetCameraProperty(&cameraInfo, i) == ASI_SUCCESS) {
                std::cout << "Camera " << i << ":" << std::endl;
                std::cout << "  Name: " << cameraInfo.Name << std::endl;
                std::cout << "  Camera ID: " << cameraInfo.CameraID << std::endl;
                std::cout << "  Max Height: " << cameraInfo.MaxHeight << std::endl;
                std::cout << "  Max Width: " << cameraInfo.MaxWidth << std::endl;
                std::cout << "  Is Color Camera: " << (cameraInfo.IsColorCam ? "Yes" : "No") << std::endl;
                std::cout << "  Bayer Pattern: " << cameraInfo.BayerPattern << std::endl;
                std::cout << "  Supported Bins: ";
                for (int j = 0; j < 16; j++) {
                    if (cameraInfo.SupportedBins[j] == 0) break;
                    std::cout << cameraInfo.SupportedBins[j] << " ";
                }
                std::cout << std::endl;
                std::cout << "  Pixel Size: " << cameraInfo.PixelSize << " um" << std::endl;
                std::cout << "  Mechanical Shutter: " << (cameraInfo.MechanicalShutter ? "Yes" : "No") << std::endl;
                std::cout << "  ST4 Port: " << (cameraInfo.ST4Port ? "Yes" : "No") << std::endl;
                std::cout << "  Is Cooler Camera: " << (cameraInfo.IsCoolerCam ? "Yes" : "No") << std::endl;
                std::cout << "  Is USB3 Host: " << (cameraInfo.IsUSB3Host ? "Yes" : "No") << std::endl;
                std::cout << "  Is USB3 Camera: " << (cameraInfo.IsUSB3Camera ? "Yes" : "No") << std::endl;
                std::cout << "  Elec Per ADU: " << cameraInfo.ElecPerADU << std::endl;
                std::cout << "  Bit Depth: " << cameraInfo.BitDepth << std::endl;
                std::cout << "  Is Trigger Camera: " << (cameraInfo.IsTriggerCam ? "Yes" : "No") << std::endl;
                std::cout << std::endl;
            }
        }
        std::cout << "ZWO ASI SDK installation successful!" << std::endl;
        return 0;
    } else {
        std::cout << "No cameras detected. Check USB connection." << std::endl;
        return 1;
    }
}
EOF

# Compile test program
echo "Compiling test program..."
if g++ -o "$HOME/test_zwo_asi" "$HOME/test_zwo_asi.cpp" -lASICamera2 -lpthread; then
    echo "✓ Test program compiled successfully"
else
    echo "✗ Test program compilation failed"
    echo "This may indicate SDK installation issues"
fi

# Verify installation
echo "Verifying installation..."

# Check if library is installed
if ldconfig -p | grep -q ASICamera2; then
    echo "✓ ZWO ASI library found in system"
else
    echo "✗ ZWO ASI library not found in system"
fi

# Check if header is installed
if [ -f "/usr/local/include/ASICamera2.h" ]; then
    echo "✓ ZWO ASI header file installed"
else
    echo "✗ ZWO ASI header file not found"
fi

# Check USB permissions
if groups $USER | grep -q plugdev; then
    echo "✓ User is in plugdev group"
else
    echo "✗ User not in plugdev group (reboot required)"
fi

# Check for USB 3.0 optimization
echo "Checking USB 3.0 configuration..."
USB_MEMORY=$(cat /sys/module/usbcore/parameters/usbfs_memory_mb 2>/dev/null || echo "default")
echo "  USB memory buffer: ${USB_MEMORY} MB"

if [ "$USB_MEMORY" = "default" ] || [ "$USB_MEMORY" -lt 1000 ]; then
    echo "  Recommendation: Increase USB buffer with system_optimization.sh"
fi

echo "=================================="
echo "ZWO ASI SDK Installation Summary"
echo "=================================="
echo
echo "Installation completed!"
echo
echo "Files installed:"
echo "  Libraries: /usr/local/lib/libASICamera2.so*"
echo "  Headers: /usr/local/include/ASICamera2.h"
echo "  Udev rules: /etc/udev/rules.d/99-asi.rules"
echo
echo "Test program: ~/test_zwo_asi"
echo
echo "To test the installation:"
echo "1. Connect your ZWO ASI camera"
echo "2. Run: ~/test_zwo_asi"
echo
echo "If no cameras are detected:"
echo "1. Check USB connection (use USB 3.0 port for best performance)"
echo "2. Reboot (for udev rules and group membership)"
echo "3. Check 'lsusb' for ZWO devices (vendor ID 03c3)"
echo "4. Ensure camera has external power if required"
echo
echo "For ROS2 integration:"
echo "1. The SDK is now available for CMake"
echo "2. Use find_library(ASI_LIBRARY ASICamera2)"
echo "3. Use find_path(ASI_INCLUDE_DIR ASICamera2.h)"
echo
echo "Performance tips:"
echo "1. Use USB 3.0 ports for maximum bandwidth"
echo "2. Run system_optimization.sh for USB buffer tuning"
echo "3. Consider external powered USB hub for multiple cameras"
echo
if  ! groups $USER | grep -q plugdev ; then
    echo "IMPORTANT: Reboot required for USB permissions!"
fi
