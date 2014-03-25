#!/usr/env/bin python

import time
import functools

class throttle(object):
    """
    Decorator that prevents a function from being called more than once every
    time period.

    To create a function that cannot be called more than once a second:

        @throttle(1)
        def my_fun():
            pass
    """
    def __init__(self, seconds, persist_return_value=False):
        self.throttle_period = seconds
        self.time_of_last_call = 0
        self.persist_return_value = persist_return_value
        self.last_return_value = None

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            now = time.time()
            time_since_last_call = now - self.time_of_last_call
            if time_since_last_call > self.throttle_period:
                self.time_of_last_call = now
                self.last_return_value = fn(*args, **kwargs)
                return self.last_return_value
            else:
                if self.persist_return_value:
                    return self.last_return_value
        return wrapper
