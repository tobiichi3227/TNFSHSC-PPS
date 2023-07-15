import json
from typing import Dict

from sqlalchemy import insert

from models.models import db, Log


class LogService(object):
    def __init__(self):
        LogService.inst = self

    async def add_log(self, operator_id: int, message: str, operate_type: str, params: Dict = None):
        if isinstance(params, dict):
            params = json.dumps(params, ensure_ascii=False)

        async with db.Sessions() as session:
            await session.execute(
                insert(Log).values(operator_id=operator_id, message=message, operate_type=operate_type,
                                   params=params))
            await session.commit()  # 來一發commit
            await session.close()
