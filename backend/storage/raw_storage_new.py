import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
import asyncio
import time
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", "/data/raw")

class RawStorage:
    def __init__(self):
        # Per-session buffering instead of global buffer
        self.session_buffers: Dict[str, List[dict]] = {}
        self.session_part_counters: Dict[str, int] = {}
        self.session_last_flush: Dict[str, float] = {}
        
        # Configuration
        self.buffer_size_threshold = 5000  # rows per session
        self.time_threshold_seconds = 300  # 5 minutes
        self.min_file_size_rows = 100  # minimum rows for a file
        
        self._lock = asyncio.Lock()

    async def append(self, session_id: str, payload: dict):
        """Append data to a specific session buffer"""
        async with self._lock:
            if session_id not in self.session_buffers:
                self.session_buffers[session_id] = []
                self.session_part_counters[session_id] = 0
                self.session_last_flush[session_id] = time.time()
            
            self.session_buffers[session_id].append(payload)
            
            # Check if this session should be flushed
            should_flush = self._should_flush_session(session_id)
            
        if should_flush:
            await self.flush_session(session_id)

    def _should_flush_session(self, session_id: str) -> bool:
        """Check if a session should be flushed based on conditions"""
        buffer = self.session_buffers.get(session_id, [])
        if not buffer:
            return False
        
        # Condition A: Buffer size threshold
        if len(buffer) >= self.buffer_size_threshold:
            return True
        
        # Condition B: Time-based threshold (only if buffer has minimum data)
        time_since_flush = time.time() - self.session_last_flush.get(session_id, 0)
        if time_since_flush >= self.time_threshold_seconds and len(buffer) >= self.min_file_size_rows:
            return True
        
        return False

    async def flush_session(self, session_id: str):
        """Flush a specific session's buffer to parquet"""
        async with self._lock:
            if session_id not in self.session_buffers or not self.session_buffers[session_id]:
                return
            
            records = self.session_buffers[session_id]
            self.session_buffers[session_id] = []
            self.session_last_flush[session_id] = time.time()
            
        if records:
            # Run the IO operation in an executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_session_parquet, session_id, records)

    def _write_session_parquet(self, session_id: str, records: List[dict]):
        """Write session data to parquet with proper naming"""
        try:
            df = pd.DataFrame(records)
            
            # Convert timestamp to readable date for partitioning
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
            
            # Group by device_id and date partition
            for (device_id, date), group_df in df.groupby(['device_id', 'date']):
                partition_dir = os.path.join(RAW_DATA_DIR, f"device_id={device_id}", f"date={date}")
                os.makedirs(partition_dir, exist_ok=True)
                
                # Deterministic file naming based on session_id and part number
                part_num = self.session_part_counters.get(session_id, 0)
                if part_num == 0:
                    # First file for this session
                    file_path = os.path.join(partition_dir, f"{session_id}.parquet")
                else:
                    # Chunked file for this session
                    file_path = os.path.join(partition_dir, f"{session_id}_part_{part_num}.parquet")
                
                # Increment part counter for next chunk
                self.session_part_counters[session_id] = part_num + 1
                
                # Drop partition columns before saving
                save_df = group_df.drop(columns=['datetime', 'date'])
                
                table = pa.Table.from_pandas(save_df)
                pq.write_table(table, file_path, compression='snappy')
                
                if len(logger.handlers) > 0:  # Check if logger is configured
                    logger.info(f"Written {len(save_df)} rows for session {session_id} to {file_path}")
                
        except Exception as e:
            logger.error(f"Error flushing session {session_id} parquet data: {e}")
            raise

    async def flush_all(self):
        """Flush all active sessions (for graceful shutdown)"""
        async with self._lock:
            session_ids = list(self.session_buffers.keys())
        
        for session_id in session_ids:
            await self.flush_session(session_id)

    async def cleanup_session(self, session_id: str):
        """Clean up resources for a completed session"""
        async with self._lock:
            # Remove from all tracking structures
            self.session_buffers.pop(session_id, None)
            self.session_part_counters.pop(session_id, None)
            self.session_last_flush.pop(session_id, None)
        
        if len(logger.handlers) > 0:
            logger.info(f"Cleaned up resources for session {session_id}")

    def get_session_stats(self) -> Dict[str, Dict]:
        """Get statistics for all active sessions"""
        stats = {}
        for session_id, buffer in self.session_buffers.items():
            stats[session_id] = {
                'buffer_size': len(buffer),
                'part_count': self.session_part_counters.get(session_id, 0),
                'last_flush': self.session_last_flush.get(session_id, 0),
                'time_since_flush': time.time() - self.session_last_flush.get(session_id, 0)
            }
        return stats

    # Legacy methods for backward compatibility
    async def append_legacy(self, payload: dict):
        """Legacy method - use append(session_id, payload) instead"""
        # Try to extract session_id from payload
        session_id = payload.get('session_id', 'unknown')
        await self.append(session_id, payload)

    async def flush_legacy(self):
        """Legacy method - flushes all sessions"""
        await self.flush_all()
