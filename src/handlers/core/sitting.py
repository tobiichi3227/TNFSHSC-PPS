"""
    @author: tobiichi3227
    @day: 2023/7/4
"""
from handlers.base import RequestHandler, reqenv


class SittingManageHandler(RequestHandler):

    @reqenv
    async def get(self, sitting_id):
        await self.render('core/sitting.html', sitting_id=sitting_id)

    @reqenv
    async def post(self):
        pass
