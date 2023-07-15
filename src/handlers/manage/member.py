"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
import base64

import bcrypt
import tornado.web
from sqlalchemy import select, insert, update

from models.models import Sessions, Member, MemberGroup
from services.log import LogService
from services.sysconfig import SysConfigService
from util.error import Success, WrongParamError, CanNotAccessError
from ..base import RequestHandler, reqenv


class MemberManageHandler(RequestHandler):
    @reqenv
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
                stmt = select(Member.name.label("name"),
                              Member.class_seat_number.label("classseatnumber"),
                              Member.is_global_constituency.label("is_global_constituency"),
                              Member.group.label("group"), Member.official_name.label("official_name")).where(
                    Member.id == member_id)

                res = (await session.execute(stmt)).fetchone()
            await self.render('manage/manage-update-member.html', member_id=member_id, member=res,
                              member_group=MemberGroup.ChineseNameMap)
            return

    @reqenv
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

                err, _ = await self.register_single_member(name, mail, 'Init', group, classseatnumber,
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

    async def register_single_member(self, name: str, mail: str, password: str, group: int, classseatnumber: str,
                                     is_global_constituency: str, official_name: str, appointed_dates: int,
                                     sessions: int):
        try:
            group = int(MemberGroup(int(group)))
        except ValueError:
            print('128')
            return WrongParamError, None

        try:
            classseatnumber = int(classseatnumber)
        except ValueError:
            print("133")
            return WrongParamError, None

        try:
            is_global_constituency = bool(is_global_constituency)
        except ValueError:
            print("139")
            return WrongParamError, None

        hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

        async with Sessions() as session:
            stmt = insert(Member).values(name=name, mail=mail, class_seat_number=classseatnumber,
                                         password=base64.b64encode(hash_pw).decode('utf-8'), group=group,
                                         is_global_constituency=is_global_constituency, official_name=official_name,
                                         appointed_dates=appointed_dates,
                                         sessions=sessions, permission_list=[]).returning(Member.id, Member.name,
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
            is_global_constituency = bool(is_global_constituency)
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
