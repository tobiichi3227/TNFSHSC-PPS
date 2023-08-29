"""
    @author: tobiichi3227
    @day: 2023/7/4
"""
from handlers.base import RequestHandler, reqenv, require_permission
from models.models import MemberGroup


class SittingManageHandler(RequestHandler):

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self, sitting_id):
        await self.render('core/sitting.html', sitting_id=sitting_id)

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self):
        pass
