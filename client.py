#!/usr/env/bin python

import RPi.GPIO as io
import requests
import sys

class Switch(object):
    def __init__(self, **kwargs):
        self.pin = kwargs["pin"]
        io.setup(self.pin, io.IN)

    @property
    def is_on(self):
      return io.input(self.pin)


PINS = (8, 16, 18)
switches = set()

def has_free():
    global switches
    return not all([s.is_on for s in switches])

def call_api(is_on):
    r = requests.post("SERVER_ADDRESS",
                     params={"is_free": "yes" if is_on else "no"})

if __name__ == "__main__":
    io.setmode(io.BOARD)
    for pin in PINS:
        switches.add(Switch(pin=pin))
    try:
        previous_state = has_free()
        while True:
            state = has_free()
            if state is not previous_state:
                call_api(state)
            previous_state = state
    except KeyboardInterrupt:
        pass
