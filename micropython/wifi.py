import network
import time
import uasyncio as asyncio

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        self.connected = False
        
    async def connect(self):
        """Connect to WiFi network with auto-reconnect"""
        self.wlan.active(True)
        
        if not self.wlan.isconnected():
            print(f"Connecting to {self.ssid}...")
            self.wlan.connect(self.ssid, self.password)
            
            # Wait for connection with timeout
            timeout = 20
            while not self.wlan.isconnected() and timeout > 0:
                await asyncio.sleep(1)
                timeout -= 1
                print(".")
                
            if self.wlan.isconnected():
                self.connected = True
                ip = self.wlan.ifconfig()[0]
                print(f"Connected! IP: {ip}")
                return ip
            else:
                print("Failed to connect")
                return None
        else:
            self.connected = True
            ip = self.wlan.ifconfig()[0]
            print(f"Already connected. IP: {ip}")
            return ip
    
    async def maintain_connection(self):
        """Maintain WiFi connection with auto-reconnect"""
        while True:
            if not self.wlan.isconnected():
                print("WiFi disconnected, attempting reconnect...")
                self.connected = False
                await self.connect()
            await asyncio.sleep(10)  # Check every 10 seconds
    
    def is_connected(self):
        return self.connected and self.wlan.isconnected()
    
    def get_ip(self):
        if self.is_connected():
            return self.wlan.ifconfig()[0]
        return None
