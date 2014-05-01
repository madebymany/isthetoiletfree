#!/usr/bin/env python

import os
import hmac
import hashlib
import datetime
import urllib
import json

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpclient import AsyncHTTPClient
from gpiocrust import Header, PWMOutputPin, InputPin


def percentage_filter(function, iterable):
    count = 0
    for element in iterable:
        if function(element):
            count += 1
    return float(count) / float(len(iterable))


def one(iterable):
    elements = [e for e in iterable if e]
    return len(elements) == 1


SERVER_URL = os.getenv("ITTF_SERVER_URL", "http://localhost:8888/")
INTERVAL = 2000.0
HMAC_SECRET = open(os.path.join(os.path.dirname(__file__),
                                ".hmac_secret")).read().strip()

led_map = {"r": 8, "g": 10, "b": 12}
switch_map = (22, 24, 26)


class RGBLED(object):
    def __init__(self, r, g, b, hz=50.0, color=(0, 0, 0)):
        self.pulses = [PWMOutputPin(p, frequency=hz) for p in (r, g, b)]
        self._frequency = hz
        self._color = color

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, value):
        self._frequency = value
        for p in self.pulses:
            p.frequency = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        for p, c in zip(self.pulses, self._color):
            p.value = (c / 255.0) * 100.0

    def color_between(self, c1, c2, delta):
        return tuple(b + ((a - b) * delta) for a, b in zip(c1, c2))


class Toilet(object):
    def __init__(self, tid=None, pin=None):
        self.tid = tid
        self.pin = pin
        self.input = InputPin(self.pin)

    @property
    def is_free(self):
        return not self.input.value

    def has_changed_state(self):
        try:
            return self.is_free != self.latest_is_free
        except AttributeError:
            return True
        finally:
            self.latest_is_free = self.is_free


def call_server(params):
    data = json.dumps(params)
    AsyncHTTPClient().fetch(SERVER_URL, method="POST", body=urllib.urlencode({
        "data": data,
        "token": hmac.new(HMAC_SECRET, data, hashlib.sha256).hexdigest()
    }))


if __name__ == "__main__":
    with Header() as header:
        toilets = [Toilet(tid=i, pin=p) for i, p in enumerate(switch_map)]
        led = RGBLED(**led_map)

        def update_state():
            percentage_free = percentage_filter(
                lambda e: e, [t.is_free for t in toilets])
            led.color = led.color_between(
                (0, 255, 0), (255, 0, 0), percentage_free)

            timestamp = datetime.datetime.now().isoformat()
            params = []
            for t in toilets:
                if t.has_changed_state():
                    params.append(dict(
                        toilet_id=t.tid,
                        is_free="yes" if t.is_free else "no",
                        timestamp=timestamp
                    ))
            if len(params):
                call_server(params)

        try:
            PeriodicCallback(update_state, INTERVAL).start()
            IOLoop.instance().start()
        except KeyboardInterrupt:
            pass
