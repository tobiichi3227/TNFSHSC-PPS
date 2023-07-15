import datetime
from uuid import uuid4

from sqlalchemy import select, insert, update

from util.error import Success, UnknownError
from ..base import RequestHandler, reqenv

from models.models import Sessions, Member, AbsenceRecord

from services.log import LogService
from services.core import SittingCoreService


class CheckinManageHandler(RequestHandler):
    @reqenv
    async def get(self, sitting_id):
        async with Sessions() as session:
            member_session_id = SittingCoreService.inst.member_session_id
            stmt = select(Member.id.label("id"), Member.name.label("name"),
                          Member.class_seat_number.label("classseatnumber")
                          ).order_by(Member.id)
            members = await session.execute(stmt)
            stmt = select(AbsenceRecord)

        await self.render('core/checkin.html', sitting_id=sitting_id, members=members,
                          member_session_id=member_session_id)

    @reqenv
    async def post(self, sitting_id):
        sitting_id = int(sitting_id)
        member_session_id = SittingCoreService.inst.member_session_id
        reqtype = self.get_argument('reqtype')
        member_id = int(self.get_argument('member_id'))
        if reqtype == 'checkin':
            if member_session_id.get(member_id) is None:
                member_session_id[member_id] = str(uuid4().hex)

                async with Sessions() as session:
                    async with session.begin():
                        stmt = insert(AbsenceRecord).values(member_id=member_id, sitting_id=sitting_id).returning(
                            AbsenceRecord.id)

                        res = (await session.execute(stmt)).fetchone()
                        stmt = select(Member.name).where(AbsenceRecord.id == res[0]).join_from(AbsenceRecord, Member)
                        res = (await session.execute(stmt)).fetchone()

                await LogService.inst.add_log(self.member['id'], f"{res[0]} checkin", "sitting.checkin.checkin")

                await self.error(Success)
                return

            else:
                await self.error(UnknownError)
                return

        elif reqtype == 'checkout':
            print(member_session_id.get(member_id))
            if member_session_id.get(member_id) is not None and member_session_id.get(member_id) != "checkout":
                member_session_id[member_id] = 'checkout'
                async with Sessions() as session:
                    async with session.begin():
                        stmt = update(AbsenceRecord).values(exit_time=datetime.datetime.now()).where(
                            AbsenceRecord.member_id == member_id).where(
                            AbsenceRecord.sitting_id == sitting_id).returning(AbsenceRecord.id)
                        res = (await session.execute(stmt)).fetchone()
                        stmt = select(Member.name).where(AbsenceRecord.id == res[0]).join_from(AbsenceRecord, Member)
                        res = (await session.execute(stmt)).fetchone()

                await LogService.inst.add_log(self.member['id'], f"{res[0]} checkout", "sitting.checkin.checkout")

                await self.error(Success)
                return

            else:
                await self.error(UnknownError)
                return
