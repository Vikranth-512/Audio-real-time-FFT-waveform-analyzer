import asyncio
import os
import json
import uuid
import logging
import time

import redis.asyncio as redis
from redis.exceptions import ResponseError, ConnectionError

from processing.metrics_engine import MetricsEngine
from storage.db import batch_insert_metrics
from storage.raw_storage import RawStorage

# Configure logging level based on environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Debug flag for verbose logging (set via environment variable)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

STREAM_NAME = "audio_stream"
GROUP_NAME = "audio_group"
METRICS_STREAM_NAME = "audio_metrics_stream"

class StreamWorker:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.raw_storage = RawStorage()
        self.consumer_name = f"worker-{uuid.uuid4()}"
        self.engines = {}  # session_id -> MetricsEngine
        self.stopped_sessions_cache = set()
        self.last_stopped_check = 0


    async def ensure_consumer_group(self):
        while True:
            try:
                await self.redis.xgroup_create(
                    name=STREAM_NAME,
                    groupname=GROUP_NAME,
                    id="0",
                    mkstream=True
                )
                logger.info("Consumer group created")
                return

            except ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.info("Consumer group already exists")
                    return
                else:
                    raise

            except ConnectionError:
                logger.warning("Redis not ready, retrying...")
                await asyncio.sleep(2)

    async def setup(self):
        await self.ensure_consumer_group()

    async def check_stopped_sessions(self):
        """Check if there are any stopped sessions to cache"""
        now = time.time()
        # Only check every 5 seconds to avoid excessive API calls
        if now - self.last_stopped_check > 5:
            try:
                # Simple approach: use a Redis key to track stopped sessions
                stopped = await self.redis.smembers("stopped_sessions")
                self.stopped_sessions_cache = set(stopped)
                self.last_stopped_check = now
            except Exception as e:
                logger.error(f"Failed to check stopped sessions: {e}")
    
    async def is_session_stopped(self, session_id: str) -> bool:
        """Check if a session is stopped"""
        await self.check_stopped_sessions()
        return session_id in self.stopped_sessions_cache

    def get_engine(self, session_id: str) -> MetricsEngine:
        if session_id not in self.engines:
            self.engines[session_id] = MetricsEngine()
        return self.engines[session_id]

    async def process_messages(self, messages):
        metrics_batch = []
        raw_payloads = []
        ack_ids = []

        for message_id, data in messages:
            try:
                device_id = data.get("device_id")
                timestamp = float(data.get("timestamp"))
                session_id = data.get("session_id")
                samples = json.loads(data.get("samples", "[]"))

                # CRITICAL: Check if session is stopped before processing
                if await self.is_session_stopped(session_id):
                    if DEBUG_MODE:
                        logger.info(f"Worker skipped stopped session: {session_id}")
                    ack_ids.append(message_id)  # Still ack to avoid reprocessing
                    continue
                
                if DEBUG_MODE:
                    logger.info(f"Worker processing session: {session_id}")

                raw_payloads.append({
                    "device_id": device_id,
                    "timestamp": timestamp,
                    "session_id": session_id,
                    "samples": samples
                })

                engine = self.get_engine(session_id)
                metrics = engine.calculate_metrics(samples, timestamp)

                db_metric = {
                    "timestamp": timestamp,
                    "device_id": device_id,
                    "session_id": session_id,
                    "bpm": float(metrics.get("bpm", 0.0)),
                    "avg_amplitude": float(metrics.get("peak", 0.0)),
                    "rms_energy": float(metrics.get("rms", 0.0)),
                }

                metrics_batch.append(db_metric)

                stream_metric = dict(db_metric)
                stream_metric["full_metrics"] = json.dumps(metrics)
                stream_metric["samples"] = json.dumps(samples)

                await self.redis.xadd(METRICS_STREAM_NAME, stream_metric)

                ack_ids.append(message_id)

            except Exception as e:
                logger.error(f"Error processing message {message_id}: {e}")

        # DB write (only ack if successful)
        if metrics_batch:
            try:
                await batch_insert_metrics(metrics_batch)
            except Exception as e:
                logger.error(f"DB insert failed, not acking: {e}")
                return

        # Raw storage - buffer per session, no per-loop flushing
        for payload in raw_payloads:
            try:
                await self.raw_storage.append(payload['session_id'], payload)
            except Exception as e:
                logger.error(f"Parquet append failed: {e}")

        # ACK messages
        if ack_ids:
            try:
                await self.redis.xack(STREAM_NAME, GROUP_NAME, *ack_ids)
            except Exception as e:
                logger.error(f"XACK failed: {e}")

        # Check for stopped sessions and flush them
        await self.flush_stopped_sessions()

    async def flush_stopped_sessions(self):
        """Flush data for stopped sessions and clean up resources"""
        await self.check_stopped_sessions()
        
        # Get all active sessions from engines
        active_sessions = set(self.engines.keys())
        stopped_to_flush = active_sessions.intersection(self.stopped_sessions_cache)
        
        for session_id in stopped_to_flush:
            try:
                if DEBUG_MODE:
                    logger.info(f"Flushing stopped session: {session_id}")
                
                # Flush session data to parquet
                await self.raw_storage.flush_session(session_id)
                
                # Clean up engine resources
                if session_id in self.engines:
                    del self.engines[session_id]
                
                # Remove from stopped sessions cache after successful flush
                await self.redis.srem("stopped_sessions", session_id)
                self.stopped_sessions_cache.discard(session_id)
                
            except Exception as e:
                logger.error(f"Error flushing stopped session {session_id}: {e}")

    async def run(self):
        await self.setup()

        last_claim_time = time.time()

        logger.info(f"{self.consumer_name} consuming from {STREAM_NAME}")

        while True:
            try:
                now = time.time()

                # Reclaim stale messages
                if now - last_claim_time > 10:
                    try:
                        pending = await self.redis.xpending(STREAM_NAME, GROUP_NAME)
                        if pending and pending["pending"] > 0:
                            claimed = await self.redis.xautoclaim(
                                name=STREAM_NAME,
                                groupname=GROUP_NAME,
                                consumername=self.consumer_name,
                                min_idle_time=30000,
                                start_id="0-0",
                                count=100
                            )

                            if claimed and claimed[1]:
                                logger.info(f"Reclaimed {len(claimed[1])} messages")
                                await self.process_messages(claimed[1])

                    except Exception as e:
                        logger.error(f"Reclaim failed: {e}")

                    last_claim_time = now

                # Read new messages
                results = await self.redis.xreadgroup(
                    groupname=GROUP_NAME,
                    consumername=self.consumer_name,
                    streams={STREAM_NAME: ">"},
                    count=100,
                    block=1000
                )

                if results:
                    for _, messages in results:
                        if messages:
                            await self.process_messages(messages)

                # Check for stopped sessions and flush them (no per-loop flushing)
                await self.flush_stopped_sessions()

            except ConnectionError:
                logger.error("Redis connection lost, retrying...")
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(1)


if __name__ == "__main__":
    worker = StreamWorker()
    asyncio.run(worker.run())

