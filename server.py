#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.escape
import hmac
import hashlib
import functools
import os
import momoko
import urlparse

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("db_host", default="localhost", help="database hostname", type=str)
define("db_port", default=5432, help="database port", type=int)
define("db_name", default="callum", help="database name", type=str)
define("db_user", default="callum", help="database username", type=str)
define("db_pass", default="", help="database password", type=str)

def get_psql_credentials():
    try:
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.getenv("DATABASE_URL"))
        credentials = { "host": url.hostname, "port": url.port,
                        "dbname": url.path[1:], "user": url.username,
                        "password": url.password }
    except:
        credentials = { "host": options.db_host, "port": options.db_port,
                        "dbname": options.db_name, "user": options.db_user,
                        "password": options.db_pass }
    return credentials


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
    def db(self):
        return self.application.db

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        cursor = yield momoko.Op(self.db.execute,
                                 "WITH latest_events AS ("
                                 "SELECT DISTINCT ON (toilet_id) * FROM events "
                                 "ORDER BY toilet_id, recorded_at DESC) "
                                 "SELECT EXISTS "
                                 "(SELECT 1 FROM latest_events WHERE is_free);")
        self.render("index.html",
                    has_free_toilet="yes" if cursor.fetchone()[0] else "no")

    @hmac_authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        for t in tornado.escape.json_decode(self.get_argument("data")):
            yield momoko.Op(self.db.execute,
                            "INSERT INTO events "
                            "(toilet_id, is_free, recorded_at) "
                            "VALUES (%s, %s, %s);",
                            (t["toilet_id"], t["is_free"], t["timestamp"]))
        self.finish()

if __name__ == "__main__":
    app = tornado.web.Application(
        [(r"/", MainHandler)],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        hmac_key=get_secret_key()
    )
    app.db = momoko.Pool(
        dsn=" ".join(["%s=%s" % c for c in get_psql_credentials().iteritems()]),
        size=1
    )
    tornado.options.parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
