"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

from models.models import MemberGroup
from ..base import RequestHandler, reqenv, require_permission


class ManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self):
        await self.render('manage/manage.html')

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self):
        pass
