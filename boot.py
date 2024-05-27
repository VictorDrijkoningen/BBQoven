# pylint: skip-file

# This file is executed on every boot (including wake-boot from deepsleep)
import gc
import webrepl
import network

webrepl.start()

network.hostname('ReflowOven')
ap = network.WLAN(network.AP_IF)
ap.config(essid="ReflowOven")
ap.active(True)

gc.collect()

