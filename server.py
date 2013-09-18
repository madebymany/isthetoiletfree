#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import hmac
import hashlib
import functools
import os
import sse

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

def get_secret_key():
    try:
        with open(os.path.join(os.path.dirname(__file__), ".hmac_key")) as f:
            return f.read().strip()
    except IOError:
        return os.getenv("ITTF_HMAC_KEY")


def hmac_authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        hash = hmac.new(
            self.settings["hmac_key"],
            self.get_argument("data"),
            hashlib.sha256
        )
        if self.get_argument("token") != hash.hexdigest():
            raise tornado.web.HTTPError(401, "Invalid token")
        return method(self, *args, **kwargs)
    return wrapper

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html",
                    has_free_toilet=self.application.has_free_toilet)

    @hmac_authenticated
    def post(self):
        has_free_toilet = self.application.has_free_toilet =\
                          self.get_argument("data")
        SSEHandler.write_message_to_all("message", has_free_toilet)

class SSEHandler(sse.SSEHandler):
    pass

if __name__ == "__main__":
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/sse", SSEHandler),
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        hmac_key=get_secret_key()
    )
    app.has_free_toilet = "yes"
    tornado.options.parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
