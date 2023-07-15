"""
    所有會議管理
    包含增刪會議 會議歷史紀錄
    @author: tobiichi3227
    @day: 2023/7/3
"""

from sqlalchemy import select, insert

from services.log import LogService
from util.numeric import num2chinese_num
from util.error import Success, WrongParamError

from ..base import RequestHandler, reqenv

from models.models import Sessions, Sittings, SittingType

from services.sysconfig import SysConfigService


class SittingsManageHandler(RequestHandler):
    @reqenv
    async def get(self):
        async with Sessions() as session:
            async with session.begin():
                stmt = select(Sittings.id.label("id"), Sittings.sitting_type.label("type"),
                              Sittings.appointed_dates.label("appointed_dates"), Sittings.sessions.label("sessions"),
                              Sittings.sitting.label("sitting_time"), Sittings.location.label("location"),
                              Sittings.end_time.label("end_time")).order_by(Sittings.id)
                res = await session.execute(stmt)
                sittings = []
                for row in res:
                    sessions_cnt = "一" if row.sessions == 1 else "二"
                    name = f"第{num2chinese_num(row.appointed_dates)}屆第{sessions_cnt}會期"
                    if row.type == int(SittingType.Regular):
                        name += f"第{num2chinese_num(row.sitting_time)}次常會"
                    elif row.type == int(SittingType.Extraordinary):
                        name += f"第{num2chinese_num(row.sitting_time)}次臨時會"
                    elif row.type == int(SittingType.Parpare):
                        name += "預備會議"

                    if row.end_time is None:
                        end_time = '尚未開始'
                    else:
                        # TODO: 只顯示到日期
                        end_time = row.end_time

                    sittings.append({
                        'id': row.id,
                        'name': name,
                        'location': row.location,
                        'time': end_time,
                    })
        config = await SysConfigService.inst.get_config()
        await self.render('manage/manage-sittings.html', sittings=sittings, appointed_dates=config['appointed_dates'],
                          sessions=config['sessions'])

    @reqenv
    async def post(self):
        reqtype = self.get_argument('reqtype')
        if reqtype == 'create':
            try:
                sitting_times = int(self.get_argument('sitting_times'))

                sitting_type = int(self.get_argument('sitting_type'))
                sitting_type = int(SittingType(sitting_type))
            except ValueError:
                await self.error(WrongParamError)
                return

            location = self.get_argument('location')

            config = await SysConfigService.inst.get_config()

            async with Sessions() as session:
                async with session.begin():
                    stmt = insert(Sittings).values(sitting_type=sitting_type, location=location,
                                                   appointed_dates=config['appointed_dates'],
                                                   sessions=config['sessions'], sitting=sitting_times).returning(
                        Sittings.id)

                    res = (await session.execute(stmt)).fetchone()

            await LogService.inst.add_log(self.member['id'],
                                          f"{self.member['name']} create new sitting<id: {res[0]}> successfully",
                                          'manage.sittings.create.success')

            await self.error(Success)
