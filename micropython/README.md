# ESP32 Audio Waveform Analyzer Firmware

MicroPython firmware for ESP32 that captures audio via ADC and streams waveform data over WiFi.

## Hardware Setup

### Components Required:
- ESP32 development board
- Stereo AUX input
- 2x 4.7kΩ resistors (stereo mixing)
- 1µF capacitor (AC coupling)
- 2x 10kΩ resistors (bias divider)
- 10µF capacitor (bias stabilization)
- 3.3kΩ resistor (anti-alias filter)
- 10nF capacitor (anti-alias filter)

### Circuit Connection:
1. Connect audio input to GPIO34 (ADC1_CH6)
2. Build analog front-end circuit as specified in PRD
3. Ensure signal range is 0-3.3V

## Configuration

Before uploading, update the configuration in `main.py`:

```python
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
BACKEND_IP = "192.168.1.100"  # Your computer's IP address
```

## Installation

1. Install MicroPython on ESP32
2. Upload all files to the ESP32:
   - `main.py`
   - `wifi.py`
   - `sampler.py`
   - `streamer.py`

3. Reset the ESP32 to start the system

## Operation

- LED blinks during startup
- LED stays on when system is running
- LED blinks briefly every 10 seconds as heartbeat
- System will auto-reconnect to WiFi and backend

## Technical Specifications

- **Sampling Rate**: 8 kHz
- **ADC Resolution**: 12-bit (0-4095)
- **Buffer Size**: 512 samples per packet
- **Target Latency**: <150ms
- **Data Rate**: ~50KB/sec

## Troubleshooting

1. **WiFi Connection Issues**
   - Check SSID and password
   - Ensure WiFi network is available
   - Monitor serial output for connection status

2. **Backend Connection Issues**
   - Verify backend IP address
   - Ensure backend server is running on port 8000
   - Check network connectivity

3. **Audio Input Issues**
   - Verify analog front-end circuit
   - Check GPIO34 connection
   - Ensure signal is in 0-3.3V range
