from models.models import MemberGroup
from ..base import RequestHandler, reqenv, require_permission


class SysConfigHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self):
        pass

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self):
        pass
