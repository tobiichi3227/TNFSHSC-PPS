"""
    議案管理
    @author: tobiichi3227
    @day: 2023/7/3
"""

from sqlalchemy import select, insert

from util.error import Success
from ..base import RequestHandler, reqenv

from models.models import Sessions, Bill


class BillsManageHandler(RequestHandler):
    @reqenv
    async def get(self):
        async with Sessions() as session:
            async with session.begin():
                stmt = select(Bill.id, Bill.name).order_by(Bill.id)
                res = await session.execute(stmt)
        await self.render("manage/manage-bills.html", bills=res)

    @reqenv
    async def post(self):
        reqtype = self.get_argument('reqtype')

        if reqtype == "create":
            bill_name = self.get_argument('bill_name')
            err = await self.create_bill(bill_name)
            await self.error(err)

    async def create_bill(self, bill_name, sitting_id=None):
        async with Sessions() as session:
            async with session.begin():
                stmt = insert(Bill).values(name=bill_name)
                await session.execute(stmt)

        return Success
