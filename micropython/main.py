import uasyncio as asyncio
import time
import machine
from wifi import WiFiManager
from sampler import ADCSampler
from streamer import WebSocketStreamer

# WiFi configuration - UPDATE THESE VALUES
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# Backend server IP - UPDATE THIS VALUE
BACKEND_IP = "192.168.1.100"  # Your computer's IP address

class AudioWaveformAnalyzer:
    def __init__(self):
        self.wifi_manager = WiFiManager(WIFI_SSID, WIFI_PASSWORD)
        self.sampler = ADCSampler()
        self.streamer = WebSocketStreamer(self.wifi_manager, self.sampler)
        self.streamer.backend_url = f"ws://{BACKEND_IP}:8000/ws/audio"
        
        # Setup status LED
        self.led = machine.Pin(2, machine.Pin.OUT)  # Built-in LED
        
    async def start(self):
        """Start the audio waveform analyzer"""
        print("Starting ESP32 Audio Waveform Analyzer...")
        
        # Blink LED to indicate startup
        for _ in range(3):
            self.led.on()
            await asyncio.sleep(0.2)
            self.led.off()
            await asyncio.sleep(0.2)
        
        # Connect to WiFi
        ip = await self.wifi_manager.connect()
        if not ip:
            print("Failed to connect to WiFi")
            return
        
        # Start background tasks
        asyncio.create_task(self.wifi_manager.maintain_connection())
        asyncio.create_task(self.streamer.maintain_connection())
        
        # Keep main task running
        self.led.on()  # LED on when running
        print("System running. LED indicates active status.")
        
        try:
            while True:
                await asyncio.sleep(1)
                # Heartbeat - blink LED every 10 seconds
                if time.ticks_ms() % 10000 < 1000:
                    self.led.off()
                    await asyncio.sleep(0.1)
                    self.led.on()
                    
        except KeyboardInterrupt:
            print("Shutting down...")
            self.streamer.stop_streaming()
            self.led.off()

async def main():
    analyzer = AudioWaveformAnalyzer()
    await analyzer.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
        machine.reset()
