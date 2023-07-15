"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

from ..base import RequestHandler, reqenv


class ManageHandler(RequestHandler):
    @reqenv
    async def get(self):
        await self.render('manage/manage.html')

    @reqenv
    async def post(self):
        pass
