#!/usr/env/bin python

from RPi import GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)

PINS = (22, 24, 26)

latest_states = {}
for p in PINS:
    GPIO.setup(p, GPIO.IN)
    latest_states[p] = GPIO.input(p)

try:
    while True:
        for p in PINS:
            state = GPIO.input(p)
            if state and state != latest_states[p]:
                print "%s on" % p
            latest_states[p] = state
        sleep(0.5)
except KeyboardInterrupt:
    pass
