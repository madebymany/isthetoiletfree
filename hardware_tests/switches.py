#!/usr/env/bin python

from RPi import GPIO

GPIO.setmode(GPIO.BOARD)

PINS = (22, 24, 26)

for p in PINS:
    GPIO.setup(p, GPIO.IN)

while True:
    for p in PINS:
        if GPIO.input(p):
            print "%s on" % p
