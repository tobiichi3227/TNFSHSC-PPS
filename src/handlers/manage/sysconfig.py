from ..base import RequestHandler, reqenv


class SysConfigHandler(RequestHandler):
    @reqenv
    async def get(self):
        pass

    @reqenv
    async def post(self):
        pass
