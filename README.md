# ESP32 Wi-Fi Audio Waveform Analyzer Dashboard

A complete embedded + web system that captures analog audio from a phone through an ESP32, processes the signal to detect waveform characteristics, and streams the data in real time over Wi-Fi to a web dashboard.

## System Overview

```
Phone (audio source) → Analog Front-End → ESP32 (MicroPython) → WiFi → Backend (FastAPI) → Dashboard (React)
```

## Features

- **Real-time Audio Capture**: 8kHz sampling rate with 12-bit ADC resolution
- **Live Waveform Display**: Scrolling oscilloscope visualization
- **Audio Metrics**: BPM estimation, RMS amplitude, peak detection, frequency analysis
- **Session Management**: Automatic recording and historical data storage
- **WebSocket Streaming**: Low-latency real-time data transmission
- **Professional Dashboard**: Dark navy theme with responsive design
- **SQLite Database**: Persistent session storage and retrieval

## Quick Start

### Prerequisites

- ESP32 development board
- Computer with Python 3.8+ and Node.js 16+
- WiFi network
- Audio source (phone with AUX output)

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

### Software Setup

1. **Backend Installation**:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

2. **Frontend Installation**:
```bash
cd dashboard
npm install
npm run dev
```

3. **ESP32 Configuration**:
   - Edit `micropython/main.py`:
     - Set `WIFI_SSID` and `WIFI_PASSWORD`
     - Set `BACKEND_IP` to your computer's IP address

4. **Access Dashboard**:
   - Open browser to `http://localhost:3000`
   - Backend API available at `http://localhost:8000`

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

## Configuration

### ESP32 Configuration
Edit `micropython/main.py`:
```python
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
BACKEND_IP = "192.168.1.100"  # Your computer's IP
```

### Backend Configuration
- Database: SQLite `audio_sessions.db` (auto-created)
- Port: 8000 (configurable)
- CORS: Enabled for all origins (development)

### Frontend Configuration
- WebSocket: `ws://localhost:8000/ws/audio`
- API: `http://localhost:8000/api`
- Development server: `http://localhost:3000`

## API Endpoints

### REST API
- `GET /` - Dashboard frontend
- `GET /api/health` - Health check and connection stats
- `GET /api/sessions` - All sessions (active + historical)
- `GET /api/sessions/{id}` - Specific session details
- `GET /api/metrics/current` - Current metrics for active sessions

### WebSocket Endpoints
- `/ws/audio` - Dashboard clients
- `/ws/esp32` - ESP32 devices

## Performance Specifications

- **Sampling Rate**: 8 kHz
- **ADC Resolution**: 12-bit (0-4095)
- **Target Latency**: 50-150ms
- **Data Throughput**: ~50KB/sec
- **Waveform Buffer**: 5 seconds (40,000 samples)
- **Update Rate**: 20-30 FPS

## Troubleshooting

### Common Issues

1. **ESP32 Won't Connect**:
   - Check WiFi credentials
   - Verify network availability
   - Monitor serial output

2. **Backend Connection Failed**:
   - Confirm backend IP address
   - Check firewall settings
   - Verify port 8000 is accessible

3. **No Audio Data**:
   - Test analog front-end circuit
   - Verify GPIO34 connection
   - Check signal level (0-3.3V range)

4. **Dashboard Not Loading**:
   - Ensure backend is running
   - Check browser console for errors
   - Verify WebSocket connection

### Debug Mode

Enable verbose logging:
- ESP32: Monitor serial output
- Backend: Check console logs
- Frontend: Open browser developer tools

## Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload --log-level debug
```

### Frontend Development
```bash
cd dashboard
npm run dev
```

### ESP32 Development
- Use MicroPython REPL for testing
- Monitor serial output for debugging
- Test modules individually

## Production Deployment

For production use:
1. Build frontend: `npm run build`
2. Use production WSGI server (Gunicorn/Uvicorn)
3. Configure reverse proxy (Nginx)
4. Set up SSL certificates
5. Configure firewall rules

## License

ISC License - feel free to use for personal and commercial projects.

## Support

For issues and questions:
1. Check individual component README files
2. Review troubleshooting section
3. Test components individually
4. Verify network connectivity
