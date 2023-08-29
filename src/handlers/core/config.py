import datetime
import json
import uuid
import csv
from collections import defaultdict

import ujson
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from services.agenda.bill import tree_build
from ..base import RequestHandler, reqenv, require_permission
from models.models import Sessions, Member, AbsenceRecord, MemberGroup, Bill as BillMapper, BillSource, Sittings
from utils.error import Success, UnknownError, NotExistError, WrongParamError, MemberNotFoundError
from services.log import LogService
from services.core import SittingCoreManageService


class SittingConfigManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self, sitting_id):
        sitting_id = int(sitting_id)
        core = SittingCoreManageService.inst.get_sittingcore(sitting_id)
        if core == NotExistError:
            await self.render(error=NotExistError)
            return

        async with Sessions() as session:
            stmt = select(Sittings.location, Sittings.chairperson_id, Sittings.secretary_id).where(
                Sittings.id == sitting_id)
            res = (await session.execute(stmt)).fetchone()
        await self.render('core/config.html', sitting_id=sitting_id, res=res)

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self, sitting_id):
        sitting_id = int(sitting_id)
        core = SittingCoreManageService.inst.get_sittingcore(sitting_id)
        if core == NotExistError:
            await self.error(NotExistError)
            return

        # TODO: 地點 議長 秘書長 設定

        reqtype = self.get_argument("reqtype")

        if reqtype == "config":
            location = self.get_argument('location')
            chairperson_id = self.get_optional_number_arg('chairperson')
            secretary_id = self.get_optional_number_arg('secretary')
            if chairperson_id is None or secretary_id is None:
                await self.error(WrongParamError)
                return

            if chairperson_id not in core.participated_members or secretary_id not in core.participated_members:
                await self.error(MemberNotFoundError)
                return

            if len(location.strip()) == 0:
                await self.error(WrongParamError)
                return

            async with Sessions() as session:
                async with session.begin():
                    stmt = update(Sittings).values(chairperson_id=chairperson_id, secretary_id=secretary_id,
                                                   location=location)
                    await session.execute(stmt)

        elif reqtype == "csv":
            """
            id class-seat-number name entry-time exit-time total-time 
            if not exist, the 倒數三個為-1
            
            更好的作法是在每次簽到時對csv寫入，在會議結束時把沒簽到的人一次寫入到csv中即可
            """

            tz = datetime.timezone(datetime.timedelta(hours=+8))
            csv_id = uuid.uuid4().hex
            with open(f'./download/{csv_id}.csv', mode='w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["ID", "班級座號", "姓名", "簽到時間", "簽退時間"])
                async with Sessions() as session:
                    stmt = select(AbsenceRecord).order_by(AbsenceRecord.member_id).options(
                        joinedload(AbsenceRecord.member, innerjoin=True))

                    res = await session.execute(stmt)
                    vis = defaultdict(bool)
                    for record in res:
                        record = record[0]
                        vis[record.member.id] = True
                        writer.writerow([
                            record.member.id, record.member.name, record.member.class_seat_number,
                            record.entry_time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                            record.exit_time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
                        ])  # , (record.exit_time - record.entry_time)])

                    # TODO: 記得沒有出席的議員也要算
                    for member_id, member in core.participated_members.items():
                        if not vis[member_id]:
                            vis[member_id] = True

                            writer.writerow([member_id, member['name'], member['number'], -1, -1])  # -1])
            await self.finish(f"{csv_id}")
            return

        elif reqtype == "json":

            sitting_id = int(sitting_id)
            async with Sessions() as session:
                async with session.begin():
                    stmt = select(BillMapper.id.label("id"), BillMapper.root_id.label("root_id"),
                                  BillMapper.parent_id.label("parent_id"), BillMapper.name.label("name"),
                                  BillMapper.desc.label("desc"), BillMapper.data.label("data")).where(
                        BillMapper.sitting_id == sitting_id).where(BillMapper.delete_status == False).where(
                        BillMapper.source == BillSource.Default).order_by(
                        BillMapper.root_id)
                    res = await session.execute(stmt)

            bills_map, root_bills = tree_build(res)

            async with Sessions() as session:
                async with session.begin():
                    stmt = select(BillMapper.id.label("id"), BillMapper.root_id.label("root_id"),
                                  BillMapper.parent_id.label("parent_id"), BillMapper.name.label("name"),
                                  BillMapper.desc.label("desc"), BillMapper.data.label("data")).where(
                        BillMapper.sitting_id == sitting_id).where(BillMapper.delete_status == False).where(
                        BillMapper.source == BillSource.Impromptu).order_by(
                        BillMapper.root_id)
                    res = await session.execute(stmt)
            impromptu_bills = res

            async with Sessions() as session:
                stmt = select(Sittings).where(Sittings.id == sitting_id)
                res = await session.execute(stmt)
            sitting: Sittings = res.fetchone()[0]

            agendas = ujson.loads(sitting.agenda)
            output = []
            output.append({
                'appointed_dates': sitting.appointed_dates,
                'sessions': sitting.sessions,
                'sittings': sitting.sitting,
                'sitting_type': sitting.sitting_type,
                'start_time': sitting.start_time,
                'end_time': sitting.end_time,
                'location': sitting.location,
                'chairperson': core.participated_members[sitting.chairperson_id]['name'],
                'secretary': core.participated_members[sitting.secretary_id]['name'],
            })
            for agenda in agendas:
                if isinstance(agenda, list):
                    continue

                if agenda['type'] == "impromptu-motion":
                    l = []
                    for impromptu in impromptu_bills:
                        l.append({
                            "name": impromptu[3],
                            "desc": "",
                            "data": impromptu[5],
                        })
                    agenda['impromptu'] = l

                elif agenda['type'] == 'proposal-discussion':
                    m = {}
                    for bill_id, bill in bills_map.items():
                        m[bill_id] = {
                            "name": bill.bill.get_name(),
                            "desc": bill.bill.desc,
                            "data": bill.bill.data,
                        }
                    agenda['bills'] = m

            output.append(agendas)

            class _encoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime.datetime):
                        return obj.isoformat()

                    else:
                        return json.JSONEncoder.default(self, obj)

            json_id = uuid.uuid4().hex
            with open(f"./download/{json_id}.json", mode='w', newline='') as jsonfile:

                jsonfile.write(json.dumps(output, cls=_encoder))

            await self.finish(json_id)
