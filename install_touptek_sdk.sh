#!/bin/bash
# install_touptek_sdk.sh
# ToupTek SDK installation for ARM64 (Raspberry Pi 5)

set -e

echo "=================================="
echo "ToupTek SDK Installation"
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
SDK_DIR="$HOME/Downloads/camera_sdks/touptek"
echo "Creating SDK directory: $SDK_DIR"
mkdir -p "$SDK_DIR"
cd "$SDK_DIR"

# Download ToupTek SDK
echo "Downloading ToupTek SDK..."

# Note: You'll need to get the actual download URL from ToupTek website
# This is a placeholder - check https://www.touptek.com/download/ for the latest version
# SDK_URL="https://www.touptek.com/upload/download/toupcamsdk.tar.gz"
SDK_URL="https://www.touptek-astro.com/dl_software/toupcamsdk.20250824.zip"

if command -v wget >/dev/null 2>&1; then
    wget "$SDK_URL" -O toupcamsdk.tar.gz || {
        echo "Failed to download SDK automatically."
        echo "Please manually download the ToupTek SDK from:"
        echo "https://www.touptek-astro.com/downloads/"
        echo "Save it as toupcamsdk.tar.gz in $SDK_DIR"
        read -p "Press Enter when you have downloaded the file..."
    }
elif command -v curl >/dev/null 2>&1; then
    curl -L "$SDK_URL" -o toupcamsdk.tar.gz || {
        echo "Failed to download SDK automatically."
        echo "Please manually download the ToupTek SDK from:"
        echo "https://www.touptek.com/download/"
        echo "Save it as toupcamsdk.tar.gz in $SDK_DIR"
        read -p "Press Enter when you have downloaded the file..."
    }
else
    echo "Neither wget nor curl found."
    echo "Please manually download the ToupTek SDK from:"
    echo "https://www.touptek-astro.com/downloads/"
    echo "Save it as toupcamsdk.tar.gz in $SDK_DIR"
    read -p "Press Enter when you have downloaded the file..."
fi

# Verify download
if [ ! -f "toupcamsdk.tar.gz" ]; then
    echo "Error: toupcamsdk.tar.gz not found in $SDK_DIR"
    echo "Please download the SDK manually and try again."
    exit 1
fi

# Extract SDK
echo "Extracting ToupTek SDK..."
#tar -xzf toupcamsdk.tar.gz
mv toupcamsdk.tar.gz toupcamsdk.zip
unzip toupcamsdk.zip

# Find the extracted directory (name may vary)
# SDK_EXTRACTED_DIR=$(find . -name "*toupcam*" -type d | head -n 1)
SDK_EXTRACTED_DIR=$SDK_DIR
if [ -z "$SDK_EXTRACTED_DIR" ]; then
    echo "Error: Could not find extracted SDK directory"
    echo "Please check the archive contents and adjust the script"
    exit 1
fi

echo "Found SDK directory: $SDK_EXTRACTED_DIR"
cd "$SDK_EXTRACTED_DIR"

# Install libraries for ARM64
echo "Installing ToupTek libraries..."

# Check for ARM64 libraries
if [ -d "lib/linux/arm64" ]; then
    ARM64_LIB_DIR="lib/linux/arm64"
elif [ -d "lib/arm64" ]; then
    ARM64_LIB_DIR="lib/arm64"
elif [ -d "lib/aarch64" ]; then
    ARM64_LIB_DIR="lib/aarch64"
elif [ -d "linux/arm64" ]; then
    ARM64_LIB_DIR="linux/arm64"
else
    echo "Error: ARM64 libraries not found in SDK"
    echo "Available library directories:"
    find . -name "lib" -type d -exec find {} -type d \;
    exit 1
fi

echo "Using library directory: $ARM64_LIB_DIR"

# Copy libraries to system directory
sudo cp "$ARM64_LIB_DIR"/libtoupcam.so* /usr/local/lib/ 2>/dev/null || {
    echo "Warning: Could not copy .so files, trying alternative patterns..."
    sudo cp "$ARM64_LIB_DIR"/*toupcam* /usr/local/lib/ 2>/dev/null || {
        echo "Error: Could not find ToupTek library files"
        echo "Contents of $ARM64_LIB_DIR:"
        ls -la "$ARM64_LIB_DIR"
        exit 1
    }
}

# Install header files
echo "Installing ToupTek header files..."

if [ -f "inc/toupcam.h" ]; then
    sudo cp inc/toupcam.h /usr/local/include/
elif [ -f "include/toupcam.h" ]; then
    sudo cp include/toupcam.h /usr/local/include/
else
    echo "Error: toupcam.h header file not found"
    echo "Looking for header files..."
    find . -n "*.h" -type f
    exit 1
fi

# Update library cache
echo "Updating library cache..."
sudo ldconfig

# Install udev rules for USB permissions
echo "Installing udev rules..."

# Create udev rule for ToupTek cameras
sudo tee /etc/udev/rules.d/99-touptek.rules << 'EOF'
# ToupTek camera USB permissions
# ToupTek vendor IDs: 0547, 1618
SUBSYSTEM=="usb", ATTR{idVendor}=="0547", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="1618", MODE="0666", GROUP="plugdev"

# ToupTek cameras by product name
SUBSYSTEM=="usb", ATTR{product}=="*ToupCam*", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{product}=="*ToupTek*", MODE="0666", GROUP="plugdev"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add user to plugdev group
sudo usermod -a -G plugdev $USER

# Create test program
echo "Creating test program..."

tee "$HOME/test_touptek.cpp" << 'EOF'
#include <iostream>
#include <toupcam.h>

int main() {
    std::cout << "Testing ToupTek SDK..." << std::endl;
    
    // Enumerate cameras
    ToupcamDeviceV2 cameras[16];
    unsigned count = Toupcam_EnumV2(cameras);
    
    std::cout << "Found " << count << " ToupTek camera(s)" << std::endl;
    
    for (unsigned i = 0; i < count; i++) {
        std::cout << "Camera " << i << ": " << cameras[i].displayname << std::endl;
        std::cout << "  Model: " << cameras[i].model->name << std::endl;
        std::cout << "  ID: " << cameras[i].id << std::endl;
    }
    
    if (count > 0) {
        std::cout << "ToupTek SDK installation successful!" << std::endl;
        return 0;
    } else {
        std::cout << "No cameras detected. Check USB connection." << std::endl;
        return 1;
    }
}
EOF

# Compile test program
echo "Compiling test program..."
if g++ -o "$HOME/test_touptek" "$HOME/test_touptek.cpp" -ltoupcam; then
    echo "✓ Test program compiled successfully"
else
    echo "✗ Test program compilation failed"
    echo "This may indicate SDK installation issues"
fi

# Verify installation
echo "Verifying installation..."

# Check if library is installed
if ldconfig -p | grep -q toupcam; then
    echo "✓ ToupTek library found in system"
else
    echo "✗ ToupTek library not found in system"
fi

# Check if header is installed
if [ -f "/usr/local/include/toupcam.h" ]; then
    echo "✓ ToupTek header file installed"
else
    echo "✗ ToupTek header file not found"
fi

# Check USB permissions
if groups $USER | grep -q plugdev; then
    echo "✓ User is in plugdev group"
else
    echo "✗ User not in plugdev group (reboot required)"
fi

echo "=================================="
echo "ToupTek SDK Installation Summary"
echo "=================================="
echo
echo "Installation completed!"
echo
echo "Files installed:"
echo "  Libraries: /usr/local/lib/libtoupcam.so*"
echo "  Headers: /usr/local/include/toupcam.h"
echo "  Udev rules: /etc/udev/rules.d/99-touptek.rules"
echo
echo "Test program: ~/test_touptek"
echo
echo "To test the installation:"
echo "1. Connect your ToupTek camera"
echo "2. Run: ~/test_touptek"
echo
echo "If no cameras are detected:"
echo "1. Check USB connection"
echo "2. Reboot (for udev rules and group membership)"
echo "3. Check 'lsusb' for ToupTek devices"
echo
echo "For ROS2 integration:"
echo "1. The SDK is now available for CMake"
echo "2. Use find_library(TOUPTEK_LIBRARY toupcam)"
echo "3. Use find_path(TOUPTEK_INCLUDE_DIR toupcam.h)"
echo
if  ! groups $USER | grep -q plugdev ; then
    echo "IMPORTANT: Reboot required for USB permissions!"
fi
