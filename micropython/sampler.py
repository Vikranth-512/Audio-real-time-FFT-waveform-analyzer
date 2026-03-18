import machine
import time
import uasyncio as asyncio
from micropython import const

ADC_PIN = const(34)
SAMPLE_RATE = const(8000)
BUFFER_SIZE = const(512)
ADC_RESOLUTION = const(4095)

class ADCSampler:

    def __init__(self):

        self.adc = machine.ADC(machine.Pin(ADC_PIN))
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.adc.width(machine.ADC.WIDTH_12BIT)

        self.sample_buffer = [0] * BUFFER_SIZE
        self.buffer_index = 0

        self.sampling = False

        self.sample_interval_us = int(1000000 / SAMPLE_RATE)


    async def start_sampling(self):

        self.sampling = True

        print(f"Starting ADC sampling at {SAMPLE_RATE} Hz")

        next_sample_time = time.ticks_us()

        while self.sampling:

            now = time.ticks_us()

            if time.ticks_diff(now, next_sample_time) >= 0:

                sample = self.adc.read()

                self.sample_buffer[self.buffer_index] = sample
                self.buffer_index += 1

                next_sample_time = time.ticks_add(
                    next_sample_time,
                    self.sample_interval_us
                )

                if self.buffer_index >= BUFFER_SIZE:

                    packet = list(self.sample_buffer)

                    self.buffer_index = 0

                    yield packet

            else:

                await asyncio.sleep_ms(0)


    def stop_sampling(self):

        self.sampling = False

        print("ADC sampling stopped")


    def get_buffer(self):

        if self.buffer_index > 0:

            buffer = self.sample_buffer[:self.buffer_index]

            self.buffer_index = 0

            return buffer

        return None


    def is_active(self):

        return self.sampling
