# pylint: skip-file

import machine
import uasyncio as asyncio


with open(".env") as f:
        env = f.read().split(",")


async def blink():
    led = machine.Pin(2, machine.Pin.OUT)
    while True:
        led.value(1)
        await asyncio.sleep(0.25)
        led.value(0)
        await asyncio.sleep(2)
    




async def do_something_else():
    pass

async def main():
    await asyncio.gather(blink(), do_something_else())

def start():
    asyncio.run(main())

start()
