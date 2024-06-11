# pylint: skip-file
import os
from machine import Pin, PWM
import uasyncio as asyncio
from microdot import Microdot,send_file
import gc
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

outfile = "temps.csv"

def smd4300ax10():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 20
    
    runtime = time.time() - GLOBAL_STATE['start_time']

    time_section = [0, 60,  150, 180, 210, 240, 270, 500]
    temp_section = [30,100, 150, 183, 235, 235, 183, 60]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
    GLOBAL_STATE['running'] = False
    return 20

def temp_curve_points():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 20
    
    runtime = time.time() - GLOBAL_STATE['start_time']

    time_section = [0,150, 270, 330, 360, 470]
    temp_section = [30,100, 110, 150, 150, 30]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
    GLOBAL_STATE['running'] = False
    return 20

def temp_curve_points_test():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 20
    
    runtime = time.time() - GLOBAL_STATE['start_time']

    time_section = [0,180, 300, 500, ]
    temp_section = [30,100, 100, 0, ]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])
    GLOBAL_STATE['running'] = False
    return 20

def temp_curve_sine():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 20

    runtime = time.time() - GLOBAL_STATE['start_time']

    return 112.5 + 12.5*math.sin(runtime/40 - math.pi/2)

def one_temp():
    global GLOBAL_STATE

    if not GLOBAL_STATE['running']:
        return 20
    runtime = time.time() - GLOBAL_STATE['start_time']
    if runtime < 400:
        return 50
    else:
        GLOBAL_STATE['running'] = False
        return 20

using_curve = smd4300ax10

async def update_heater():
    global heater
    global heater_pid
    global cooler
    global cooler_pid
    global temp1

    target_temp = using_curve()
    pos = 0


    while not GLOBAL_STATE['shutdown']:
        await asyncio.sleep(1)
        target_temp_last = target_temp
        target_temp = using_curve()
        actual_temp = thermocouple(temp1)
        # print("update heater: ", actual_temp, "  ", time.time())
        # print("update target: ", target_temp)


        if GLOBAL_STATE['running'] and target_temp + 0.25 > target_temp_last:
            heater_pid.setpoint = target_temp
            duty = int(heater_pid(actual_temp))
            GLOBAL_STATE['heating_duty'] = duty
            heater.duty(duty)
            GLOBAL_STATE['cooling'] = False
            GLOBAL_STATE['heating'] = True
            # print("update heater duty: ", duty)

        else:
            heater.duty(0)
            GLOBAL_STATE['heating_duty'] = 0
        
        if GLOBAL_STATE['running']:
            cooler_pid.setpoint = target_temp
            pos = int(cooler_pid(actual_temp))
            GLOBAL_STATE['cooling_pos'] = pos
            servo(cooler, pos)
            GLOBAL_STATE['cooling'] = True
            GLOBAL_STATE['heating'] = False
        else:
            if not pos == -1:
                servo(cooler, 150)
                await asyncio.sleep(1.5)
                pos = -1
                GLOBAL_STATE['cooling_pos'] = pos
                disable_servo(cooler)
        # else:
        #     if not pos == 90:
        #         pos = 90
        #         servo(cooler, pos)
        #         await asyncio.sleep(1)
        #     GLOBAL_STATE['cooling_pos'] = pos

        # if not GLOBAL_STATE['running']:
        #     disable_servo(cooler)
         
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
    while not GLOBAL_STATE['shutdown']:
        await asyncio.sleep(5)
        if GLOBAL_STATE['running']:
            fan.duty(1023)
            been_on = True
        else:
            if been_on:
                await asyncio.sleep(240)
                been_on = False
            fan.duty(450)

async def update_temp():
    global thermometer
    global heater
    global heater_pid
    global fan
    global GLOBAL_STATE
    with open(outfile, mode="w") as f:
        f.write("time,target_temp,t1,t2,heating_duty,cooling_pos,fan_duty, PID:"+str(heater_pid.Kp)+"-"+str(heater_pid.Ki)+"-"+str(heater_pid.Kd)+"- diffOM: " + str(heater_pid.differential_on_measurement)+"\n")
    
    while not GLOBAL_STATE['shutdown']:

        await asyncio.sleep(1)
        t1 = thermocouple(temp1)
        t2 = thermocouple(temp2)
        GLOBAL_STATE['temp1'].append(t1)
        GLOBAL_STATE['temp2'].append(t2)

        if GLOBAL_STATE['download']:
            GLOBAL_STATE['not_saving'] = True
        else:
            GLOBAL_STATE['not_saving'] = False
            try:
                with open(outfile, mode="a") as f:
                    f.write(str(time.time())+","+str(using_curve())+","+str(t1)+","+str(t2)+","+str(heater.duty())+","+str(GLOBAL_STATE['cooling_pos'])+","+str(fan.duty())+"\n")
            except Exception as e:
                print("writing file error!! [", e, "]")
        
        GLOBAL_STATE['target_temp'].append(round(using_curve(),2))
        if len(GLOBAL_STATE['temp1']) > int(GLOBAL_STATE['graph_length']):
            GLOBAL_STATE['temp1'].pop(0)
            GLOBAL_STATE['temp2'].pop(0)
            GLOBAL_STATE['target_temp'].pop(0)
        GLOBAL_STATE['memfree'] = round(gc.mem_free()/1024)
        gc.collect()

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
    heater_pid = PID(120,0,840, setpoint=20, )
    heater_pid.output_limits = (0,1023)

    global cooler
    global cooler_pid
    cooler = PWM(Pin(13))
    cooler.freq(50)
    cooler.duty(0)
    cooler_pid = PID(-10,0,0, setpoint=20)
    cooler_pid.output_limits = (35,150)


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
GLOBAL_STATE['download'] = False
GLOBAL_STATE['shutdown'] = False
GLOBAL_STATE['pid'] = str(heater_pid.Kp) + "-" + str(heater_pid.Ki) + "-" + str(heater_pid.Kd)

app = Microdot()

@app.route('/', methods=['GET'])
async def index(request):
    return send_file('index.html')

@app.route('/chart.js', methods=['GET'])
async def chart(request):
    return send_file('chart.js')


@app.route('/shutdown', methods=['GET'])
async def shutdown(request):
    heater.duty(0)
    fan.duty(400)
    request.app.shutdown()
    GLOBAL_STATE['shutdown'] = True
    
@app.route('/start', methods=['GET'])
async def start(request):
    print("start signal")
    GLOBAL_STATE['start_time'] = time.time()
    GLOBAL_STATE['running'] = True

@app.route('/stop', methods=['GET'])
async def stop(request):
    print("stop signal")
    GLOBAL_STATE['running'] = False
    GLOBAL_STATE['heating'] = False
    GLOBAL_STATE['cooling'] = False

@app.route('/temps.csv', methods=['GET'])
async def temp(request):
    GLOBAL_STATE['download'] = True
    while not GLOBAL_STATE['not_saving']:
        await asyncio.sleep(0.5)
    out = send_file('temps.csv')
    GLOBAL_STATE['download'] = False
    return out

@app.route('/data', methods=['GET'])
async def data(request):
    return json.dumps(GLOBAL_STATE)

@app.route('/mem', methods=['GET'])
async def mem(request):
    return str(gc.mem_alloc()) + " used, " +  str(gc.mem_free()) + " free"


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
    import webrepl
    webrepl.start()

start()