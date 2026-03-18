import json
import asyncio
import time
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from session_manager import SessionManager


class WebSocketManager:

    def __init__(self, session_manager: SessionManager):

        self.session_manager = session_manager

        self.active_connections: Dict[str, Set[WebSocket]] = {}

        self.esp32_connections: Dict[str, WebSocket] = {}


    async def connect(self, websocket: WebSocket, client_type: str = "dashboard"):

        await websocket.accept()

        if client_type == "dashboard":

            if "dashboard" not in self.active_connections:
                self.active_connections["dashboard"] = set()

            self.active_connections["dashboard"].add(websocket)

            print(
                f"Dashboard connected | total: {len(self.active_connections['dashboard'])}"
            )

        elif client_type == "esp32":

            session_id = self.session_manager.create_session()

            self.esp32_connections[session_id] = websocket

            print(f"ESP32 connected | session {session_id}")

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "session_created",
                        "session_id": session_id,
                    }
                )
            )

            return session_id

        return None


    def disconnect(self, websocket: WebSocket, session_id: str = None):

        for client_type, connections in self.active_connections.items():

            if websocket in connections:

                connections.remove(websocket)

                print(
                    f"Dashboard disconnected | remaining: {len(connections)}"
                )

                break

        if session_id and session_id in self.esp32_connections:

            del self.esp32_connections[session_id]

            self.session_manager.end_session(session_id)

            print(f"ESP32 disconnected | session ended {session_id}")


    async def handle_esp32_message(self, websocket: WebSocket, message: str, session_id: str):

        try:

            data = json.loads(message)

            if data.get("type") == "audio_data":

                samples = data.get("samples", [])

                if not samples:
                    return

                timestamp = data.get("timestamp", time.time())

                bpm_sim = data.get("bpm_simulated") or data.get("bpm")

                metrics = self.session_manager.process_samples(
                    session_id,
                    samples,
                    timestamp,
                    bpm_simulated=bpm_sim,
                )

                if metrics:

                    audio_msg = {
                        "type": "audio_update",
                        "session_id": session_id,
                        "timestamp": timestamp,
                        "samples": samples,
                        "metrics": metrics,
                        "sample_count": len(samples),
                    }

                    for fld in ("bpm_simulated", "bpm", "sample_rate"):

                        if fld in data:

                            audio_msg[fld] = data[fld]

                            try:
                                metrics[fld] = data[fld]
                            except Exception:
                                pass

                    await self.broadcast_to_dashboards(audio_msg)

                    session_stats = self.session_manager.get_session_stats(session_id)

                    if session_stats:

                        await self.broadcast_to_dashboards(
                            {
                                "type": "session_update",
                                "session_id": session_id,
                                "stats": session_stats,
                            }
                        )

        except json.JSONDecodeError:

            print("Invalid JSON from ESP32")

        except Exception as e:

            print(f"ESP32 message error: {e}")


    async def broadcast_to_dashboards(self, message: dict):

        dashboards = self.active_connections.get("dashboard")

        if not dashboards:
            return

        message_str = json.dumps(message)

        send_tasks = []

        disconnected = []

        for connection in list(dashboards):

            send_tasks.append(self._safe_send(connection, message_str, disconnected))

        await asyncio.gather(*send_tasks, return_exceptions=True)

        for ws in disconnected:

            dashboards.discard(ws)


    async def _safe_send(self, websocket: WebSocket, message: str, disconnected: list):

        try:

            await websocket.send_text(message)

        except Exception:

            disconnected.append(websocket)


    async def send_session_history(self, websocket: WebSocket):

        await websocket.send_text(
            json.dumps(
                {
                    "type": "session_history",
                    "data": {},
                }
            )
        )


    async def send_session_details(self, websocket: WebSocket, session_id: str):

        session_export = self.session_manager.get_session_export(session_id)

        if session_export:

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "session_details",
                        "session_id": session_id,
                        "data": session_export,
                    }
                )
            )

        else:

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Session {session_id} not found",
                    }
                )
            )


    async def handle_dashboard_message(self, websocket: WebSocket, message: str):

        try:

            data = json.loads(message)

            msg_type = data.get("type")

            if msg_type == "get_history":

                await self.send_session_history(websocket)

            elif msg_type == "get_session":

                session_id = data.get("session_id")

                if session_id:

                    await self.send_session_details(websocket, session_id)

            elif msg_type == "ping":

                await websocket.send_text(json.dumps({"type": "pong"}))

        except json.JSONDecodeError:

            print("Invalid JSON from dashboard")

        except Exception as e:

            print(f"Dashboard message error: {e}")


    async def cleanup_inactive_sessions(self):

        while True:

            try:

                self.session_manager.cleanup_inactive_sessions(
                    timeout_seconds=60
                )

            except Exception as e:

                print(f"Session cleanup error: {e}")

            await asyncio.sleep(30)


    def get_connection_stats(self) -> dict:

        return {
            "dashboard_connections": len(
                self.active_connections.get("dashboard", set())
            ),
            "esp32_connections": len(self.esp32_connections),
            "active_sessions": len(self.session_manager.active_sessions),
        }
