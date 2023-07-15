"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
import json
from urllib.parse import urlparse

import tornado

from handlers.base import RequestHandler, reqenv
from services.core import SittingCoreService, ClientType


class PPTPeviewHandler(RequestHandler):
    @reqenv
    async def get(self, sitting_id):
        await self.render('ppt/default.html')
        pass


class SittingWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        SittingCoreService.inst.register_callback_func(self.write_message, id(self), ClientType.PPT)

    async def action_handle(self, action: str, data):
        pass

    async def on_message(self, message):
        print(message)
        receive = json.loads(message)
        data = receive['data']
        await self.action_handle(receive['action'], data)

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        # print(parsed_origin.netloc.endswith(":3227"))
        return True

    def on_close(self) -> None:
        SittingCoreService.inst.unregister_callback_func(id(self), ClientType.PPT)
