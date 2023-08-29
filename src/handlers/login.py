"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

import base64

import bcrypt
import tornado.web
from sqlalchemy import select, update

from .base import RequestHandler, reqenv

from models.models import Sessions, Member, MemberLockReason
from utils.error import Success, WrongPasswordError, MemberNotFoundError, MemberLockedError
from services.log import LogService
from services.sysconfig import SysConfigService


class LoginHandler(RequestHandler):
    @reqenv
    async def get(self):
        config = (await SysConfigService.inst.get_config())
        try:
            page = self.get_argument('page')

        except tornado.web.HTTPError:
            page = None
        if page is None:
            await self.render('login.html', current_appointed_dates=config['appointed_dates'],
                              current_sessions=config['sessions'])

        else:
            if page == "reset":
                await self.render('reset-password.html', current_appointed_dates=config['appointed_dates'],
                                  current_sessions=config['sessions'])

    @reqenv
    async def post(self):
        reqtype = self.get_argument('reqtype')

        if reqtype == 'login':
            mail = self.get_argument('mail')
            pw = self.get_argument('pw')
            appointed_dates = int(self.get_argument('appointed_dates'))
            sessions = int(self.get_argument('sessions'))

            err, member_id, lock = await self.login(mail, pw, appointed_dates, sessions)
            if err != Success:
                if err == MemberNotFoundError:
                    await LogService.inst.add_log(self.member['id'],
                                                  f"{mail} try to login but failed due to not found",
                                                  "login.failure.membernotfound")
                elif err == WrongPasswordError:
                    await LogService.inst.add_log(self.member['id'],
                                                  f"{mail} try to login but failed due to wrong password",
                                                  "login.failure.wrongpassword")
                elif err == MemberLockedError:
                    await LogService.inst.add_log(self.member['id'],
                                                  f"{mail} try to login but failed due to account locked",
                                                  "login.failure.locked")

                await self.error(err)
                return

            await LogService.inst.add_log(self.member['id'], f"#{member_id} login successfully", "login.success")
            self.set_secure_cookie('id', str(member_id), path='/pps', httponly=True)

            if lock == int(MemberLockReason.LockByPasswordReset):
                await self.finish("reset_password")

            elif lock == int(MemberLockReason.UnLock):
                await self.error(Success)

        elif reqtype == 'logout':
            await LogService.inst.add_log(self.member['id'], f"{self.member['name']}(#{self.member['id']}) logout",
                                          "logout")

            self.clear_cookie('id', path='/pps')
            await self.error(Success)
            return

        elif reqtype == 'reset':
            if self.member['id'] == 0:
                mail = self.get_argument('mail')
                appointed_dates = int(self.get_argument('appointed_dates'))
                sessions = int(self.get_argument('sessions'))
            else:
                mail = None

            password = self.get_argument('password')

            flag = False
            if len(password) < 5:
                flag = True

            if not (any(char.islower() for char in password) or any(char.isupper() for char in password)):
                flag = True

            if not any(char.isdigit() for char in password):
                flag = True

            if mail is not None:
                m = mail
            else:
                m = self.member['id']

            if flag:
                await LogService.inst.add_log(m,
                                              f"{m} try to reset password but failed due to weak password",
                                              "resetpassword.failure.weakpw")
                await self.finish("Eweakpw")
                return

            async with Sessions() as session:
                async with session.begin():
                    stmt = select(Member.password, Member.id)
                    if mail is None:
                        stmt = stmt.where(Member.id == int(self.member['id']))
                    else:
                        stmt = stmt.where(Member.mail == mail)
                        stmt = stmt.where(Member.appointed_dates == appointed_dates)
                        stmt = stmt.where(Member.sessions == sessions)

                    res = (await session.execute(stmt)).fetchone()
                    if res is None:
                        await self.error(MemberNotFoundError)
                        return

                    hpw, member_id = res
                    hpw = base64.b64decode(hpw.encode('utf-8'))
                    if bcrypt.hashpw(password.encode('utf-8'), hpw) == hpw:
                        await LogService.inst.add_log(m,
                                                      f"{m} try to reset passowrd but failed due to the same password",
                                                      "resetpassword.failure.oldpw")
                        await self.finish("Eoldpw")
                        return

                    hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

                    stmt = update(Member).where(Member.id == member_id).values(
                        password=base64.b64encode(hash_pw).decode('utf-8'), lock=MemberLockReason.UnLock)
                    await session.execute(stmt)

            await LogService.inst.add_log(m,
                                          f"{m} reset password successfully",
                                          "resetpassword.success")
            await self.error(Success)

    async def login(self, mail, pw, appointed_dates, sessions):
        async with Sessions() as session:
            async with session.begin():
                res = (await session.execute(
                    select(Member.id, Member.password, Member.lock).where(Member.mail == mail).where(
                        Member.appointed_dates == appointed_dates).where(Member.sessions == sessions))).fetchone()
                if res is None:
                    return MemberNotFoundError, None, None

                member_id, hpw, lock = res

        if lock == int(MemberLockReason.LockByAdmin):
            return MemberLockedError, member_id, MemberLockReason.LockByAdmin

        hpw = base64.b64decode(hpw.encode('utf-8'))
        if bcrypt.hashpw(pw.encode('utf-8'), hpw) == hpw:
            if lock == int(MemberLockReason.LockByPasswordReset):
                return Success, member_id, MemberLockReason.LockByPasswordReset

            return Success, member_id, MemberLockReason.UnLock

        return WrongPasswordError, None, None
