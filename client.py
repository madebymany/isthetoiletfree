#!/usr/env/bin python

import requests
import hmac
import hashlib
import json
import os
import sys
import datetime
import time

def call_api(url_params, **kwargs):
    data = json.dumps(url_params)
    requests.post(kwargs["url"], params={
        "data": data,
        "token": hmac.new(
            kwargs["hmac_key"],
            data,
            hashlib.sha256
        ).hexdigest()
    })

if __name__ == "__main__":
    import RPi.GPIO as io
    base_path = os.path.dirname(__file__)

    API_URL = os.getenv("ITTF_API_URL")
    HMAC_KEY = open(os.path.join(base_path, ".hmac_key")).read().strip()
    SWITCH_PINS = (22, 24, 26)
    RED_PIN = 8
    GREEN_PIN = 10
    BLUE_PIN = 12

    io.setmode(io.BOARD)
    for p in SWITCH_PINS:
        io.setup(p, io.IN)

    io.setup(RED_PIN, io.OUT)
    io.setup(GREEN_PIN, io.OUT)
    io.setup(BLUE_PIN, io.OUT)
    io.output(BLUE_PIN, False)

    try:
        prev_states = [io.input(p) for p in SWITCH_PINS]
        while True:
            url_params = {}
            for i, p in enumerate(SWITCH_PINS):
                state = io.input(p)
                if state != prev_states[i]:
                    url_params.update({
                        "toilet_%s" % i: {
                            "state": "yes" if not state else "no",
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                    })
                prev_states[i] = state
            if len(url_params):
                call_api(url_params, url=API_URL, hmac_key=HMAC_KEY)
            has_free = not all(prev_states)
            io.output(RED_PIN, not has_free)
            io.output(GREEN_PIN, has_free)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
