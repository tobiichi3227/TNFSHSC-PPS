"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

from .base import RequestHandler, reqenv


class AboutHandler(RequestHandler):
    @reqenv
    async def get(self):
        await self.render('about.html')
