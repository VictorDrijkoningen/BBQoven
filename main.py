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
# from rotary_irq_esp import RotaryIRQ

with open(".env") as f:
        env = f.read().split(",")


def curve1(runtime):
    time_section = [0,60, 90, 120, 150, 300]
    temp_section = [0,150, 200, 250, 250, 0]

    assert len(time_section) == len(temp_section)

    for i in range(len(time_section)):
        if runtime < time_section[i]:
            return  temp_section[i-1] + (temp_section[i] - temp_section[i-1])/(time_section[i]-time_section[i-1]) * (runtime-time_section[i-1])


async def update_heater():
    global heater
    global heater_pid
    global temp1


    while True:
        await asyncio.sleep(1)
        if GLOBAL_STATE['running']:
            heater_pid.setpoint = curve1()
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

def setup_devices():
    global fan
    fan = machine.PWM(machine.Pin(5))
    fan.freq(50)
    fan.duty(0)

    global heater
    global heater_pid
    heater = machine.PWM(machine.Pin(4))
    heater.freq(50)
    heater.duty(0)
    heater_pid = PID(1,0.1,0, setpoint=0)
    heater_pid.output_limits = (0,1023)

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
    temp1 = machine.ADC(machine.Pin(32), atten=machine.ADC.ATTN_2_5DB)
    global temp2
    temp2 = machine.ADC(machine.Pin(33), atten=machine.ADC.ATTN_2_5DB)

setup_devices()

GLOBAL_STATE = dict()
GLOBAL_STATE['running'] = False
GLOBAL_STATE['heating'] = False
GLOBAL_STATE['heating_duty'] = False
GLOBAL_STATE['cooling'] = False
GLOBAL_STATE['start_time'] = False
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
            GLOBAL_STATE['running'] = not GLOBAL_STATE['running']

        if 'start_run' in message:
            GLOBAL_STATE['start_time'] = time.time()
            GLOBAL_STATE['running'] = True

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

