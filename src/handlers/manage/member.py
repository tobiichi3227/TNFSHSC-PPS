"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
import base64

import bcrypt
import tornado.web
from sqlalchemy import select, insert, update

from models.models import Sessions, Member, MemberGroup, MemberLockReason
from services.log import LogService
from services.sysconfig import SysConfigService
from utils.error import Success, WrongParamError, CanNotAccessError
from ..base import RequestHandler, reqenv, require_permission


class MemberManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self):
        if self.member['group'] <= int(MemberGroup.MEMBER):
            await self.error(CanNotAccessError)
            return

        try:
            page = self.get_argument('page')
        except tornado.web.HTTPError:
            page = None

        if page is None:
            async with Sessions() as session:
                stmt = select(Member.id.label("id"), Member.name.label("name"),
                              Member.class_seat_number.label("classseatnumber"),
                              Member.mail.label("mail"),
                              Member.is_global_constituency.label("is_global_constituency"),
                              Member.group.label("group")).order_by(Member.id)
                res = await session.execute(stmt)
            await self.render('manage/manage-member.html', members=res, member_group=MemberGroup.ChineseNameMap)
            return

        elif page == 'update':
            member_id = int(self.get_argument('member_id'))
            async with Sessions() as session:
                stmt = select(Member.name,
                              Member.class_seat_number,
                              Member.is_global_constituency,
                              Member.group, Member.official_name,
                              Member.lock).where(
                    Member.id == member_id)

                res = (await session.execute(stmt)).fetchone()
            await self.render('manage/manage-update-member.html', changed_member_id=member_id, member=res,
                              member_group=MemberGroup.ChineseNameMap)
            return

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self):
        if self.member['group'] <= int(MemberGroup.ASSOCIATION):
            await self.error(CanNotAccessError)
            return

        reqtype = self.get_argument('reqtype')

        if reqtype == 'register':
            register_type = self.get_argument('type')
            if register_type == 'single':
                name = self.get_argument('name')
                mail = self.get_argument('mail')
                group = self.get_argument('group')
                classseatnumber = self.get_argument('classseatnumber')
                is_global_constituency = self.get_argument('is_global_constituency')
                official_name = self.get_argument('official_name')

                config = await SysConfigService.inst.get_config()

                err, _ = await self.register_single_member(name, mail, mail, group, classseatnumber,
                                                           is_global_constituency, official_name,
                                                           config['appointed_dates'], config['sessions'])
                await self.error(err)
                return
            elif register_type == 'csv':
                pass

        elif reqtype == 'update':
            member_id = int(self.get_argument("member_id"))
            name = self.get_argument("name")
            class_seat_number = self.get_argument("class_seat_number")
            is_global_constituency = self.get_argument("is_global_constituency")
            official_name = self.get_argument("official_name")
            group = int(self.get_argument("group"))
            err, _ = await self.update_member(member_id, name, is_global_constituency, group, class_seat_number,
                                              official_name)

            if err != Success:
                await LogService.inst.add_log(self.member['id'],
                                              f"{self.member['name']} updated #{member_id} failure",
                                              "manage.member.update.failure")
                await self.error(err)
                return

            await LogService.inst.add_log(self.member['id'],
                                          f"{self.member['name']} updated #{member_id} successfully",
                                          "manage.member.update.success")
            await self.error(err)
            return

        elif reqtype == 'updatepassword':
            member_id = int(self.get_argument("member_id"))
            password = self.get_argument("password")

            await self.update_password(member_id, password)
            await LogService.inst.add_log(self.member['id'],
                                          f"{self.member['name']} updated #{member_id} password successfully",
                                          "manage.member.updatepassword.success")

            await self.error(Success)
            return

        elif reqtype == 'reset':
            member_id = self.get_optional_number_arg("member_id")
            reset = self.get_argument('reset')
            if reset == 'true':
                reset = True
            elif reset == 'false':
                reset = False
            else:
                await self.error(WrongParamError)
                return

            await self.set_password_reset(member_id, reset)
            await self.error(Success)
            return

        elif reqtype == 'lock':
            member_id = self.get_optional_number_arg("member_id")
            lock = self.get_argument('lock')
            if lock == 'true':
                lock = True
            elif lock == 'false':
                lock = False
            else:
                await self.error(WrongParamError)
                return

            await self.lock_member(member_id, lock)
            await self.error(Success)
            return

    async def register_single_member(self, name: str, mail: str, password: str, group: int, classseatnumber: str,
                                     is_global_constituency: str, official_name: str, appointed_dates: int,
                                     sessions: int):
        try:
            group = int(MemberGroup(int(group)))
        except ValueError:
            return WrongParamError, None

        try:
            classseatnumber = int(classseatnumber)
        except ValueError:
            return WrongParamError, None

        try:
            if is_global_constituency == "false":
                is_global_constituency = False
            elif is_global_constituency == "true":
                is_global_constituency = True
            else:
                raise ValueError
        except ValueError:
            return WrongParamError, None

        hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

        async with Sessions() as session:
            stmt = insert(Member).values(name=name, mail=mail, class_seat_number=classseatnumber,
                                         password=base64.b64encode(hash_pw).decode('utf-8'), group=group,
                                         is_global_constituency=is_global_constituency, official_name=official_name,
                                         appointed_dates=appointed_dates,
                                         sessions=sessions, permission_list=[],
                                         lock=int(MemberLockReason.LockByPasswordReset)).returning(
                Member.id, Member.name,
                Member.group)
            res = await session.execute(stmt)
            res = res.fetchone()

            await session.commit()  # 來發commit
            await session.close()

        await LogService.inst.add_log(self.member['id'],
                                      f"{self.member['name']} registered member<id: {res[0]} name: {res[1]} group: {res[2]}> successfully",
                                      'manage.member.register_single_member.success')

        return Success, None

    async def update_member(self, member_id: int, name: str, is_global_constituency: str, group: int,
                            class_seat_number: str, official_name: str):
        try:
            group = int(MemberGroup(group))
        except ValueError:
            return WrongParamError, None

        try:
            if is_global_constituency == "false":
                is_global_constituency = False
            elif is_global_constituency == "true":
                is_global_constituency = True
            else:
                raise ValueError
        except ValueError:
            return WrongParamError, None

        async with Sessions() as session:
            async with session.begin():
                stmt = update(Member).where(Member.id == member_id).values(name=name,
                                                                           group=group,
                                                                           class_seat_number=class_seat_number,
                                                                           is_global_constituency=is_global_constituency,
                                                                           official_name=official_name)
                await session.execute(stmt)
        return Success, None

    async def update_password(self, member_id: int, password: str):
        async with Sessions() as session:
            async with session.begin():
                hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

                stmt = update(Member).where(Member.id == member_id).values(
                    password=base64.b64encode(hash_pw).decode('utf-8'))
                await session.execute(stmt)
        return Success, None

    async def set_password_reset(self, member_id, reset: bool):
        await LogService.inst.add_log(self.member['id'],
                                      f"{self.member['name']} set member password reset flag {reset} successfully",
                                      'manage.member.set_password_reset.success')

        async with Sessions() as session:
            lock = MemberLockReason.UnLock
            if reset:
                lock = MemberLockReason.LockByPasswordReset

            async with session.begin():
                stmt = update(Member).where(Member.id == member_id).values(lock=int(lock))
                await session.execute(stmt)
        return Success, None

    async def lock_member(self, member_id, lock: bool):
        await LogService.inst.add_log(self.member['id'],
                                      f"{self.member['name']} set member lock flag {lock} successfully",
                                      'manage.member.set_lock.success')

        async with Sessions() as session:
            if lock:
                lock = MemberLockReason.LockByAdmin
            else:
                lock = MemberLockReason.UnLock

            async with session.begin():
                stmt = update(Member).where(Member.id == member_id).values(lock=int(lock))
                await session.execute(stmt)
        return Success, None
