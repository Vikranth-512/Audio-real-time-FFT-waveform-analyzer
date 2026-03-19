# Audio Waveform FFT Analyzer Dashboard

A complete embedded + web system that captures analog audio from a source, processes the signal to detect waveform 
characteristics,and streams the data in real time with time and frequecy domain analytics over Wi-Fi to a web dashboard.

A high-performance real-time audio visualization tool that captures raw samples, processes it using Fast Fourier Transform 
(FFT), and renders both waveform and frequency-domain representations.

Designed for learning, experimentation, and real-time signal analysis, this project demonstrates the complete pipeline 
from raw audio acquisition to frequency/time-domain visualization and analysis

## Features

- **Real-time Audio Capture**: 8kHz sampling rate with 12-bit ADC resolution,48000khz sampling rate for device audio capture
- **Live Waveform Display**: Scrolling oscilloscope visualization
- **Session Management**: Automatic recording and historical data storage
- **WebSocket Streaming**: Low-latency real-time data transmission
- **Professional Dashboard**: Dark navy theme with responsive and animated design
- **SQLite Database**:Persistent session storage and retrieval of export functionality for session data (CSV)
- **Exports**: exports of real time data and averages for all computed metrics 

⚡ Real-time audio capture

Continuous streaming from microphone input

Low-latency processing pipeline

### FFT-based frequency analysis

Converts time-domain audio signals into frequency spectrum

Visualizes amplitude vs frequency in real-time

Real-time display of dominant frequency, spectral centroid, rolloff, flatness, 

### Waveform visualization

Displays raw time-domain signal alongside FFT output

Useful for understanding signal characteristics

### Live data processing pipeline

Buffered streaming architecture

Continuous updates without blocking UI

### Signal processing concepts implemented

Windowing

Frequency binning

Magnitude computation from complex FFT output

### Audio metrics: (averages and real time values computed)

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

Note: Audio capture should be run on host machine for best compatibility.
(run the demo_audio_capture.py script to test dashboard functionality with audio direct from device)

### Prerequisites

Python 3.8+ and Node.js 16+

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

with the exclusion of docker files and demo audio capture script both of which can be found in the main directory

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
