# Audio Waveform Analyzer Backend

FastAPI backend server for processing and streaming audio waveform data from ESP32.

## Features

- Real-time WebSocket streaming from ESP32
- Audio metrics calculation (BPM, RMS, Peak, Frequency)
- Session management with SQLite persistence
- REST API for historical data
- Dashboard WebSocket broadcasting

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
uvicorn main:app --reload
```

Or for development with auto-reload:
```bash
python main.py
```

## API Endpoints

### REST Endpoints

- `GET /` - Serve dashboard frontend
- `GET /api/health` - Health check and connection stats
- `GET /api/sessions` - Get all sessions (active and historical)
- `GET /api/sessions/{session_id}` - Get specific session details
- `GET /api/metrics/current` - Get current metrics for active sessions

### WebSocket Endpoints

- `/ws/audio` - Dashboard clients connect here
- `/ws/esp32` - ESP32 devices connect here

## Database

The system uses SQLite for data persistence:

- **audio_sessions.db** - Main database file
- **sessions table** - Session metadata and summary metrics
- **samples table** - Individual audio samples

## Architecture

```
ESP32 → WebSocket → Session Manager → Database
                    ↓
                Metrics Engine
                    ↓
                WebSocket → Dashboard
```

## Configuration

The server automatically:
- Creates database on first run
- Handles WebSocket connections
- Manages session lifecycle
- Calculates real-time metrics
- Broadcasts to dashboard clients

## Performance

- **Target latency**: 50-150ms
- **Supported sampling rate**: 8kHz
- **Data throughput**: ~50KB/sec
- **Concurrent connections**: Multiple dashboard clients

## Troubleshooting

1. **Port already in use**
   - Change port: `uvicorn main:app --port 8001`
   - Kill existing process on port 8000

2. **Database errors**
   - Ensure write permissions to directory
   - Delete `audio_sessions.db` to reset

3. **WebSocket connection issues**
   - Check firewall settings
   - Verify ESP32 and backend are on same network
   - Monitor logs for connection errors

## Development

The backend is structured into modular components:

- `main.py` - FastAPI application and endpoints
- `database.py` - SQLite database operations
- `session_manager.py` - Session lifecycle management
- `metrics_engine.py` - Audio signal processing
- `websocket_stream.py` - WebSocket connection handling

Each module can be tested independently and has clear separation of concerns.
