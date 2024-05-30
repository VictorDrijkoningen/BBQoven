# pylint: skip-file

from machine import Pin, PWM
import uasyncio as asyncio
from microdot import Microdot,send_file
import gc
from ws import with_websocket
import math
import json
import time
from pid import PID
from max6675 import MAX6675
from micropython import alloc_emergency_exception_buf
# from rotary_irq_esp import RotaryIRQ

alloc_emergency_exception_buf(100)

# def temp_R_253():
#     time_section = [0,90, 180, 240, 300]
#     temp_section = [0,150, 200, 250, 0]



def temp_curve_points():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 0
    
    runtime = time.time() - GLOBAL_STATE['start_time']

    time_section = [0,90, 180, 240, 260, 630]
    temp_section = [30,75,75, 150, 150, 20]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
    GLOBAL_STATE['running'] = False
    return 0

def temp_curve_points_test():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 0
    
    runtime = time.time() - GLOBAL_STATE['start_time']

    time_section = [0,180, 300, 500, ]
    temp_section = [30,100, 100, 0, ]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
    GLOBAL_STATE['running'] = False
    return 0

def temp_curve_sine():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 0

    runtime = time.time() - GLOBAL_STATE['start_time']

    return 112.5 + 12.5*math.sin(runtime/40 - math.pi/2)

def one_temp():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 0
    runtime = time.time() - GLOBAL_STATE['start_time']
    if runtime < 180:
        return 250
    else:
        GLOBAL_STATE['running'] = False
        return 0

using_curve = one_temp

async def update_heater():
    global heater
    global heater_pid
    global cooler
    global cooler_pid
    global temp1

    target_temp = using_curve()
    pos = 0


    while True:
        await asyncio.sleep(1)
        target_temp_last = target_temp
        target_temp = using_curve()
        actual_temp = thermocouple(temp1)


        if GLOBAL_STATE['running'] and target_temp + 0.25 > target_temp_last:
            heater_pid.setpoint = target_temp
            duty = int(heater_pid(actual_temp))
            GLOBAL_STATE['heating_duty'] = duty
            heater.duty(duty)
            GLOBAL_STATE['cooling'] = False
            GLOBAL_STATE['heating'] = True
        else:
            heater.duty(0)
            GLOBAL_STATE['heating_duty'] = 0
        
        if GLOBAL_STATE['running'] and target_temp -0.25 < target_temp_last:
            cooler_pid.setpoint = target_temp
            pos = int(cooler_pid(actual_temp))
            GLOBAL_STATE['cooling_pos'] = pos
            servo(cooler, pos)
            GLOBAL_STATE['cooling'] = True
            GLOBAL_STATE['heating'] = False
        else:
            if not pos == 90:
                pos = 90
                servo(cooler, pos)
                await asyncio.sleep(1)
            GLOBAL_STATE['cooling_pos'] = pos

        if not GLOBAL_STATE['running']:
            disable_servo(cooler)
            

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

def thermocouple(thermObj):
    global GLOBAL_STATE
    try:
        out = thermObj.readCelsius()
        return out
    except ValueError:
        GLOBAL_STATE['running'] = False
        GLOBAL_STATE['error_detected'] = True
        return -1

async def update_fan():
    global fan
    global GLOBAL_STATE
    been_on = False
    while True:
        await asyncio.sleep(1)
        if GLOBAL_STATE['running']:
            fan.duty(512)
            been_on = True
        else:
            if been_on:
                await asyncio.sleep(240)
                been_on = False
            fan.duty(0)


async def update_temp():
    global thermometer
    global GLOBAL_STATE
    while True:
        GLOBAL_STATE['temp1'].append(thermocouple(temp1))
        GLOBAL_STATE['temp2'].append(thermocouple(temp2))
        GLOBAL_STATE['target_temp'].append(round(using_curve(),2))
        if len(GLOBAL_STATE['temp1']) > int(GLOBAL_STATE['graph_length']):
            GLOBAL_STATE['temp1'].pop(0)
            GLOBAL_STATE['temp2'].pop(0)
            GLOBAL_STATE['target_temp'].pop(0)
        await asyncio.sleep(1)
        GLOBAL_STATE['memfree'] = round(gc.mem_free()/1024)

def setup_devices():
    global fan
    fan = PWM(Pin(26))
    fan.freq(50)
    fan.duty(0)

    global heater
    global heater_pid
    heater = PWM(Pin(25))
    heater.freq(50)
    heater.duty(0)
    heater_pid = PID(25,0.2,10, setpoint=0)
    heater_pid.output_limits = (0,820)

    global cooler
    global cooler_pid
    cooler = PWM(Pin(13))
    cooler.freq(50)
    cooler.duty(0)
    cooler_pid = PID(-5,0,0, setpoint=0)
    cooler_pid.output_limits = (135,180)

    global temp1
    temp1 = MAX6675(so_pin=19, cs_pin=22, sck_pin=18)
    global temp2
    temp2 = MAX6675(so_pin=19, cs_pin=23, sck_pin=18)

setup_devices()

GLOBAL_STATE = dict()
GLOBAL_STATE['running'] = False
GLOBAL_STATE['target_temp'] = list()
GLOBAL_STATE['heating'] = False
GLOBAL_STATE['heating_duty'] = False
GLOBAL_STATE['cooling'] = False
GLOBAL_STATE['cooling_pos'] = 0
GLOBAL_STATE['start_time'] = False
GLOBAL_STATE['temp1'] = list()
GLOBAL_STATE['temp2'] = list()
GLOBAL_STATE['graph_length'] = 120
GLOBAL_STATE['memfree'] = 0
GLOBAL_STATE['error_detected'] = False



app = Microdot()

@app.route('/', methods=['GET'])
async def index(request):
    return send_file('index.html')

@app.route('/chart.js', methods=['GET'])
async def chart(request):
    return send_file('chart.js')

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

        if 'start_run' in message:
            GLOBAL_STATE['start_time'] = time.time()
            GLOBAL_STATE['running'] = True

        # if 'cooler' in message.keys():
        #     if message['cooler'] == 'off':
        #         disable_servo(cooler)
        #     else:
        #         servo(cooler, message['cooler'])
        if 'STOP' in message:
            GLOBAL_STATE['running'] = False
            GLOBAL_STATE['heating'] = False
            GLOBAL_STATE['cooling'] = False
        
        await ws.send(json.dumps(GLOBAL_STATE))





async def webserver():
    await app.start_server(debug=True,host='0.0.0.0', port=80)


async def main():
    await asyncio.gather(update_temp(), webserver(), update_heater(), update_fan(), )

def start():
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
        print("ERROR")

    heater.duty(0)

start()
