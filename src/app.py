"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

import tornado.web

from urls import urls
from handlers.base import DefaultHandler

import config

app = tornado.web.Application(urls, autoescape='xhtml_escape', cookie_secret=config.SECRET_COOKIE,
                              default_handler_class=DefaultHandler,
                              debug=True, autoreload=True)  # for dev
