# pylint: skip-file

import machine
import uasyncio as asyncio
from microdot import Microdot,send_file
import gc
from ws import with_websocket

with open(".env") as f:
        env = f.read().split(",")


async def blink():
    led = machine.Pin(2, machine.Pin.OUT)
    while True:
        led.value(0)
        await asyncio.sleep(0.25)
        led.value(1)
        await asyncio.sleep(2)


def thermistor(pin: int):
    therm = machine.ADC(pin)
    # todo one wire digital temp sens?
    #return somefunction(therm.read())


fan = machine.PWM(machine.Pin(5))
fan.freq(50)
fan.duty(0)

heater = machine.PWM(machine.Pin(4))
heater.freq(50)
heater.duty(0)


app = Microdot()

@app.route('/', methods=['GET'])
async def index(request):
    return send_file('index.html')

@app.route('/mem', methods=['GET'])
async def index(request):
    return str(gc.mem_alloc()) + " used, " +  str(gc.mem_free()) + " free"

@app.route('/shutdown', methods=['GET'])
async def shutdown(request):
    request.app.shutdown()
    return 'shutting down'

@app.route('/websocket')
@with_websocket
async def websocket(request, ws):
    while True:
        message = await ws.receive()
        print("ws: "+message)
        await ws.send("rcvd")





async def webserver():
    await app.start_server(debug=True,host='0.0.0.0', port=80)


async def main():
    await asyncio.gather(blink(), webserver())

asyncio.run(main())

