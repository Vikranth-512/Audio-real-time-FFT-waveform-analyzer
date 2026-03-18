# ESP32 Wi-Fi Audio Waveform Analyzer Dashboard

A complete embedded + web system that captures analog audio from a phone through an ESP32, processes the signal to detect waveform 
characteristics,and streams the data in real time over Wi-Fi to a web dashboard.
A real-time audio signal processing system that captures live audio,and visualizes waveform + frequency-domain features+ FFT analysis
in a WebGL dashboard.

## System Overview

```
Phone (audio source) → Analog Front-End → ESP32 (MicroPython) → WiFi → Backend (FastAPI) → Dashboard (React)
```

## Features

- **Real-time Audio Capture**: 8kHz sampling rate with 12-bit ADC resolution,48000khz sampling rate for device audio capture
- **Live Waveform Display**: Scrolling oscilloscope visualization
- **Session Management**: Automatic recording and historical data storage
- **WebSocket Streaming**: Low-latency real-time data transmission
- **Professional Dashboard**: Dark navy theme with responsive and animated design
- **SQLite Database**:Persistent session storage and retrieval of export functionality for session data (CSV)
- **exports**: exports of real time data and averages for all computed metrics 

### Audio metrics:(averages and real time values computed)

RMS (signal energy)

frequency

Peak amplitude

Dominant frequency (FFT)

Spectral centroid(FFT)

Spectral rolloff(FFT)

Spectral flatness(FFT)

BPM

### Docker Setup

Build image
docker build -t audio-analyzer .
Run backend
docker run -p 8000:8000 audio-analyzer

⚠️ Note: Audio capture should be run on host machine for best compatibility.
(run the demo_audio_capture.py script to test dashboard functionality with audio direct from device)

### Prerequisites

- ESP32 development board
- Computer with Python 3.8+ and Node.js 16+
- WiFi network
- Audio source

### Hardware Setup

1. **Analog Front-End Circuit**:
   - Stereo AUX input → 2x 4.7kΩ resistors (mixing)
   - 1µF capacitor (AC coupling)
   - 2x 10kΩ resistors (bias divider to 1.65V)
   - 10µF capacitor (bias stabilization)
   - 3.3kΩ resistor + 10nF capacitor (anti-alias filter)
   - Connect to ESP32 GPIO34 (ADC1_CH6)

2. **ESP32 Setup**:
   - Install MicroPython firmware
   - Upload firmware files from `micropython/` directory

## Project Structure

```
├── micropython/          # ESP32 firmware
│   ├── main.py           # Main application
│   ├── wifi.py           # WiFi management
│   ├── sampler.py        # ADC sampling
│   ├── streamer.py       # WebSocket streaming
│   └── README.md         # Hardware setup guide
├── backend/              # FastAPI server
│   ├── main.py           # API endpoints
│   ├── database.py       # SQLite operations
│   ├── session_manager.py # Session lifecycle
│   ├── metrics_engine.py # Audio processing
│   ├── websocket_stream.py # WebSocket handling
│   ├── requirements.txt  # Python dependencies
│   └── README.md         # Backend documentation
├── dashboard/            # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── App.jsx       # Main application
│   │   └── styles.css    # Styling
│   ├── package.json      # Dependencies
│   ├── vite.config.js    # Build configuration
│   └── README.md         # Frontend documentation
└── README.md            # This file
```
### Software system architecture

Audio Source (Mic / Stereo Mix) 
↓ 
demo_audio_listener.py (PyAudio) 
↓ 
WebSocket Stream 
↓
FastAPI Backend
↓
Metrics Engine (FFT + DSP)
↓
Frontend Dashboard (WebGL)