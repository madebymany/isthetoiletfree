#!/usr/env/bin python

import requests
import hmac
import hashlib
import json
import os
import datetime
import time

from RPi import GPIO

GPIO.setmode(GPIO.BOARD)

SLEEP = 3
HMAC_KEY = open(os.path.join(os.path.dirname(__file__),
                             ".hmac_key")).read().strip()

class Toilet(object):
    def __init__(self, pin):
        GPIO.setup(pin, GPIO.IN)
        self.pin = pin
        self.latest_is_free = self.is_free

    @property
    def is_free(self):
        return not GPIO.input(self.pin)

    def has_changed_state(self):
        is_free = self.is_free
        has_changed = is_free != self.latest_is_free
        self.latest_is_free = is_free
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
toilets = [Toilet(p) for p in (22, 24, 26)]

for c, p in leds.iteritems():
    GPIO.setup(p, GPIO.OUT)

GPIO.output(leds["b"], False)

try:
    while True:
        url_params = []
        for i, t in enumerate(toilets):
            if t.has_changed_state():
                url_params.append({
                    "toilet_id": i,
                    "is_free": "yes" if t.is_free else "no",
                    "timestamp": datetime.datetime.now().isoformat()
                })
        if len(url_params):
            call_api(url_params)
        has_free = any(t.is_free for t in toilets)
        GPIO.output(leds["r"], not has_free)
        GPIO.output(leds["g"], has_free)
        time.sleep(SLEEP)
except KeyboardInterrupt:
    pass
