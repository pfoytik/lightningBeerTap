# Lightning Payment Solenoid Controller

A Bitcoin Lightning Network payment-activated solenoid valve controller using Raspberry Pi Zero W and LNbits.

## 🚀 Project Overview

This system monitors an LNbits Lightning wallet for incoming payments and automatically activates a 12V solenoid valve when payments are received. Perfect for Bitcoin-powered dispensers, irrigation systems, or any application requiring payment-activated hardware control.

## ⚡ Features

- **Real-time Lightning payment detection** via LNbits API
- **Reliable payment verification** using dedicated payment status endpoints
- **Hardware control** via GPIO relay switching
- **Smart filtering** - only new payments trigger activation (ignores historical)
- **Configurable minimum payment amounts**
- **Automatic reconnection** and error handling
- **Detailed logging** for monitoring and debugging

## 🛠 Hardware Requirements

### Core Components
- **Raspberry Pi Zero W** (with WiFi)
- **MicroSD card** (8GB+, Class 10 recommended)
- **5V Relay Module** (3-terminal: COM, NO, NC)
- **12V Solenoid Valve** (2-wire)
- **12V Power Supply** (appropriate amperage for your solenoid)
- **Jumper wires** for connections

### Optional
- **Micro-USB to USB-A hub** (for keyboard/mouse during setup)
- **Mini-HDMI to HDMI cable** (for monitor during setup)

## 📋 Software Requirements

- **Raspberry Pi OS** (32-bit recommended for Pi Zero W)
- **Python 3** with pip
- **LNbits server** (self-hosted or hosted instance)
- **Lightning wallet** for testing

## 🔧 Installation

### 1. Prepare Raspberry Pi

**Flash SD Card:**
```bash
# Use Raspberry Pi Imager to flash 32-bit Pi OS
# Add these files to boot partition:
```

**boot/ssh** (empty file)
```
# Empty file to enable SSH
```

**boot/wpa_supplicant.conf**
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourWiFiName"
    psk="YourWiFiPassword"
}
```

**boot/userconf**
```
pi:$6$rBoByrWl$XJLBvk.VwYP47B/H6gTsWUgKPIE7zWNPKxaGpGjEA7i5Us3pM4.aWRxSlRQG5dRx5B6LfGLc4pWb.Zqj1oXK1
```

### 2. SSH Setup

**Find Pi IP Address:**
```bash
# From your computer on same network:
nmap -sn 192.168.1.0/24    # Adjust subnet as needed
```

**Connect via SSH:**
```bash
ssh pi@[pi-ip-address]
# Default password: raspberry
```

### 3. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python packages
pip3 install RPi.GPIO requests

# Add user to GPIO group
sudo usermod -a -G gpio pi
```

### 4. Deploy Code

**Create the main script:**
```bash
nano /home/pi/lightning_solenoid.py
```

Copy the Lightning Payment Monitor code into this file.

**Configure settings:**
```python
# Edit these values in the script:
LNBITS_URL = "https://your-lnbits-server.com"
WALLET_ID = "your-wallet-id"
API_KEY = "your-invoice-key"
RELAY_PIN = 18
SOLENOID_DURATION = 5
MIN_PAYMENT_AMOUNT = 1
```

**Make executable:**
```bash
chmod +x /home/pi/lightning_solenoid.py
```

## 🔌 Hardware Wiring

### GPIO Connections (Pi to Relay)
```
Pi Pin → Relay Pin
Pin 12 (GPIO 18) → S (Signal)
Pin 2  (5V)      → + (VCC)
Pin 6  (GND)     → - (GND)
```

### Power Circuit (12V Side)
```
12V Power Supply (+) → Relay COM
Relay NO            → Solenoid Wire 1
Solenoid Wire 2     → 12V Power Supply (-)
```

### Wiring Diagram
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Raspberry   │    │   5V Relay  │    │ 12V Solenoid│
│ Pi Zero W   │    │   Module    │    │    Valve    │
│             │    │             │    │             │
│ GPIO18 ─────┼────┤ S           │    │             │
│ 5V ─────────┼────┤ +       COM ├────┤ Wire 1      │
│ GND ────────┼────┤ -        NO ├────┤ Wire 2      │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                      12V Power Supply
                                         (+) (-)
```

## ⚙️ Configuration

### LNbits Setup

1. **Get API Credentials:**
   - Log into your LNbits instance
   - Navigate to your wallet
   - Copy the **Invoice/Read API key** (not admin key)
   - Note your **Wallet ID** from the URL

2. **Test Connection:**
   ```bash
   # Test API access:
   curl -H "X-Api-Key: your-api-key" https://your-lnbits-server.com/api/v1/wallet
   ```

### Script Configuration

Edit `/home/pi/lightning_solenoid.py`:

```python
# Required Settings
LNBITS_URL = "https://your-lnbits-server.com"
WALLET_ID = "your-wallet-id" 
API_KEY = "your-invoice-key"

# Hardware Settings
RELAY_PIN = 18                # GPIO pin for relay control
SOLENOID_DURATION = 5         # Seconds to keep solenoid active

# Payment Settings  
MIN_PAYMENT_AMOUNT = 1        # Minimum sats to trigger (0 = any amount)
POLL_INTERVAL = 2             # How often to check payment status
```

## 🚀 Usage

### Manual Start
```bash
python3 /home/pi/lightning_solenoid.py
```

### Auto-Start Service

**Create service file:**
```bash
sudo nano /etc/systemd/system/lightning-solenoid.service
```

**Add content:**
```ini
[Unit]
Description=Lightning Payment Solenoid Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/lightning_solenoid.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Enable service:**
```bash
sudo systemctl enable lightning-solenoid.service
sudo systemctl start lightning-solenoid.service
sudo systemctl status lightning-solenoid.service
```

## 🧪 Testing

### 1. Software Test
```bash
# Run the script and look for:
🚀 Starting Lightning Payment Monitor (Polling)
✅ Connected to wallet: Your Wallet Name
💳 Current balance: XXX sats
🎯 Ready to detect NEW payments only!
👀 Monitoring for payments...
```

### 2. Payment Test
1. Send a Lightning payment to your LNbits wallet
2. Watch for output:
   ```
   📄 New invoice detected: 10 sats (monitoring for payment)
   🎉 PAYMENT COMPLETED!
   💧 Activating solenoid for 5 seconds
   ✅ Solenoid deactivated
   ```

### 3. Hardware Test
- You should hear the relay click ON when payment is received
- Solenoid should activate (valve opens, water flows, etc.)
- Relay clicks OFF after the configured duration

## 🔍 Troubleshooting

### Common Issues

**Pi won't connect to WiFi:**
- Ensure network is 2.4GHz (Pi Zero W doesn't support 5GHz)
- Check WPA2 security (WPA3 not supported)
- Verify wpa_supplicant.conf file format and location

**SSH connection refused:**
- Verify `ssh` file exists in boot partition
- Check Pi IP address with network scanner
- Try `ssh pi@raspberrypi.local`

**Script can't connect to LNbits:**
- Verify LNBITS_URL is correct and accessible
- Check API_KEY has proper permissions
- Test API manually with curl

**Relay doesn't activate:**
- Check GPIO wiring (Pin 12 = GPIO 18)
- Verify 5V power to relay
- Test with multimeter for continuity

**Solenoid doesn't work:**
- Check 12V power supply connections
- Verify COM → 12V+ and NO → Solenoid connections
- Test solenoid with direct 12V connection

### Log Files
```bash
# Check application logs
tail -f /home/pi/solenoid_controller.log

# Check system service logs
sudo journalctl -u lightning-solenoid.service -f
```

### Debug Mode
Add debug logging to script:
```python
# Change logging level
logging.basicConfig(level=logging.DEBUG, ...)
```

## 🔒 Security Considerations

- **Use read-only API keys** (Invoice/Read, not Admin)
- **Secure your LNbits instance** with HTTPS
- **Change default Pi password** immediately
- **Use firewall rules** if Pi is exposed to internet
- **Regular system updates** for security patches

## 📊 Monitoring

### Check Status
```bash
# Service status
sudo systemctl status lightning-solenoid.service

# Live logs
tail -f /home/pi/solenoid_controller.log

# System resources
htop
```

### Performance Notes
- **Polling interval:** 2 seconds (configurable)
- **Memory usage:** ~50MB typical
- **CPU usage:** <5% on Pi Zero W
- **Network:** Minimal bandwidth usage

## 🔧 Customization

### Multiple Solenoids
```python
# Add more GPIO pins for multiple valves
RELAY_PINS = [18, 19, 20]  # Multiple GPIO pins
```

### Payment Amount Scaling
```python
# Scale solenoid duration based on payment amount
duration = min(payment_amount_sats / 10, 60)  # Max 60 seconds
```

### Webhook Integration
For instant notifications, consider implementing LNbits webhook support instead of polling.

## 📄 License

This project is open source. Use and modify as needed for your applications.

## 🙏 Acknowledgments

- **LNbits** for providing excellent Lightning wallet infrastructure
- **Raspberry Pi Foundation** for accessible hardware
- **Bitcoin Lightning Network** for enabling instant microtransactions

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review log files for error messages
3. Test individual components (Pi, relay, solenoid, LNbits API)
4. Verify all wiring connections

---

**⚡ Happy Lightning automation! ⚡**
