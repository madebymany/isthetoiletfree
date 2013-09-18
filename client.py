#!/usr/env/bin python

import requests
import hmac
import hashlib
import sys
import os

def call_api(state, **kwargs):
    has_free_toilet = "yes" if state else "no"
    requests.post(kwargs["url"], params={
        "data": has_free_toilet,
        "token": hmac.new(
            kwargs["hmac_key"],
            has_free_toilet,
            hashlib.sha256
        ).hexdigest()
    })

if __name__ == "__main__":
    import RPi.GPIO as io
    base_path = os.path.dirname(__file__)

    API_URL = sys.argv[1]
    HMAC_KEY = open(os.path.join(base_path, ".hmac_key")).read().strip()
    PINS = (8, 16, 18)

    io.setmode(io.BOARD)
    for p in PINS:
        io.setup(p, io.IN)

    def has_open_switch(pins):
        return not all(io.input(p) for p in pins)

    try:
        prev_state = has_open_switch(PINS)
        while True:
            state = has_open_switch(PINS)
            if state != prev_state:
                call_api(state, url=API_URL, hmac_key=HMAC_KEY)
            prev_state = state
    except KeyboardInterrupt:
        pass
