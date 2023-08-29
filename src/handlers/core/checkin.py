import datetime
import enum
from uuid import uuid4

from sqlalchemy import select, insert, update

from utils.error import Success, UnknownError, NotExistError
from ..base import RequestHandler, reqenv, require_permission

from models.models import Sessions, Member, AbsenceRecord, MemberGroup

from services.log import LogService
from services.core import SittingCoreManageService


class CheckinStatus(enum.IntEnum):
    NotEnter = 0,
    Checkin = 1,
    Checkout = 2,


class CheckinManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self, sitting_id):
        core = SittingCoreManageService.inst.get_sittingcore(int(sitting_id))
        if core == NotExistError:
            await self.render(error=NotExistError)
            return

        await self.render('core/checkin.html', sitting_id=sitting_id, members=core.participated_members,
                          checkin_cnt=core.member_checkin_cnt, checkout_cnt=core.member_checkout_cnt)

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self, sitting_id):
        sitting_id = int(sitting_id)
        core = SittingCoreManageService.inst.get_sittingcore(sitting_id)
        if core == NotExistError:
            await self.error(NotExistError)
            return

        members = core.participated_members

        reqtype = self.get_argument('reqtype')
        member_id = int(self.get_argument('member_id'))

        if reqtype == 'checkin':
            if (member := members.get(member_id)) is not None:
                if member['checkin_status'] == CheckinStatus.NotEnter:
                    member['checkin_status'] = CheckinStatus.Checkin
                    member['session_id'] = str(uuid4().hex)

                    async with Sessions() as session:
                        async with session.begin():
                            stmt = insert(AbsenceRecord).values(member_id=member_id, sitting_id=sitting_id)

                            await session.execute(stmt)

                    core.member_checkin_cnt += 1
                    await self.error(Success)
                    return

        elif reqtype == 'checkout':
            if (member := members.get(member_id)) is not None:
                if member['checkin_status'] == CheckinStatus.Checkin:
                    member['checkin_status'] = CheckinStatus.Checkout
                    member['session_id'] = None

                    async with Sessions() as session:
                        async with session.begin():
                            stmt = update(AbsenceRecord).values(exit_time=datetime.datetime.now()).where(
                                AbsenceRecord.member_id == member_id).where(
                                AbsenceRecord.sitting_id == sitting_id).returning(AbsenceRecord.id)
                            await session.execute(stmt)

                    core.member_checkout_cnt += 1
                    await self.error(Success)
                    return

        else:
            await self.error(UnknownError)
            return
