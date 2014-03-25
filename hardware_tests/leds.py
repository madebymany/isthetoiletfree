#!/usr/env/bin python

from RPi import GPIO
import time

GPIO.setmode(GPIO.BOARD)

PINS = (8, 10, 12)

for p in PINS:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, False)

try:
    r, g, b = PINS
    while True:
        GPIO.output(b, False)
        GPIO.output(r, True)
        time.sleep(1)
        GPIO.output(r, False)
        GPIO.output(g, True)
        time.sleep(1)
        GPIO.output(g, False)
        GPIO.output(b, True)
        time.sleep(1)
except KeyboardInterrupt:
    pass
