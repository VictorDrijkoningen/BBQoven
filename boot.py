# pylint: skip-file

# This file is executed on every boot (including wake-boot from deepsleep)
# import webrepl
import network
import time
# webrepl.start()

network.hostname('ReflowOven')
ap = network.WLAN(network.AP_IF)
ap.config(ssid="ReflowOven")
ap.active(True)

time.sleep(0.5)
