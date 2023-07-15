"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

import base64

import bcrypt
from sqlalchemy import select

from .base import RequestHandler, reqenv

from models.models import Sessions, Member, MemberConst
from util.error import Success, WrongPasswordError, MemberNotFoundError
from services.log import LogService
from services.sysconfig import SysConfigService


class LoginHandler(RequestHandler):
    @reqenv
    async def get(self):
        config = (await SysConfigService.inst.get_config())
        await self.render('login.html', current_appointed_dates=config['appointed_dates'],
                          current_sessions=config['sessions'])
        return

    @reqenv
    async def post(self):
        reqtype = self.get_argument('reqtype')

        if reqtype == 'login':
            mail = self.get_argument('mail')
            pw = self.get_argument('pw')
            appointed_dates = int(self.get_argument('appointed_dates'))
            sessions = int(self.get_argument('sessions'))

            err, member_id = await self.login(mail, pw, appointed_dates, sessions)
            if err != Success:
                if err == MemberNotFoundError:
                    await LogService.inst.add_log(self.member['id'],
                                                  f"{mail} try to login but failed due to not found",
                                                  "login.failure.membernotfound")
                elif err == WrongPasswordError:
                    await LogService.inst.add_log(self.member['id'],
                                                  f"{mail} try to login but but failed due to wrong password",
                                                  "login.failure.wrongpassword")

                await self.error(err)
                return

            await LogService.inst.add_log(self.member['id'], f"#{member_id} login successfully", "login.success")
            self.set_secure_cookie('id', str(member_id), path='/pps', httponly=True)
            await self.error(err)

        elif reqtype == 'logout':
            await LogService.inst.add_log(self.member['id'], f"{self.member['name']}(#{self.member['id']}) logout",
                                          "logout")

            self.clear_cookie('id', path='/pps')
            await self.error(Success)
            return

    async def login(self, mail, pw, appointed_dates, sessions):
        async with Sessions() as session:
            async with session.begin():
                res = (await session.execute(
                    select(Member.id, Member.password).where(Member.mail == mail,
                                                             Member.appointed_dates == appointed_dates,
                                                             Member.sessions == sessions))).fetchone()
                if res is None:
                    return MemberNotFoundError, None

                member_id, hpw = res

        hpw = base64.b64decode(hpw.encode('utf-8'))
        if bcrypt.hashpw(pw.encode('utf-8'), hpw) == hpw:
            return Success, member_id

        return WrongPasswordError, None
