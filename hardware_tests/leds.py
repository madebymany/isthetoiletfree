#!/usr/env/bin python

from RPi import GPIO
from time import sleep

GPIO.setmode(GPIO.BOARD)

PINS = (8, 10, 12)

for p in PINS:
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, False)

r, g, b = PINS

try:
    while True:
        GPIO.output(b, False)
        GPIO.output(r, True)
        sleep(1)
        GPIO.output(r, False)
        GPIO.output(g, True)
        sleep(1)
        GPIO.output(g, False)
        GPIO.output(b, True)
        sleep(1)
except KeyboardInterrupt:
    pass
