"""
    操作紀錄查詢
    @author: tobiichi3227
    @day: 2023/7/3
"""
import datetime

import tornado
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from models.models import Sessions, Log
from util.error import Success
from ..base import RequestHandler, reqenv


class LogManageHandler(RequestHandler):
    def __init__(self, *args, **kwargs):
        self.tz = datetime.timezone(datetime.timedelta(hours=+8))

        super().__init__(*args, **kwargs)

    @reqenv
    async def get(self):
        try:
            offset = int(self.get_argument('offset'))
        except tornado.web.HTTPError or ValueError:
            offset = 0

        try:
            limit = int(self.get_argument('limit'))
        except tornado.web.HTTPError or ValueError:
            limit = 25
        _, logs = await self.list_log(offset, limit)
        _, logcnt = await self.get_logcnt()
        await self.render('manage/manage-log.html', logs=logs, offset=offset, limit=limit, logcnt=logcnt)

    @reqenv
    async def post(self):
        pass

    async def list_log(self, offset: int, limit: int, operator_id: int = None, operate_type: str = None):
        stmt = select(Log).order_by(Log.id).offset(offset).limit(limit).options(
            joinedload(Log.member, innerjoin=True))

        if operator_id is not None:
            stmt.where(Log.operator_id == operator_id)
        if operate_type is not None:
            stmt.where(Log.operate_type == operate_type)

        async with Sessions() as session:
            stmt.where()
            res = await session.execute(stmt)
            logs = []
            for row in res:
                logs.append({
                    "id": row[0].id,
                    "operator_name": row[0].member.name,
                    "message": row[0].message,
                    "operate_type": row[0].operate_type,
                    "timestamp": row[0].timestamp.astimezone(self.tz).isoformat(timespec="seconds"),
                })

            return Success, logs

    async def get_logcnt(self):
        async with Sessions() as session:
            stmt = select(func.count()).select_from(Log)
            count: int = (await session.execute(stmt)).scalar()

        return Success, count
