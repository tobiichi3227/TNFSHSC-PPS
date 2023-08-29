"""
    所有會議管理
    包含增刪會議 會議歷史紀錄
    @author: tobiichi3227
    @day: 2023/7/3
"""

from sqlalchemy import select, insert

from services.core import SittingCoreManageService
from services.log import LogService
from utils.numeric import num2chinese_num
from utils.error import Success, WrongParamError, ExistError, NotExistError

from ..base import RequestHandler, reqenv, require_permission

from models.models import Sessions, Sittings, SittingType, MemberGroup

from services.sysconfig import SysConfigService


class SittingsManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
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
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
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

        elif reqtype == 'start':
            sitting_id = int(self.get_argument('sitting_id'))

            if (await SittingCoreManageService.inst.new_sittingcore(sitting_id)) != ExistError:
                await LogService.inst.add_log(self.member['id'],
                                              f"{self.member['name']} start a sitting<id: {sitting_id}> successfully",
                                              'manage.sittings.start')
                await self.error(Success)
                return

            await LogService.inst.add_log(self.member['id'],
                                          f"{self.member['name']} start a sitting<id: {sitting_id}> failure because of sitting existing",
                                          'manage.sittings.start.failure')
            await self.error(ExistError)
            return

        elif reqtype == 'close':
            sitting_id = int(self.get_argument('sitting_id'))

            if (await SittingCoreManageService.inst.close_sittingcore(sitting_id)) != NotExistError:
                await LogService.inst.add_log(self.member['id'],
                                              f"{self.member['name']} close a sitting<id: {sitting_id}> successfully",
                                              'manage.sittings.close')
                await self.error(Success)
                return

            await LogService.inst.add_log(self.member['id'],
                                          f"{self.member['name']} close a sitting<id: {sitting_id}> failure because of sitting not-existing",
                                          'manage.sittings.close.failure')
            await self.error(NotExistError)
            return
