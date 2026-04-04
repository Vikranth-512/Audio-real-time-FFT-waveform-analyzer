import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import ValidationError

from ingestion.schemas import AudioPayload
from ingestion.stream_producer import StreamProducer
from storage.db import async_session, AudioMetric
from storage.db import init_db
from sqlalchemy import select, desc
import redis.asyncio as redis
from sqlalchemy import func

# Configure logging level based on environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Debug flag for verbose logging (set via environment variable)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

stopped_sessions: set[str] = set()

app = FastAPI(title="Audio Waveform Analyzer API Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR.parent / "dashboard" / "dist"

if DIST_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(DIST_DIR)), name="static")


stream_producer = StreamProducer()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Dashboard connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.active_connections.discard(connection)

manager = ConnectionManager()

# Background broadcast task
async def broadcast_metrics_task():
    logger.info("Starting background metrics broadcaster...")
    last_id = "0"  # Start from beginning, then track properly
    # Loop over stream using XREAD
    while True:
        try:
            response = await redis_client.xread(
                streams={"audio_metrics_stream": last_id},
                count=100,
                block=5000
            )
            if response:
                for stream, messages in response:
                    for message_id, data in messages:
                        # Only update last_id if we successfully process this message
                        # This prevents re-reading messages if there's an error
                        last_id = message_id
                        
                        device_id = data.get("device_id")
                        session_id = data.get("session_id")

                        if session_id in stopped_sessions:
                            if DEBUG_MODE:
                                logger.info(f"Dropped stopped session: {session_id}")
                            continue
                        
                        timestamp = float(data.get("timestamp"))
                        metrics = json.loads(data.get("full_metrics", "{}"))
                        samples = json.loads(data.get("samples", "[]"))

                        
                        if DEBUG_MODE:
                            logger.info(f"Broadcasting session: {session_id}")
                        audio_msg = {
                            "type": "audio_update",
                            "session_id": session_id,
                            "timestamp": timestamp,
                            "samples": samples,
                            "metrics": metrics,
                            "sample_count": len(samples),
                        }
                        
                        await manager.broadcast(json.dumps(audio_msg))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    await init_db()
    asyncio.create_task(broadcast_metrics_task())

@app.on_event("shutdown")
async def shutdown_event():
    await stream_producer.close()
    await redis_client.aclose()


@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("../dashboard/dist/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard missing. Run npm run build.</h1>")


@app.post("/ingest")
async def ingest_audio(payload: AudioPayload):
    if not payload.timestamp:
        payload.timestamp = time.time()
    await stream_producer.push_to_stream(payload.dict())
    return {"status": "ok"}


@app.websocket("/ws/stream")
@app.websocket("/ws/esp32")
async def websocket_ingest(websocket: WebSocket):
    await websocket.accept()
    # Simple logic simulating esp32 connection
    session_id = str(uuid.uuid4())[:8]
    await websocket.send_text(json.dumps({"type": "session_created", "session_id": session_id}))

    try:
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                
                # Check for either explicit type "audio_data" OR the presence of "samples"
                samples = data.get("samples", [])
                
                if samples:
                    timestamp = data.get("timestamp", time.time())
                    # CRITICAL: Always use server-generated session_id, never client override
                    payload = AudioPayload(
                        device_id=data.get("device_id", "ws-device"),
                        timestamp=timestamp,
                        session_id=session_id,  # Server-generated only
                        samples=samples
                    )
                    await stream_producer.push_to_stream(payload.dict())
            except ValidationError as ve:
                logger.warning(f"Validation error: {ve}")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        logger.info(f"ESP32 ingestion websocket disconnected: {session_id}")


@app.websocket("/ws/audio")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            # Dashboard might ping or ask for history
            try:
                data = json.loads(message)
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- REST APIs MIGRATION TO POSTGRES ---

def _compute_averages_from_rows(rows):
    if not rows:
        return {"avg_rms": 0.0, "avg_peak": 0.0, "avg_frequency": 0.0, "avg_bpm": 0.0}
        
    rms_sum, amp_sum, bpm_sum = 0, 0, 0
    count = len(rows)
    for r in rows:
        rms_sum += (r.rms_energy or 0.0)
        amp_sum += (r.avg_amplitude or 0.0)
        bpm_sum += (r.bpm or 0.0)

    avg_rms = round(rms_sum / count, 4)
    avg_amp = round(amp_sum / count, 4)
    avg_bpm = round(bpm_sum / count, 4)
    
    return {
        "avg_rms": avg_rms,
        "avg_peak": avg_amp,
        "avg_frequency": 0.0,
        "avg_bpm": avg_bpm,
        "rms": avg_rms,
        "peak": avg_amp,
        "bpm": avg_bpm,
        "frequency": 0.0
    }
@app.get("/api/sessions")
async def list_sessions():
    async with async_session() as session:

        stmt = (
            select(
                AudioMetric.session_id,
                func.max(AudioMetric.timestamp).label("last_timestamp")
            )
            .group_by(AudioMetric.session_id)
            .order_by(desc("last_timestamp"))
            .limit(100)
        )

        result = await session.execute(stmt)

        sessions = [
            {"session_id": sid, "timestamp": ts}
            for sid, ts in result.fetchall()
        ]

        return {"sessions": sessions}

@app.get("/api/sessions/search")
async def search_sessions(q: str = ""):
    async with async_session() as session:

        stmt = (
            select(
                AudioMetric.session_id,
                func.max(AudioMetric.timestamp).label("last_timestamp")
            )
            .where(AudioMetric.session_id.ilike(f"%{q}%"))
            .group_by(AudioMetric.session_id)
            .order_by(desc("last_timestamp"))
            .limit(100)
        )

        result = await session.execute(stmt)

        sessions = [
            {"session_id": sid, "timestamp": ts}
            for sid, ts in result.fetchall()
        ]

        return {"sessions": sessions}

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Load full session for display: { session_id, averages, metrics }."""
    async with async_session() as session:
        stmt = select(AudioMetric).where(AudioMetric.session_id == session_id).order_by(AudioMetric.timestamp)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
            
        metrics = []
        for r in rows:
            metrics.append({
                "timestamp": r.timestamp,
                "metrics": {
                    "bpm": r.bpm,
                    "rms": r.rms_energy,
                    "peak": r.avg_amplitude
                }
            })
            
        averages = _compute_averages_from_rows(rows)
        return {
            "session_id": session_id,
            "averages": averages,
            "metrics": metrics
        }

@app.get("/api/session/{session_id}/averages")
async def get_session_averages(session_id: str, mode: str = Query(default="wave", pattern="^(wave|fft)$")):
    async with async_session() as session:
        stmt = select(AudioMetric).where(AudioMetric.session_id == session_id)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
        averages = _compute_averages_from_rows(rows)
        return {"session_id": session_id, **averages}

@app.get("/api/session/{session_id}/export")
@app.get("/api/sessions/{session_id}/export")
@app.get("/api/session/{session_id}/metrics")
async def export_session_metrics(session_id: str, mode: str = Query(default="wave", pattern="^(wave|fft)$")):
    async with async_session() as session:
        stmt = select(AudioMetric).where(AudioMetric.session_id == session_id).order_by(AudioMetric.timestamp)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
            
        metrics = []
        for r in rows:
            metrics.append({
                "timestamp": r.timestamp,
                "metrics": {
                    "bpm": r.bpm,
                    "rms": r.rms_energy,
                    "peak": r.avg_amplitude
                }
            })
            
        averages = _compute_averages_from_rows(rows)
        return {
            "session_id": session_id,
            "averages": averages,
            "full_metrics": metrics
        }

@app.get("/api/metrics/current")
async def get_current_metrics():
    """This returns nothing for now, it's mostly unused if using websockets heavily."""
    return {
        "active_sessions": {},
        "timestamp": time.time()
    }

@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    stopped_sessions.add(session_id)
    # Also store in Redis for worker access
    await redis_client.sadd("stopped_sessions", session_id)
    logger.info(f"Session stopped: {session_id}")
    return {"status": "stopped", "session_id": session_id}