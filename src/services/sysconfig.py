"""
    @author: tobiichi3227
    @day: 2023/7/7
"""
from sqlalchemy import select, insert, update

from models.models import db, SystemConfig, Member, MemberGroup
from util.error import WrongParamError, Success


class SysConfigService(object):
    current_config = None

    def __init__(self):
        SysConfigService.inst = self

    async def Init(self):
        async with db.Sessions() as session:
            stmt = select(SystemConfig).where(SystemConfig.id == 1)
            res = (await session.execute(stmt)).fetchone()
            if res is None:
                stmt = insert(SystemConfig).values(id=1, current_appointed_dates=1, current_sessions=1)
                await session.execute(stmt)
                await session.commit()  # 還是commit
                stmt = select(SystemConfig).where(SystemConfig.id == 1)
                res = (await session.execute(stmt)).fetchone()

            self.current_config = res[0]

            stmt = select(Member.id).where(Member.id == 0)
            res = (await session.execute(stmt)).fetchone()
            if res is None:
                stmt = insert(Member).values(id=0, name='', mail='', password='', group=MemberGroup.GUEST,
                                             class_seat_number=0, is_global_constituency=False, appointed_dates=0,
                                             sessions=0, permission_list=[])
                await session.execute(stmt)
                await session.commit()  # 來發commit

    async def get_config(self):
        return {
            "appointed_dates": self.current_config.current_appointed_dates,
            "sessions": self.current_config.current_sessions,
        }

    async def next_sessions(self, appointed_dates: int, sessions: int):
        # TODO:
        if sessions > 2:
            return WrongParamError, None

        if appointed_dates < self.current_config.current_appointed_dates:
            return WrongParamError, None

        async with db.Sessions() as session:
            async with session.begin():
                stmt = update(SystemConfig).where(SystemConfig.id == 1).values(current_appointed_dates=appointed_dates,
                                                                               current_sessions=sessions)
                session.execute(stmt)

        return Success, None
