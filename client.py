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

INTERVAL = 2
HMAC_SECRET = open(os.path.join(os.path.dirname(__file__),
                                ".hmac_secret")).read().strip()


class Toilet(object):
    def __init__(self, tid=None, pin=None):
        GPIO.setup(pin, GPIO.IN)
        self.tid = tid
        self.pin = pin

    @property
    def is_free(self):
        return not GPIO.input(self.pin)

    def has_changed_state(self):
        try:
            return self.is_free != self.latest_is_free
        except AttributeError:
            return True
        finally:
            self.latest_is_free = self.is_free


def call_server(url_params):
    data = json.dumps(url_params)
    requests.post(os.getenv("ITTF_SERVER_URL"), params={
        "data": data,
        "token": hmac.new(HMAC_SECRET, data, hashlib.sha256).hexdigest()
    })


leds = {"r": 8, "g": 10, "b": 12}
toilets = [Toilet(tid=i, pin=p) for i, p in enumerate([22, 24, 26])]

for c, p in leds.iteritems():
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, False)

try:
    while True:
        url_params = []
        for t in toilets:
            if t.has_changed_state():
                url_params.append({
                    "toilet_id": t.tid,
                    "is_free": "yes" if t.is_free else "no",
                    "timestamp": datetime.datetime.now().isoformat()
                })
        if len(url_params):
            call_server(url_params)
        has_free = any(t.is_free for t in toilets)
        GPIO.output(leds["r"], not has_free)
        GPIO.output(leds["g"], has_free)
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    pass
