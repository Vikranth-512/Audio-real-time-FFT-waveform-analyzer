import ujson
import uasyncio as asyncio
import time
import ubinascii
import urandom

class WebSocketStreamer:
    def __init__(self, wifi_manager, sampler):
        self.wifi_manager = wifi_manager
        self.sampler = sampler
        self.session_id = self._generate_session_id()
        self.websocket = None
        self.streaming = False
        self.backend_url = "ws://192.168.1.100:8000/ws/audio"  # Update with your backend IP
        
    def _generate_session_id(self):
        """Generate unique session ID"""
        random_bytes = urandom.getrandbits(64).to_bytes(8, 'big')
        return ubinascii.hexlify(random_bytes).decode('ascii')[:8]
    
    async def connect_to_backend(self):
        """Connect to backend WebSocket server"""
        if not self.wifi_manager.is_connected():
            print("WiFi not connected, cannot connect to backend")
            return False
            
        try:
            import usocket as socket
            import uwebsocket as websocket
            
            print(f"Connecting to backend at {self.backend_url}")
            self.websocket = await websocket.connect(self.backend_url)
            print("Connected to backend WebSocket")
            return True
            
        except Exception as e:
            print(f"Failed to connect to backend: {e}")
            return False
    
    async def stream_data(self):
        """Stream waveform data to backend"""
        if not self.websocket:
            print("WebSocket not connected")
            return
            
        self.streaming = True
        print(f"Starting data streaming for session {self.session_id}")
        
        async for sample_buffer in self.sampler.start_sampling():
            if not self.streaming:
                break
                
            # Create packet
            packet = {
                "timestamp": time.time(),
                "session_id": self.session_id,
                "samples": sample_buffer
            }
            
            try:
                # Send packet
                message = ujson.dumps(packet)
                await self.websocket.send(message)
                print(f"Sent {len(sample_buffer)} samples")
                
            except Exception as e:
                print(f"Error sending data: {e}")
                break
    
    async def maintain_connection(self):
        """Maintain WebSocket connection with auto-reconnect"""
        while True:
            if not self.websocket or not self.streaming:
                print("Attempting to connect to backend...")
                if await self.connect_to_backend():
                    # Start streaming in background
                    asyncio.create_task(self.stream_data())
                    
                # Wait before retry
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(10)  # Check connection every 10 seconds
    
    def stop_streaming(self):
        """Stop data streaming"""
        self.streaming = False
        self.sampler.stop_sampling()
        if self.websocket:
            try:
                asyncio.create_task(self.websocket.close())
            except:
                pass
        print("Streaming stopped")
    
    def is_connected(self):
        return self.websocket is not None and self.streaming
