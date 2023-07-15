"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

import tornado.web
import tornado.template
from sqlalchemy import select

from models.models import Sessions, Member, MemberConst, MemberGroup
import util.error


class RequestHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.tpldr = tornado.template.Loader('static/template', autoescape=None)

    async def render(self, templ, **kwargs):
        if self.member['id'] != MemberConst.MEMBERID_GUEST:
            kwargs['member_id'] = self.member['id']
        else:
            kwargs['member_id'] = ''

        data = self.tpldr.load(templ).generate(**kwargs)
        await self.finish(data)

        return

    async def error(self, err):
        if err == util.error.Success:
            await self.finish(str(err))
            return

        await self.finish(str(err))
        return


def reqenv(func):
    async def wrap(self, *args, **kwargs):
        member_id = self.get_secure_cookie('id')
        if member_id == None:
            self.member = {
                'id': 0,
                'name': '',
                'group': MemberGroup.GUEST
            }
        else:
            member_id = int(member_id)
            async with Sessions() as session:
                res = (await session.execute(select(Member.id, Member.name,
                                                    Member.group, Member.permission_list).where(
                    Member.id == member_id))).fetchone()
                self.member = {
                    'id': res[0],
                    'name': res[1],
                    'group': res[2],
                    'permission_list': res[3],
                }

        ret = await func(self, *args, **kwargs)
        return ret

    return wrap


class DefaultHandler(RequestHandler):
    @reqenv
    async def get(self):
        await self.render('404.html')
        return
