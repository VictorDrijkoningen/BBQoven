# pylint: skip-file

import machine
import uasyncio as asyncio
from microdot import Microdot,send_file
import gc
from ws import with_websocket
import math

with open(".env") as f:
        env = f.read().split(",")


async def blink():
    led = machine.Pin(2, machine.Pin.OUT)
    while True:
        led.value(0)
        await asyncio.sleep(0.25)
        led.value(1)
        await asyncio.sleep(2)


def thermistor(thermObj):
    # Define the beta value of the thermistor, typically provided in the datasheet
    beta = 3950

    # Read the voltage in microvolts and convert it to volts
    Vr = (3.3*float(thermObj.read_u16())/65535)

    # Calculate the resistance of the thermistor based on the measured voltage
    Rt = 100_000 * Vr / (3.3 - Vr)

    # Use the beta parameter and resistance value to calculate the temperature in Kelvin
    kelvin = 1 / (((math.log(Rt / 10_000)) / beta) + (1 / (273.15 + 25)))

    # Convert to Celsius
    Cel = kelvin - 273.15

    # Print the temperature values in Celsius
    print('Celsius: ' + str(Cel))

async def keep_reading():
    while True:
        print(thermistor(thermometer))
        await asyncio.sleep(1000)

fan = machine.PWM(machine.Pin(5))
fan.freq(50)
fan.duty(0)

heater = machine.PWM(machine.Pin(4))
heater.freq(50)
heater.duty(0)

thermometer = machine.ADC(0)

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
    await asyncio.gather(keep_reading(), blink(), webserver())

asyncio.run(main())

