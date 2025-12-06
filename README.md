# Lightning Payment Dual Beer Tap Controller

A Bitcoin Lightning Network payment-activated dual beer tap controller using Raspberry Pi and LNbits. Monitor two different Lightning wallets and control two separate beer taps independently.

## 🚀 Project Overview

This enhanced system monitors **two different LNbits Lightning wallets** for incoming payments and automatically activates the corresponding 12V solenoid valve when payments are received. Perfect for Bitcoin-powered dual beer taps, different beer types, pricing tiers, or any beverage dispensing application requiring independent payment-activated hardware control.

- bitcoinswitch_tester.py - python file to test your lnbits api
- lightning_solenoid_polling.py - python script to test controls of a single solenoid
- dual_beer_tap.py - final solution to control 2 beer taps, each for a different lnbits wallet
- config_example.py - example configurations for dual_beer_tap

## ⚡ Features

- **Dual beer tap system** - Monitor two different LNbits wallets simultaneously
- **Independent tap control** - Each wallet triggers its own beer tap
- **Fast internal payment detection** - Catches instant payments within the same LNbits server
- **Timezone-aware timestamp handling** - Proper handling of API timestamps
- **Real-time Lightning payment detection** via LNbits API polling
- **Reliable payment verification** using dedicated payment status endpoints
- **Hardware control** via GPIO relay switching for two separate relays
- **Smart filtering** - only new payments trigger activation (ignores historical)
- **Configurable settings per beer tap** - Different minimum payments, pour rates, durations
- **Automatic reconnection** and error handling
- **Memory management** - Prevents memory leaks with payment tracking cleanup
- **Detailed logging** for monitoring and debugging both beer taps

## 🛠 Hardware Requirements

### Core Components
- **Raspberry Pi Zero W** (with WiFi) or Raspberry Pi 4
- **MicroSD card** (8GB+, Class 10 recommended)
- **2x 5V Relay Modules** (3-terminal: COM, NO, NC) - or 1x dual relay module
- **2x 12V Solenoid Valves** (2-wire, normally closed recommended) - for beer tap control
- **12V Power Supply** (5A+ recommended for dual beer taps)
- **Jumper wires** for connections

### Pi pinout
```
SD Card Side    |    Edge Side
(1) 3V3         |    5V (2)
(3) GPIO2       |    5V (4)  
(5) GPIO3       |    GND (6)
(7) GPIO4       |    GPIO14 (8)
(9) GND         |    GPIO15 (10)
(11) GPIO17     |    GPIO18 (12) ← Connect relay IN here
```
### Relay Connections
```
Relay Module → Pi Zero W Pin
VCC         → Pin 2 (5V)
GND         → Pin 6 (GND) 
IN          → Pin 12 (GPIO 18)
```

### Power Circuit (12V side):
```
12V Power Supply (+) → Relay COM terminal
Relay NO terminal    → Solenoid cable 2
Solenoid cable 1     → 12V Power Supply (-)
```
### Control Circuit (Pi side):
```
Pi GPIO 18 (Pin 12) → Relay S pin ✅
Pi 5V (Pin 2)       → Relay + pin ✅  
Pi GND (Pin 6)      → Relay - pin ✅
```
