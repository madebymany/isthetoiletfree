#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import tornado.gen
import tornado.websocket
import tornado.auth
import tornado.escape
import hmac
import hashlib
import functools
import os
import momoko
import urlparse
import time
import datetime
import parsedatetime
import prettytable
import logging

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("db_host", default="localhost", help="database hostname", type=str)
define("db_port", default=5432, help="database port", type=int)
define("db_name", default="callum", help="database name", type=str)
define("db_user", default="callum", help="database username", type=str)
define("db_pass", default="", help="database password", type=str)


class DateStrParser(object):
    def __init__(self):
        self.calendar = parsedatetime.Calendar()

    def parse(self, str):
        return datetime.datetime.fromtimestamp(
            time.mktime(self.calendar.parse(str)[0]))


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


def bool2str(boolean):
    return "yes" if boolean else "no"


class HasFreeWebSocketHandler(tornado.websocket.WebSocketHandler):
    connections = set()

    def open(self):
        HasFreeWebSocketHandler.connections.add(self)

    def on_message(self, message):
        pass

    def on_close(self):
        HasFreeWebSocketHandler.connections.remove(self)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        return self.get_secure_cookie("ittf_user")

    @tornado.gen.coroutine
    def has_free_toilet(self):
        cursor = yield momoko.Op(self.db.callproc, "has_free_toilet")
        raise tornado.gen.Return(cursor.fetchone()[0])


class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("openid.mode", None):
            email = (yield self.get_authenticated_user())["email"]
            if email.endswith("@madebymany.co.uk") or \
               email.endswith("@madebymany.com"):
                self.set_secure_cookie("ittf_user", email)
                self.redirect("/stats")
            self.redirect("/")
        else:
            yield self.authenticate_redirect()


class MainHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        has_free = bool2str((yield self.has_free_toilet()))
        self.render("index.html", has_free_toilet=has_free)

    @hmac_authenticated
    @tornado.gen.coroutine
    def post(self):
        values = yield [momoko.Op(self.db.mogrify,
            "(%(toilet_id)s, %(is_free)s, %(timestamp)s)", t) \
            for t in tornado.escape.json_decode(self.get_argument("data"))
        ]
        yield momoko.Op(self.db.execute,
                        "INSERT INTO events (toilet_id, is_free, recorded_at) "
                        "VALUES %s;" % ", ".join(values))
        self.notify_has_free()
        self.finish()

    @tornado.gen.coroutine
    def notify_has_free(self):
        for connected in HasFreeWebSocketHandler.connections:
            try:
                connected.write_message({
                    "hasFree": bool2str((yield self.has_free_toilet()))
                })
            except:
                logging.error("Error sending message", exc_info=True)


class StatsHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        parser = DateStrParser()
        parsed_start = None
        parsed_end = None
        text = None
        op = None
        clause = None
        start = self.get_argument("from", None)
        end = self.get_argument("to", None)

        if start and end:
            parsed_start = parser.parse(start)
            parsed_end = parser.parse(end)
            text = "Showing from %s til %s" % (parsed_start, parsed_end)
            op = ("WHERE recorded_at BETWEEN %s AND %s",
                  (parsed_start, parsed_end))
        elif start:
            parsed_start = parser.parse(start)
            text = "Showing from %s onward" % parsed_start
            op = ("WHERE recorded_at >= %s", (parsed_start,))
        elif end:
            parsed_end = parser.parse(end)
            text = "Showing from %s backward" % parsed_end
            op = ("WHERE recorded_at <= %s", (parsed_end,))

        if op:
            clause = yield momoko.Op(self.db.mogrify, *op)

        queries = [
            ("Number of visits",
             "SELECT toilet_id, count(*) "
             "AS num_visits FROM visits %(clause)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Average visit duration",
             "SELECT toilet_id, avg(duration) "
             "AS duration_avg FROM visits %(clause)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Minimum visit duration",
             "SELECT toilet_id, min(duration) "
             "AS duration_min FROM visits %(clause)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Maximum visit duration",
             "SELECT toilet_id, max(duration) "
             "AS duration_max FROM visits %(clause)s "
             "GROUP BY toilet_id ORDER BY toilet_id;")
        ]
        results = yield [momoko.Op(self.db.execute,
                                   q % {"clause": clause or ""}) \
                         for _, q in queries]

        self.render("stats.html", text=text, start=start, end=end,
                    tables=[(queries[i][0], prettytable.from_db_cursor(r)) \
                            for i, r in enumerate(results)])


class APIHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        response = tornado.escape.json_encode({
            "has_free_toilet": (yield self.has_free_toilet())
        })
        callback = self.get_argument("callback", None)
        if callback:
            response = "%s(%s)" % (callback, response)
        self.set_header("content-type", "application/json")
        self.write(response)


if __name__ == "__main__":
    app = tornado.web.Application(
        [(r"/login", GoogleLoginHandler),
         (r"/", MainHandler),
         (r"/stats", StatsHandler),
         (r"/api", APIHandler),
         (r"/hasfreesocket", HasFreeWebSocketHandler)],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        hmac_key=get_secret_key(),
        cookie_secret="CGT6NALTvnR8LpILJwyKGcwFzntjna7w",
        login_url="/login"
    )
    app.db = momoko.Pool(
        dsn=" ".join(["%s=%s" % c for c in get_psql_credentials().iteritems()]),
        size=1
    )
    tornado.options.parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
