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
import ascii_graph
import logging

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("db_host", default="localhost", help="database hostname", type=str)
define("db_port", default=5432, help="database port", type=int)
define("db_name", default="callum", help="database name", type=str)
define("db_user", default="callum", help="database username", type=str)
define("db_pass", default="", help="database password", type=str)


class HumanDateParser(object):
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


def _get_secret(filename, envvar):
    try:
        with open(os.path.join(os.path.dirname(__file__), filename)) as f:
            return f.read().strip()
    except IOError:
        return os.getenv(envvar)

get_hmac_secret = \
    functools.partial(_get_secret, ".hmac_secret", "ITTF_HMAC_SECRET")
get_cookie_secret = \
    functools.partial(_get_secret, ".cookie_secret", "ITTF_COOKIE_SECRET")


def hmac_authenticated(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        hash = hmac.new(
            self.settings["hmac_secret"],
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
        cursor = yield momoko.Op(self.db.callproc, "any_are_free")
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
        has_free = bool2str((yield self.has_free_toilet()))
        for connected in HasFreeWebSocketHandler.connections:
            try:
                connected.write_message({
                    "hasFree": has_free
                })
            except:
                logging.error("Error sending message", exc_info=True)


class StatsHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        parser = HumanDateParser()
        text = None
        op = None
        where = ""
        and_where = ""
        start = self.get_argument("from", None)
        end = self.get_argument("to", None)

        if start and end:
            parsed_start = parser.parse(start)
            parsed_end = parser.parse(end)
            text = "Showing from %s to %s" % (parsed_start, parsed_end)
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
            where = yield momoko.Op(self.db.mogrify, *op)
            and_where = where.replace("WHERE", "AND", 1)

        queries = [
            ("Number of visits",
             "SELECT toilet_id, count(*) "
             "AS num_visits FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Average visit duration",
             "SELECT toilet_id, avg(duration) "
             "AS duration_avg FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Minimum visit duration",
             "SELECT toilet_id, min(duration) "
             "AS duration_min FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Maximum visit duration",
             "SELECT toilet_id, max(duration) "
             "AS duration_max FROM visits %(where)s "
             "GROUP BY toilet_id ORDER BY toilet_id;"),
            ("Visits by hour",
             "SELECT s.hour AS hour_of_day, count(v.hour) "
             "FROM generate_series(0, 23) s(hour) "
             "LEFT OUTER JOIN (SELECT recorded_at, "
             "EXTRACT('hour' from recorded_at) "
             "AS hour FROM visits %(where)s) v on s.hour = v.hour "
             "GROUP BY s.hour ORDER BY s.hour;"),
            ("Visits by day",
             "SELECT s.dow AS day_of_week, count(v.dow) "
             "FROM generate_series(0, 6) s(dow) "
             "LEFT OUTER JOIN (SELECT recorded_at, "
             "EXTRACT('dow' from recorded_at) "
             "AS dow FROM visits %(where)s) v on s.dow = v.dow "
             "GROUP BY s.dow ORDER BY s.dow;")
        ]
        results = yield [momoko.Op(self.db.execute,
                                   q % {"where": where,
                                        "and_where": and_where}) \
                         for _, q in queries]

        cursor = yield momoko.Op(self.db.execute, (
            "SELECT (s.period * 10) AS seconds, count(v.duration) "
            "FROM generate_series(0, 500) s(period) "
            "LEFT OUTER JOIN (SELECT EXTRACT(EPOCH from duration) "
            "AS duration FROM visits) v on s.period = FLOOR(v.duration / 10) "
            "GROUP BY s.period HAVING s.period <= 36 ORDER BY s.period;")
        )
        graph = "\n".join(ascii_graph.Pyasciigraph()
                          .graph("Frequency graph", cursor.fetchall()))

        self.render("stats.html", text=text, start=start, end=end,
                    tables=[(queries[i][0], prettytable.from_db_cursor(r)) \
                            for i, r in enumerate(results)],
                    frequency_graph=graph)


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
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        [(r"/login", GoogleLoginHandler),
         (r"/", MainHandler),
         (r"/stats", StatsHandler),
         (r"/api", APIHandler),
         (r"/hasfreesocket", HasFreeWebSocketHandler)],
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        hmac_secret=get_hmac_secret(),
        cookie_secret=get_cookie_secret(),
        login_url="/login"
    )
    app.db = momoko.Pool(
        dsn=" ".join(["%s=%s" % c for c in get_psql_credentials().iteritems()]),
        size=6
    )
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
