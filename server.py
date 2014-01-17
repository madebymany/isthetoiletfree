#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.escape
import hmac
import hashlib
import functools
import os
import sse
import momoko
import urlparse

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("db_host", default="localhost", help="database hostname", type=str)
define("db_port", default=5432, help="database port", type=int)
define("db_name", default="madebymany", help="database name", type=str)
define("db_user", default="madebymany", help="database username", type=str)
define("db_pass", default="", help="database password", type=str)

def get_psql_credentials():
    try:
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.getenv("DATABASE_URL"))
        return (url.hostname, url.port, url.path[1:], url.username,
                url.password)
    except:
        return (options.db_host, options.db_port, options.db_name,
                options.db_user, options.db_pass)


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
    @property
    def app(self):
        return self.application

    @property
    def db(self):
        return self.app.db

    def get(self):
        self.render("index.html",
                    has_free_toilet=self.app.has_free_toilet)

    @hmac_authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = tornado.escape.json_decode(self.get_argument("data"))
        has_free_toilet = data.get("has_free_toilet", None)
        if has_free_toilet:
            self.app.has_free_toilet = has_free_toilet
            SSEHandler.write_message_to_all("message", has_free_toilet)
        for i in xrange(self.app.num_toilets):
            value = data.get("toilet_%s" % i, None)
            if value:
                yield momoko.Op(self.db.execute,
                                "INSERT INTO events (toilet_id, is_free) "
                                "VALUES (%s, %s);", (i, value))
        self.finish()

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
    app.db = momoko.Pool(
        dsn="host=%s port=%s dbname=%s user=%s password=%s" % \
            get_psql_credentials(),
        size=1
    )
    app.num_toilets = 3
    app.has_free_toilet = "yes"
    tornado.options.parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
