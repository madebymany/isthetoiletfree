#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import sse
import os

is_free = "yes"

class SSEHandler(sse.SSEHandler):
    pass

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        global is_free
        self.render("index.html", is_free=is_free)

    def post(self):
        global is_free
        is_free = self.get_argument("is_free", is_free)
        SSEHandler.write_message_to_all("message", is_free)

app = tornado.web.Application(
    [
        (r"/", MainHandler),
        (r"/sse", SSEHandler),
    ],
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)

if __name__ == "__main__":
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
