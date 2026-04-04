import json
import os
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class StreamProducer:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.stream_name = "audio_stream"

    async def push_to_stream(self, payload: dict):
        """
        Pushes a validated audio payload to the Redis Stream.
        Serializes the values to string since XADD requires string fields.
        """
        # Redis XADD accepts a dict of string-keyed and string-valued items
        message = {
            "device_id": str(payload.get("device_id")),
            "timestamp": str(payload.get("timestamp")),
            "session_id": str(payload.get("session_id")),
            "samples": json.dumps(payload.get("samples", []))
        }
        await self.redis.xadd(self.stream_name, message)

    async def close(self):
        await self.redis.aclose()
