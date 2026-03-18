# Audio Waveform Analyzer Dashboard

Real-time audio waveform analyzer dashboard with ESP32 integration, featuring live waveform visualization, BPM detection, and session management.

## Features

- **Real-time Waveform Display**: Live oscilloscope-style visualization of audio signals
- **Audio Metrics**: BPM estimation, RMS amplitude, peak detection, frequency analysis
- **Session Management**: Automatic session recording and historical data storage
- **WebSocket Communication**: Real-time updates without page refresh
- **Professional UI**: Dark navy theme with responsive design
- **Session History**: View and replay previous recording sessions

## Technology Stack

- **Frontend**: React 18, Vite, Chart.js, WebSocket
- **Backend**: FastAPI, SQLite, WebSocket
- **Hardware**: ESP32 with MicroPython firmware
- **Communication**: WebSocket for real-time streaming

## Installation

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Build for production:
```bash
npm run build
```

## Configuration

The dashboard connects to the backend at `http://localhost:8000` by default. Ensure the backend server is running before starting the dashboard.

## Running the Application

1. Start the backend server:
```bash
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

2. Start the frontend development server:
```bash
npm run dev
```

3. Open browser to: `http://localhost:3000`

## Dashboard Components

### Real-time Waveform
- Scrolling oscilloscope display
- 5-second buffer window
- 20-30 FPS update rate
- Auto-scaling amplitude

### Live Metrics
- **BPM**: Beat detection and tempo estimation
- **RMS**: Root mean square amplitude (V)
- **Peak**: Peak amplitude detection (V)
- **Frequency**: Fundamental frequency estimation (Hz)
- **Session Time**: Elapsed recording time

### Session History
- List of all recording sessions
- Session ID, BPM, duration
- Replay functionality for historical sessions
- Sortable by date and duration

## WebSocket Communication

The dashboard uses WebSocket connections for real-time data:

- **Connection**: `ws://localhost:8000/ws/audio`
- **Message Types**:
  - `audio_update`: Real-time waveform and metrics
  - `session_update`: Session status changes
  - `session_history`: Historical session data

## Color Scheme

- **Background**: #0B1E3A (Dark navy)
- **Panels**: #132A4F (Navy panels)
- **Accent**: #4DA3FF (Bright blue)
- **Waveform**: #6EC1FF (Light blue)
- **Text**: #E8F1FF (Light text)

## Performance

- **Target Latency**: 50-150ms
- **Update Rate**: 20-30 FPS
- **Data Buffer**: 5 seconds of audio
- **Sample Rate**: 8kHz

## Troubleshooting

- **Connection Issues**: Ensure backend server is running on port 8000
- **No Data**: Check ESP32 connection and WebSocket status
- **Performance**: Reduce buffer size if experiencing lag
- **Browser Compatibility**: Use modern browser with WebSocket support

## Project Structure

```
├── src/
│   ├── components/          # React components
│   │   ├── WaveformVisualization.jsx
│   │   ├── MetricsPanel.jsx
│   │   ├── SessionHistory.jsx
│   │   └── ConnectionStatus.jsx
│   ├── hooks/              # Custom React hooks
│   │   └── useWebSocket.js
│   ├── App.jsx             # Main application component
│   ├── main.jsx            # Application entry point
│   └── styles.css          # Global styles
├── index.html              # HTML template
├── vite.config.js          # Vite configuration
├── package.json            # Dependencies and scripts
└── README.md               # This file
```
