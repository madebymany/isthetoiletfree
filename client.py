#!/usr/bin/env python

import requests
import hmac
import hashlib
import json
import os
import datetime
import time

from gpiocrust import Header, OutputPin, InputPin

def one(iterable):
    elements = [e for e in iterable if e]
    return len(elements) == 1


INTERVAL = 2.0
HMAC_SECRET = open(os.path.join(os.path.dirname(__file__),
                                ".hmac_secret")).read().strip()

leds = {"r": 8, "g": 10, "b": 12}
switches = (22, 24, 26)


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


def call_server(url_params):
    data = json.dumps(url_params)
    requests.post(os.getenv("ITTF_SERVER_URL"), params={
        "data": data,
        "token": hmac.new(HMAC_SECRET, data, hashlib.sha256).hexdigest()
    })


if __name__ == "__main__":
    with Header() as header:
        toilets = [Toilet(tid=i, pin=p) \
                   for i, p in enumerate(switches)]
        r, g, b = [OutputPin(p, value=False) \
                   for c, p in leds.iteritems()]
        try:
            while True:
                states = (t.is_free for t in toilets)
                has_one_free = one(states)
                has_any_free = any(states)
                r.value = has_one_free or not has_any_free
                g.value = has_one_free or has_any_free

                timestamp = datetime.datetime.now().isoformat()
                url_params = []
                for t in toilets:
                    if t.has_changed_state():
                        url_params.append({
                            "toilet_id": t.tid,
                            "is_free": "yes" if t.is_free else "no",
                            "timestamp": timestamp
                        })
                if len(url_params):
                    call_server(url_params)

                time.sleep(INTERVAL)
        except KeyboardInterrupt:
            pass

