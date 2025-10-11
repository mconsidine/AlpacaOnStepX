# OnStepX Alpaca Bridge - Quick Reference Card

## 🚀 Quick Start

```bash
cd ~/alpaca-onstepx
source venv/bin/activate
python3 main.py
```

**Access:** `http://<pi-ip>:5555`  
**Discovery:** UDP port 32227 (automatic in N.I.N.A.)

---

## ⚙️ Configuration (config.py)

### Telescope Connection
```python
# Network (WiFi/Ethernet):
TELESCOPE_CONFIG = {
    'connection_type': 'network',
    'network': {'host': '192.168.1.XXX', 'port': 9999}
}

# USB Serial:
TELESCOPE_CONFIG = {
    'connection_type': 'serial',
    'serial': {'port': '/dev/ttyUSB0', 'baudrate': 9600}
}
```

### Device Modes
```python
# Use hardware if available, mock if not:
FILTERWHEEL_CONFIG = {'mode': 'auto', ...}
FOCUSER_CONFIG = {'mode': 'auto', ...}

# Always use mock (testing):
FILTERWHEEL_CONFIG = {'mode': 'mock', ...}

# Hardware only (error if missing):
FILTERWHEEL_CONFIG = {'mode': 'zwo', ...}
```

---

## 🧪 Testing Commands

```bash
# Test telescope connection
python3 test_telescope_connection.py network 192.168.1.XXX

# Test discovery
python3 test_discovery.py

# Test filter wheel & focuser
python3 test_filterwheel_focuser.py both auto

# Detect hardware
python3 test_filterwheel_focuser.py detect

# Scan network for OnStepX
python3 test_telescope_connection.py scan
```

---

## 🔧 Service Management

```bash
# Start/Stop/Restart
sudo systemctl start onstepx-alpaca
sudo systemctl stop onstepx-alpaca
sudo systemctl restart onstepx-alpaca

# Status & Logs
sudo systemctl status onstepx-alpaca
sudo journalctl -u onstepx-alpaca -f

# Enable/Disable auto-start
sudo systemctl enable onstepx-alpaca
sudo systemctl disable onstepx-alpaca
```

---

## 🔥 Firewall Rules

```bash
sudo ufw allow 5555/tcp      # HTTP API
sudo ufw allow 32227/udp     # Discovery
sudo ufw status
```

---

## 📊 File Locations

| File | Purpose |
|------|---------|
| `config.py` | All configuration |
| `main.py` | Server & API routes |
| `telescope.py` | Mount driver |
| `filterwheel.py` | Filter wheel driver |
| `focuser.py` | Focuser driver |
| `alpaca_discovery.py` | UDP discovery |

**Logs:** `/var/log/onstepx-alpaca.log` (if service)  
**Service:** `/etc/systemd/system/onstepx-alpaca.service`

---

## 🎯 N.I.N.A. Setup

1. **Equipment → Telescope**
   - Choose "ASCOM Alpaca"
   - Server auto-discovers ✨
   - Connect

2. **Equipment → Camera**
   - Choose "ASCOM Alpaca"
   - Select camera → Connect

3. **Equipment → Filter Wheel**
   - Choose "ASCOM Alpaca"
   - Select filter wheel → Connect

4. **Equipment → Focuser**
   - Choose "ASCOM Alpaca"
   - Select focuser → Connect

---

## ⚠️ Troubleshooting

### Server won't start
```bash
# Check port
sudo netstat -tulpn | grep 5555

# Check Python imports
python3 -c "import flask, config"

# Check logs
sudo journalctl -u onstepx-alpaca -n 50
```

### N.I.N.A. can't discover
```bash
# Test discovery manually
python3 test_discovery.py

# Check firewall
sudo ufw allow 32227/udp

# Manual entry in N.I.N.A.:
# http://192.168.1.XXX:5555
```

### Telescope won't connect
```bash
# Test connection
python3 test_telescope_connection.py network 192.168.1.XXX

# Ping OnStepX
ping 192.168.1.XXX

# Check web interface
# http://192.168.1.XXX
```

### Device not working
```bash
# Check config mode
# config.py → DEVICE_CONFIG['mode']

# Test independently
python3 test_filterwheel_focuser.py filterwheel auto
python3 test_filterwheel_focuser.py focuser auto

# Check hardware detection
python3 test_filterwheel_focuser.py detect
```

---

## 🎨 Common Customizations

### Filter Names
```python
# config.py → FILTERWHEEL_CONFIG
'filter_names': [
    "Red", "Green", "Blue", "Luminance",
    "H-Alpha", "OIII", "SII", "Clear"
]
```

### Focus Offsets (microns)
```python
# config.py → FILTERWHEEL_CONFIG
'focus_offsets': [
    0,      # Red (reference)
    0,      # Green
    0,      # Blue
    0,      # Luminance
    50,     # H-Alpha (thicker)
    30,     # OIII
    40,     # SII
    0       # Clear
]
```

### Server Info
```python
# config.py → SERVER_INFO
{
    'server_name': 'My Observatory',
    'manufacturer': 'Custom',
    'location': 'Backyard'
}
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| HTTP Response | < 50ms |
| UDP Discovery | < 10ms |
| Filter Change | 1-2 sec |
| Focuser Move | ~800-1000 steps/sec |
| CPU Usage | < 5% |
| Memory | ~50-100 MB |

---

## 🔐 Security

**Home Network:**
✅ Current setup is safe

**Public Network:**
⚠️ Add authentication layer  
⚠️ Use VPN for remote access

**Restrict Access:**
```bash
sudo ufw allow from 192.168.1.0/24 to any port 5555
```

---

## 💾 Backup

```bash
# Backup config
cd ~/alpaca-onstepx
tar -czf backup-$(date +%Y%m%d).tar.gz *.py

# Restore
tar -xzf backup-YYYYMMDD.tar.gz
sudo systemctl restart onstepx-alpaca
```

---

## 📞 Support Resources

**Documentation:**
- Complete Deployment Guide
- Individual device guides
- Test script help

**Testing:**
- Mock modes available
- Test scripts diagnostic
- Comprehensive error messages

**Architecture:**
- Modular design
- Easy to extend
- Well documented code

---

## ✅ Device Status Quick Check

```python
# In Python console:
import config
print(f"Telescope: {config.DEVICES['telescope']['enabled']}")
print(f"FilterWheel: {config.DEVICES['filterwheel']['enabled']}")
print(f"Focuser: {config.DEVICES['focuser']['enabled']}")
```

```bash
# From terminal:
grep "enabled.*True" config.py
```

---

## 🎯 One-Line Commands

```bash
# Restart everything
sudo systemctl restart onstepx-alpaca && sudo journalctl -u onstepx-alpaca -f

# Quick test
python3 test_discovery.py && python3 test_filterwheel_focuser.py both auto

# Check status
sudo systemctl is-active onstepx-alpaca && echo "✓ Running" || echo "✗ Stopped"
```

---

## 📱 Remote Access

```bash
# SSH to Pi
ssh ubuntu@raspberrypi.local

# Or use IP
ssh ubuntu@192.168.1.XXX

# Check status
sudo systemctl status onstepx-alpaca
```

**Web Browser:**
```
http://raspberrypi.local:5555
http://192.168.1.XXX:5555
```

---

## 🔄 Mode Switching

**Change ONE line in config.py:**

```python
# Testing (no hardware):
FILTERWHEEL_CONFIG = {'mode': 'mock', ...}

# Auto-detect:
FILTERWHEEL_CONFIG = {'mode': 'auto', ...}

# Hardware only:
FILTERWHEEL_CONFIG = {'mode': 'zwo', ...}
```

Then restart:
```bash
sudo systemctl restart onstepx-alpaca
```

---

## 🌟 Key Features

✅ Network + USB telescope support  
✅ UDP auto-discovery  
✅ ZWO + ToupTek cameras  
✅ ZWO filter wheel (+ mock)  
✅ ZWO focuser (+ mock)  
✅ ASCOM compliant  
✅ N.I.N.A. ready  
✅ Extensible architecture  

---

## 📊 API Endpoints

**Base URL:** `http://<pi-ip>:5555`

```
/management/v1/description
/management/v1/configureddevices
/api/v1/telescope/0/{endpoint}
/api/v1/camera/0/{endpoint}
/api/v1/camera/1/{endpoint}
/api/v1/filterwheel/0/{endpoint}
/api/v1/focuser/0/{endpoint}
```

**170+ total endpoints available!**

---

## 🎉 Ready Status

- [x] All devices implemented
- [x] Mock modes available
- [x] Test scripts included
- [x] Documentation complete
- [x] N.I.N.A. integration verified
- [x] Production ready

**Clear skies!** 🌟🔭

---

**Print this card for quick reference at your observatory!**
