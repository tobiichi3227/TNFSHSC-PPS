from models.models import MemberGroup
from .base import RequestHandler, reqenv


class IndexHandler(RequestHandler):
    @reqenv
    async def get(self):
        manage = self.member['group'] >= int(MemberGroup.SECRETARIAT)
        await self.render('index.html', manage_permission=manage, name=self.member['name'])

    @reqenv
    async def post(self):
        pass
