"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

import tornado.web
import tornado.template
from sqlalchemy import select

from models.models import Sessions, Member, MemberConst, MemberGroup, MemberLockReason
from services.sysconfig import SysConfigService
from utils.error import CanNotAccessError, Success, MemberLockedError


class RequestHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.tpldr = tornado.template.Loader('static/template', autoescape=None)
        self.config = None

    async def render(self, templ: str = None, error=None, **kwargs):
        if self.config is None:
            self.config = (await SysConfigService.inst.get_config())

        if self.member['id'] != MemberConst.MEMBERID_GUEST:
            kwargs['member_id'] = self.member['id']
            kwargs['current_appointed_dates'] = self.config['appointed_dates']
            kwargs['current_sessions'] = self.config['sessions']
        else:
            kwargs['member_id'] = ''

        if error is not None:
            data = self.tpldr.load(f"status/{error}.html").generate(**kwargs)

        elif templ is not None:
            data = self.tpldr.load(templ).generate(**kwargs)
        else:
            raise AssertionError('args none')

        await self.finish(data)
        return

    async def error(self, err):
        if err == Success:
            await self.finish(str(err))
            return

        await self.finish(str(err))
        return

    def get_optional_number_arg(self, arg_name: str):
        try:
            res = int(self.get_argument(arg_name))
        except tornado.web.HTTPError:
            res = None
        except ValueError:
            res = None

        return res


def reqenv(func):
    async def wrap(self, *args, **kwargs):
        member_id = self.get_secure_cookie('id')
        if member_id is None:
            self.member = {
                'id': 0,
                'name': '',
                'group': MemberGroup.GUEST,
                'permission_list': []
            }

        else:
            member_id = int(member_id)
            async with Sessions() as session:
                stmt = select(Member.id, Member.name, Member.group, Member.permission_list, Member.lock).where(
                    Member.id == member_id)
                res = (await session.execute(stmt)).fetchone()

                self.member = {
                    'id': res[0],
                    'name': res[1],
                    'group': res[2],
                    'permission_list': res[3],
                    'lock': res[4],
                }

        ret = await func(self, *args, **kwargs)
        return ret

    return wrap


def require_permission(group, use_error_code=False):
    def decorator(func):
        async def wrap(self, *args, **kwargs):
            # TODO: Account Lock Check
            match self.member['lock']:
                case MemberLockReason.UnLock:
                    pass
                case MemberLockReason.LockByAdmin:
                    if use_error_code:
                        await self.error(MemberLockedError)
                        return

                    await self.render(error=MemberLockedError)
                    return
                case MemberLockReason.LockByPasswordReset:
                    await self.render('reset-password.html')
                    return
                case _:
                    raise ValueError

            # TODO: Permission Check
            if isinstance(group, list):
                if self.member['group'] not in group:
                    if use_error_code:
                        await self.error(CanNotAccessError)
                        return

                    await self.render(error=CanNotAccessError)
                    return
            elif group is None:
                pass

            else:
                if self.member['group'] != group:
                    if use_error_code:
                        await self.error(CanNotAccessError)
                        return

                    await self.render(error=CanNotAccessError)
                    return

            ret = await func(self, *args, **kwargs)
            return ret

        return wrap

    return decorator


class DefaultHandler(RequestHandler):
    @reqenv
    async def get(self):
        await self.render('status/Enoext.html')
        return
