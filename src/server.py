"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
import asyncio
import time
import signal

import tornado.netutil
import tornado.web
import tornado.log
import tornado.options
import tornado.httpserver
import tornado.ioloop

import config
import models.models
import services.service


class Server:
    def __init__(self):

        self.port = config.PORT
        self.ioloop = tornado.ioloop.IOLoop.current()
        self.httpserver = None
        self.deadline = None

    def server_init(self):
        print("Server Init")

        # db connect
        # models.models.connect_db(models.models.db)
        asyncio.get_event_loop().run_until_complete(models.models.connect_db(models.models.db))
        # services init
        asyncio.get_event_loop().run_until_complete(services.service.services_init(services.service.Service))

        signal.signal(signal.SIGTERM, self.sig_handler)
        signal.signal(signal.SIGQUIT, self.sig_handler)
        signal.signal(signal.SIGINT, self.sig_handler)

        httpsock = tornado.netutil.bind_sockets(self.port)

        tornado.log.enable_pretty_logging()

        tornado.options.parse_command_line()

        from app import app
        self.httpserver = tornado.httpserver.HTTPServer(app, xheaders=True)
        self.httpserver.add_sockets(httpsock)

    def server_start(self):
        print("Server Start")

        self.ioloop.start()

    def server_shutdown(self):
        print("Stopping http server")

        if self.httpserver is not None:
            self.httpserver.stop()

        self.deadline = time.time() + 1
        self.stop_ioloop()

    def stop_ioloop(self):
        now = time.time()
        if now < self.deadline and (self.ioloop.time):
            self.ioloop.add_timeout(now + 1, self.stop_ioloop)
        else:
            print("Server shutdown!")
            self.ioloop.stop()

    def sig_handler(self, sig, frame):
        print(f"Caught signal: {sig}")
        tornado.ioloop.IOLoop.current().add_callback(self.server_shutdown)


if __name__ == "__main__":
    server = Server()
    server.server_init()
    server.server_start()
