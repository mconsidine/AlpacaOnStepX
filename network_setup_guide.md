# OnStepX Network Connection Setup Guide

## 🌐 What Changed

Your telescope driver now supports **BOTH** connection types:
- ✅ **Network (WiFi/Ethernet)** - YOUR CURRENT SETUP
- ✅ **USB Serial** - For future USB connections

You can easily switch between them with one config change!

---

## 🚀 Quick Setup (Network Connection)

### Step 1: Find Your OnStepX IP Address

**Option A: Check OnStepX Display/Web Interface**
- Most OnStepX controllers show IP on their display
- Or check your router's DHCP client list

**Option B: Scan Your Network**
```bash
cd ~/Downloads/alpaca-onstepx/
source venv/bin/activate
python test_telescope_connection.py scan 192.168.1
```

This will find all OnStepX devices on your network!

### Step 2: Update config.py

Open `config.py` and update:

```python
TELESCOPE_CONFIG = {
    'connection_type': 'network',  # ← Already set correctly
    
    'network': {
        'host': '192.168.1.100',   # ← CHANGE TO YOUR ONSTEPX IP
        'port': 9999,               # ← Standard port (don't change)
    },
    
    # ... (serial settings below - ignore for now)
}
```

### Step 3: Test the Connection

```bash
cd ~/Downloads/alpaca-onstepx/
source venv/bin/activate

# Test your specific IP
python test_telescope_connection.py network 192.168.1.100
```

**Expected Output:**
```
============================================================
Testing NETWORK Connection
============================================================
Host: 192.168.1.100
Port: 9999

Attempting connection...

✓ CONNECTION SUCCESSFUL!

Testing basic commands:
----------------------------------------
Product:    OnStep
Firmware:   4.21e
RA:         10.5432 hours
Dec:        45.1234 degrees
Tracking:   ON
Latitude:   40.7128 degrees
Longitude:  -74.0060 degrees

✓ All tests passed!
✓ Disconnected cleanly
```

### Step 4: Run the Full Server

```bash
python main.py
```

You should see:
```
Initializing devices...
  Telescope configured for NETWORK connection to 192.168.1.100:9999
✓ Telescope initialized (call connect() to establish connection)
```

---

## 🔧 Troubleshooting Network Connection

### "Connection refused"

**Check 1:** Is OnStepX powered on and WiFi enabled?

**Check 2:** Ping the OnStepX
```bash
ping 192.168.1.100
```

**Check 3:** Try the web interface
```
http://192.168.1.100
```
If you can access the web interface, the IP is correct!

**Check 4:** Verify port 9999 is open
```bash
nc -zv 192.168.1.100 9999
```

### "Connection timeout"

- **Wrong IP address** - Use the scan tool to find it
- **Different subnet** - OnStepX might be on 192.168.0.x instead of 192.168.1.x
- **WiFi not enabled** on OnStepX

### "No response from OnStepX"

- **Wrong port** - Should be 9999 (standard)
- **Firewall blocking** - Check Pi firewall:
  ```bash
  sudo ufw allow out 9999/tcp
  ```

---

## 🔄 Switching to USB (Future Use)

If you ever want to use USB instead of WiFi:

### Step 1: Update config.py

```python
TELESCOPE_CONFIG = {
    'connection_type': 'serial',  # ← Change to 'serial'
    
    # ... (network settings above - ignore)
    
    'serial': {
        'port': '/dev/ttyUSB0',    # ← USB port
        'baudrate': 9600,
        'timeout': 2,
        'auto_detect_port': True
    }
}
```

### Step 2: Test Serial Connection

```bash
python test_telescope_connection.py serial /dev/ttyUSB0
```

### Step 3: Check Permissions

If you get "Permission denied":
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for this to take effect
```

---

## 📊 Connection Comparison

| Feature | Network (WiFi) | USB Serial |
|---------|----------------|------------|
| **Range** | Anywhere on WiFi | Cable length only |
| **Speed** | Fast | Slower |
| **Setup** | Need IP address | Plug and play |
| **Reliability** | Depends on WiFi | Very reliable |
| **Your Setup** | ✅ **Current** | Available |

---

## 🎯 What to Test

Once the server is running:

1. **Test Connection in N.I.N.A.**
   - Equipment → Telescope → Choose ASCOM
   - Server should auto-discover via UDP
   - Click Connect

2. **Verify Position Reading**
   - Should show current RA/Dec
   - Updates every second

3. **Test Tracking**
   - Enable/disable tracking
   - Change tracking rate

4. **Test Slewing**
   - Slew to coordinates
   - Verify mount responds

---

## 🔐 Network Security Notes

**Current Status:** No authentication required

**Recommendation:** Use a private network or VPN if concerned about security

**Future:** Could add authentication layer if needed

---

## 📝 Common OnStepX Network Ports

- **9999** - Standard command port (LX200 protocol)
- **80** - Web interface
- **32227** - Alpaca discovery (your Pi, not OnStepX)

---

## ✅ Success Checklist

- [ ] Found OnStepX IP address
- [ ] Updated config.py with correct IP
- [ ] Test script connects successfully
- [ ] Server starts without errors
- [ ] N.I.N.A. discovers and connects
- [ ] Can read telescope position

---

## 🆘 Still Having Issues?

Run the diagnostic:
```bash
cd ~/Downloads/alpaca-onstepx/
source venv/bin/activate

# Full diagnostic
python test_telescope_connection.py scan
python test_telescope_connection.py network <your-ip>
```

Check the output and let me know what errors you see!

---

## 📚 Technical Details

### Network Protocol
- **Type:** TCP/IP socket connection
- **Port:** 9999 (configurable)
- **Protocol:** LX200-compatible command set
- **Format:** ASCII text commands ending with `#`

### Example Commands
```
:GR#  - Get Right Ascension
:GD#  - Get Declination
:MS#  - Slew to target
:Q#   - Stop slewing
```

### Connection Flow
1. Create TCP socket
2. Connect to OnStepX IP:9999
3. Send `:GVP#` to verify connection
4. Commands/responses are ASCII text
5. All responses end with `#`

---

**Your network setup is now complete! The telescope will connect via WiFi, and you can always switch to USB later by changing one config setting.** 🎉
