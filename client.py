#!/usr/env/bin python

import requests
import hmac
import hashlib
import json
import os

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

    def has_open_switch(pins):
        return not all(io.input(p) for p in pins)

    def bool2str(b):
        return "yes" if b else "no"

    try:
        prev_has_free = has_open_switch(SWITCH_PINS)
        prev_states = [io.input(p) for p in SWITCH_PINS]
        while True:
            url_params = {}
            has_free = has_open_switch(SWITCH_PINS)
            io.output(RED_PIN, not has_free)
            io.output(GREEN_PIN, has_free)
            if has_free != prev_has_free:
                url_params.update({
                    "has_free_toilet": bool2str(has_free)
                })
            prev_has_free = has_free
            for i, p in enumerate(SWITCH_PINS):
                state = io.input(p)
                if state != prev_states[i]:
                    url_params.update({
                        "toilet_%s" % i: bool2str(not state)})
                prev_states[i] = state
            if len(url_params):
                call_api(url_params, url=API_URL, hmac_key=HMAC_KEY)
    except KeyboardInterrupt:
        pass
