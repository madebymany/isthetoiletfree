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

def hmac_authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        hash = hmac.new(self.settings["hmac_key"],
                        self.get_argument("data"))
        if self.get_argument("token") != hash.hexdigest():
            raise tornado.web.HTTPError(403, "Authentication required")
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
    base_path = os.path.dirname(__file__)
    app = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/sse", SSEHandler),
        ],
        template_path=os.path.join(base_path, "templates"),
        hmac_key=open(os.path.join(base_path, ".hmac_key")).read().strip()
    )
    app.has_free_toilet = "yes"
    tornado.options.parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
