#!/usr/env/bin python

import requests
import hmac
import hashlib
import json
import os
import datetime

from throttle import throttle
from RPi import GPIO

GPIO.setmode(GPIO.BOARD)

HMAC_KEY = open(os.path.join(os.path.dirname(__file__),
                             ".hmac_key")).read().strip()

class Switch(object):
    def __init__(self, pin):
        GPIO.setup(pin, GPIO.IN)
        self.pin = pin
        self.prev_state = self._state

    @property
    def _state(self):
        return not GPIO.input(self.pin)

    @throttle(3, persist_return_value=True)
    def is_open(self):
        return self._state

    def has_changed_state(self):
        current_state = self.is_open()
        has_changed = current_state != self.prev_state
        self.prev_state = current_state
        return has_changed

def call_api(url_params):
    data = json.dumps(url_params)
    requests.post(os.getenv("ITTF_API_URL"), params={
        "data": data,
        "token": hmac.new(
            HMAC_KEY,
            data,
            hashlib.sha256
        ).hexdigest()
    })

leds = {"r": 8, "g": 10, "b": 12}
switches = [Switch(p) for p in (22, 24, 26)]

for c, p in leds.iteritems():
    GPIO.setup(p, GPIO.OUT)

GPIO.output(leds["b"], False)

if __name__ == "__main__":
    try:
        while True:
            url_params = []
            for i, s in enumerate(switches):
                if s.has_changed_state():
                    url_params.append({
                        "toilet_id": i,
                        "is_free": "yes" if not state else "no",
                        "timestamp": datetime.datetime.now().isoformat()
                    })
            if len(url_params):
                call_api(url_params)
            is_free = any(s.prev_state for s in switches)
            GPIO.output(RED_PIN, not is_free)
            GPIO.output(GREEN_PIN, is_free)
    except KeyboardInterrupt:
        pass
