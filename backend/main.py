from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import asyncio
import uvicorn

from session_manager import SessionManager
from websocket_stream import WebSocketManager

app = FastAPI(title="Audio Waveform Analyzer API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (in-memory session manager, no DB)
session_manager = SessionManager()
websocket_manager = WebSocketManager(session_manager)

# Serve static files (dashboard)
BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR.parent / "dashboard" / "dist"

if DIST_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(DIST_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard"""
    try:
        with open("../dashboard/dist/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <body>
                <h1>Audio Waveform Analyzer</h1>
                <p>Dashboard not found. Please build the frontend first.</p>
                <p>Run: cd ../dashboard && npm run build</p>
            </body>
        </html>
        """)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connections": websocket_manager.get_connection_stats()
    }

@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop an active session (in-memory)"""
    try:
        ok = session_manager.end_session(session_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "stopped", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/export")
@app.get("/api/session/{session_id}/metrics")
async def export_session_metrics(session_id: str, mode: str = Query(default="wave", pattern="^(wave|fft)$")):
    """Export session with averages and full_metrics: { session_id, averages, full_metrics }"""
    try:
        data = session_manager.get_session_export(session_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Session not found")

        def _filter_averages(avgs: dict, m: str) -> dict:
            if m == "fft":
                keep = {
                    "avg_peak_frequency",
                    "avg_spectral_centroid",
                    "avg_spectral_rolloff",
                    "avg_spectral_flatness",
                }
                return {k: v for k, v in (avgs or {}).items() if k in keep}
            return avgs or {}

        def _filter_full_metrics(full_metrics: list, m: str) -> list:
            if m != "fft":
                return full_metrics or []
            keep = {"peak_frequency", "spectral_centroid", "spectral_rolloff", "spectral_flatness"}
            out = []
            for row in full_metrics or []:
                metrics = row.get("metrics", {}) if isinstance(row, dict) else {}
                out.append(
                    {
                        "timestamp": row.get("timestamp"),
                        "metrics": {k: metrics.get(k, 0.0) for k in keep},
                    }
                )
            return out

        averages = _filter_averages(data.get("averages", {}), mode)
        full_metrics = _filter_full_metrics(data.get("full_metrics", []), mode)

        return {"session_id": data["session_id"], "averages": averages, "full_metrics": full_metrics}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}/averages")
async def get_session_averages(session_id: str, mode: str = Query(default="wave", pattern="^(wave|fft)$")):
    """Export averages only for session_averages_<session_id>.json"""
    try:
        data = session_manager.get_session_export(session_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Session not found")
        averages = data.get("averages", {}) or {}
        if mode == "fft":
            keep = {
                "avg_peak_frequency",
                "avg_spectral_centroid",
                "avg_spectral_rolloff",
                "avg_spectral_flatness",
            }
            averages = {k: v for k, v in averages.items() if k in keep}
        return {"session_id": session_id, **averages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions():
    """Get all stored sessions (for history sidebar)."""
    try:
        sessions = session_manager.get_all_sessions(limit=100)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/search")
async def search_sessions(q: str = ""):
    """Search sessions by session_id."""
    try:
        sessions = session_manager.search_session(q, limit=100)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Load full session for display: { session_id, averages, metrics }."""
    try:
        row = session_manager.get_session(session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": row["session_id"],
            "averages": row.get("averages", {}),
            "metrics": row.get("metrics", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/current")
async def get_current_metrics():
    """Get current metrics for active sessions"""
    try:
        active_sessions = {}
        for session_id in session_manager.active_sessions:
            metrics = session_manager.get_current_metrics(session_id)
            if metrics:
                active_sessions[session_id] = metrics
        return {
            "active_sessions": active_sessions,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for ESP32 and dashboard connections"""
    await websocket_manager.connect(websocket, client_type="dashboard")
    
    try:
        while True:
            message = await websocket.receive_text()
            await websocket_manager.handle_dashboard_message(websocket, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.websocket("/ws/esp32")
async def esp32_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint specifically for ESP32 connections"""
    session_id = await websocket_manager.connect(websocket, client_type="esp32")
    
    if not session_id:
        await websocket.close()
        return
    
    try:
        while True:
            message = await websocket.receive_text()
            await websocket_manager.handle_esp32_message(websocket, message, session_id)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, session_id)

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks"""
    # Start cleanup task
    asyncio.create_task(websocket_manager.cleanup_inactive_sessions())
    print("Audio Waveform Analyzer API started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # End all active sessions
    for session_id in list(session_manager.active_sessions.keys()):
        session_manager.end_session(session_id)
    print("Audio Waveform Analyzer API shutdown")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
