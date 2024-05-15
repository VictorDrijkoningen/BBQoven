# pylint: skip-file

import machine
import uasyncio as asyncio
from microdot import Microdot,send_file
import gc
from ws import with_websocket
import math
import json
import time
from pid import PID


with open(".env") as f:
        env = f.read().split(",")

async def update_heater():
    global heater

    # heater.duty(heater_pid)


def disable_servo(device):
    device.duty(0)

def servo(device, input, inpmin=0, inpmax=180):
    def mapFromTo(x,a,b,c,d):
        y=(x-a)/(b-a)*(d-c)+c
        return y
    input = max(inpmin, min(inpmax,int(input)))
    try:
        device.duty(int(mapFromTo(input, inpmin, inpmax, 20, 130)))
    except:
        print("Servo not on")


def thermistor(thermObj):
    # Define the beta value of the thermistor, typically provided in the datasheet
    beta = 3950

    # Read the voltage in microvolts and convert it to volts
    Vr = thermObj.read_uv() / 1_000_000

    # Calculate the resistance of the thermistor based on the measured voltage
    Rt = 10_000 * Vr / (3.3 - Vr)

    # Use the beta parameter and resistance value to calculate the temperature in Kelvin
    kelvin = 1 / (((math.log(Rt / 10_000)) / beta) + (1 / (273.15 + 25)))

    # Convert to Celsius
    Cel = kelvin - 273.15

    # Print the temperature values in Celsius
    # print('Celsius: ' + str(Cel))
    return Cel

async def update_temp():
    global thermometer
    global GLOBAL_STATE
    while True:
        GLOBAL_STATE['temp1'].insert(0, round(thermistor(temp1),1))
        GLOBAL_STATE['temp2'].insert(0, round(thermistor(temp2),1))
        if len(GLOBAL_STATE['temp1']) > int(GLOBAL_STATE['graph_length']):
            GLOBAL_STATE['temp1'].pop()
            GLOBAL_STATE['temp2'].pop()
        await asyncio.sleep(1)

async def update_screen():
    global screen
    global GLOBAL_STATE
    
    if GLOBAL_STATE['cooling'] == True:
        screen.draw_text

fan = machine.PWM(machine.Pin(5))
fan.freq(50)
fan.duty(0)

heater = machine.PWM(machine.Pin(4))
heater.freq(50)
heater.duty(0)
heater_pid = PID(1,0,0, setpoint=0)

cooler = machine.PWM(machine.Pin(13))
cooler.freq(50)
cooler.duty(0)

servo(cooler, 90)
time.sleep(0.5)
disable_servo(cooler)



temp1 = machine.ADC(machine.Pin(32), atten=machine.ADC.ATTN_2_5DB)
temp1_cal = list()
temp2 = machine.ADC(machine.Pin(33), atten=machine.ADC.ATTN_2_5DB)
temp1_cal = list()


GLOBAL_STATE = dict()
GLOBAL_STATE['enabled'] = False
GLOBAL_STATE['heating'] = False
GLOBAL_STATE['cooling'] = False
GLOBAL_STATE['temp1'] = list()
GLOBAL_STATE['temp2'] = list()
GLOBAL_STATE['graph_length'] = 120



app = Microdot()

@app.route('/', methods=['GET'])
async def index(request):
    return send_file('index.html')

@app.route('/test', methods=['GET'])
async def test(request):
    return send_file('test.html')

@app.route('/chart.js', methods=['GET'])
async def chart(request):
    return send_file('chart.js')

@app.route('/shutdown', methods=['GET'])
async def shutdown(request):
    request.app.shutdown()
    return 'shutting down'

@app.route('/mem', methods=['GET'])
async def mem(request):
    return str(gc.mem_alloc()) + " used, " +  str(gc.mem_free()) + " free"

@app.route('/websocket')
@with_websocket
async def websocket(request, ws):
    global GLOBAL_STATE
    while True:
        message = await ws.receive()
        message = json.loads(message)

        if not 'refresh' in message:
            print("ws: "+str(message))

        if 'start_pressed' in message.keys():
            GLOBAL_STATE['enabled'] = not GLOBAL_STATE['enabled']
        if 'cooler' in message.keys():
            if message['cooler'] == 'off':
                disable_servo(cooler)
            else:
                servo(cooler, message['cooler'])
        
        await ws.send(json.dumps(GLOBAL_STATE))





async def webserver():
    await app.start_server(debug=True,host='0.0.0.0', port=80)


async def main():
    await asyncio.gather(update_temp(), webserver(), update_heater())

asyncio.run(main())

