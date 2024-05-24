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
from max6675 import MAX6675
# from rotary_irq_esp import RotaryIRQ

with open(".env") as f:
        env = f.read().split(",")


# def temp_R_253(runtime):
#     global GLOBAL_STATE
#     time_section = [0,90, 180, 240, 300]
#     temp_section = [0,150, 200, 250, 0]

#     assert len(time_section) == len(temp_section)

#     for i in range(len(time_section)):
#         if runtime < time_section[i]:
#             return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
#     GLOBAL_STATE['running'] = False
#     return 0


def temp_curve():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 0
    
    runtime = time.time() - GLOBAL_STATE['start_time']

    time_section = [0, 120, 500,]
    temp_section = [150, 150, 150,]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
    GLOBAL_STATE['running'] = False
    return 0


async def update_heater():
    global heater
    global heater_pid
    global temp1


    while True:
        await asyncio.sleep(1)
        if GLOBAL_STATE['running']:
            heater_pid.setpoint = temp_curve()
            duty = int(heater_pid(thermistor(temp1)))
            GLOBAL_STATE['heating_duty'] = duty
            heater.duty(duty)
            GLOBAL_STATE['heating'] = True
        else:
            heater_pid.setpoint = 0
            GLOBAL_STATE['heating'] = False
            GLOBAL_STATE['heating_duty'] = 0


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
    return thermObj.readCelsius()

async def update_fan():
    global fan
    global GLOBAL_STATE
    while True:
        await asyncio.sleep(1)
        if GLOBAL_STATE['running']:
            fan.duty(512)
        else:
            await asyncio.sleep(10)
            fan.duty(0)


async def update_temp():
    global thermometer
    global GLOBAL_STATE
    while True:
        GLOBAL_STATE['temp1'].insert(0, thermistor(temp1))
        GLOBAL_STATE['target_temp'].insert(0, round(temp_curve(),1))
        if len(GLOBAL_STATE['temp1']) > int(GLOBAL_STATE['graph_length']):
            GLOBAL_STATE['temp1'].pop()
            GLOBAL_STATE['target_temp'].pop()
        await asyncio.sleep(1)

async def update_screen():
    global screen
    global GLOBAL_STATE
    
    if GLOBAL_STATE['cooling'] == True:
        screen.draw_text

def setup_devices():
    global fan
    fan = machine.PWM(machine.Pin(26))
    fan.freq(50)
    fan.duty(0)

    global heater
    global heater_pid
    heater = machine.PWM(machine.Pin(25))
    heater.freq(50)
    heater.duty(0)
    heater_pid = PID(5,0.1,0, setpoint=0)
    heater_pid.output_limits = (0,50)

    global cooler
    cooler = machine.PWM(machine.Pin(13))
    cooler.freq(50)
    cooler.duty(0)

    servo(cooler, 90)
    time.sleep(0.25)
    disable_servo(cooler)

    # global encoder
    # encoder = RotaryIRQ(pin_num_clk=12, 
    #             pin_num_dt=13, 
    #             min_val=0,
    #             reverse=True, 
    #             range_mode=RotaryIRQ.RANGE_UNBOUNDED)

    # encoder.add_listener(encoder_listener())

    global temp1
    # temp1 = machine.SPI(2, baudrate=400, polarity=0, phase=0, bits=8, firstbit=0, sck=machine.Pin(18), mosi=machine.Pin(23), miso=machine.Pin(19))
    temp1 = MAX6675(so_pin=19, cs_pin=22, sck_pin=18)
    global CS_temp1
    CS_temp1 = machine.Pin(22)
    CS_temp1.value(1)
    

setup_devices()

GLOBAL_STATE = dict()
GLOBAL_STATE['running'] = False
GLOBAL_STATE['target_temp'] = list()
GLOBAL_STATE['heating'] = False
GLOBAL_STATE['heating_duty'] = False
GLOBAL_STATE['cooling'] = False
GLOBAL_STATE['start_time'] = False
GLOBAL_STATE['temp1'] = list()
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

        if 'start_run' in message:
            GLOBAL_STATE['start_time'] = time.time()
            GLOBAL_STATE['running'] = True

        if 'cooler' in message.keys():
            if message['cooler'] == 'off':
                disable_servo(cooler)
            else:
                servo(cooler, message['cooler'])
        if 'STOP' in message:
            GLOBAL_STATE['running'] = False
            GLOBAL_STATE['heating'] = False
        
        await ws.send(json.dumps(GLOBAL_STATE))





async def webserver():
    await app.start_server(debug=True,host='0.0.0.0', port=80)


async def main():
    await asyncio.gather(update_temp(), webserver(), update_heater(), update_fan())

def start():
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)

    heater.duty(0)
    fan.duty(0)

start()
