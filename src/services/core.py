import datetime
import time
from enum import IntFlag
from typing import List, Dict

import tornado.websocket
import ujson
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from utils.error import ExistError, NotExistError
from utils.timer import Timer
from .agenda.base import TextAgenda, AgendaBase
from .agenda.impromptu import ImpromptuAgenda
from .agenda.interpellation import InterpellationAgenda
from .agenda.proposal import ProposalAgenda
from .sysconfig import SysConfigService


class ClientType(IntFlag):
    MEMBER = 1,
    SECRETARIAT = 2,
    CHAIRPERSON = 4,
    PPT = 8,


class SittingCoreManageService(object):
    def __init__(self):
        SittingCoreManageService.inst = self
        self.active_sittings: Dict[int | SittingCore] = {}

    async def new_sittingcore(self, sitting_id: int):
        sitting_id = int(sitting_id)
        if sitting_id in self.active_sittings:
            return ExistError

        self.active_sittings[sitting_id] = SittingCore()
        self.active_sittings[sitting_id].sitting_id = sitting_id
        await self.active_sittings[sitting_id].core_prepare()
        return self.active_sittings[sitting_id]

    async def close_sittingcore(self, sitting_id: int):
        sitting_id = int(sitting_id)
        if sitting_id not in self.active_sittings:
            return NotExistError

        # FIXME: 這個沒寫好會把DB中的紀錄修改掉
        # await self.active_sittings[sitting_id].save_to_db()
        self.active_sittings.pop(sitting_id)

    def get_sittingcore(self, sitting_id: int):
        sitting_id = int(sitting_id)
        if sitting_id not in self.active_sittings:
            return NotExistError

        return self.active_sittings[sitting_id]


from handlers.core.checkin import CheckinStatus
from models.models import Member, MemberGroup, Sittings, AbsenceRecord, Sessions


class SittingCore(object):

    def __init__(self):

        self.participated_members: Dict = {}
        self.is_end = False
        self.is_start = False
        self.is_pause = False
        self.start_time = 0
        self.end_time = 0
        self.sitting_id = 0
        self.sitting_type = -1
        self.sittings = -1
        self.member_checkin_cnt = 0
        self.member_checkout_cnt = 0
        self.online_member_cnt = 0

        self.agenda: List = []
        self.impromptu = None
        self.interpellation = None
        self.proposal = None
        self.agenda_index = -1

        self.member_callback: Dict = {}
        self.secretariat_callback: Dict = {}
        self.chairperson_callback: Dict = {}
        self.ppt_callback: Dict = {}

        self.current_agenda = None

        # self.agenda = [
        #     {
        #         "type": "text",
        #         "name": "主席致詞"
        #     },
        #     {
        #         "type": "text",
        #         "name": "施政報告"
        #     },
        #     {
        #         "type": "proposal-discussion",
        #         "name": "提案討論",
        #         "list": [  # 在database中只存bill id
        #             {
        #                 "type": "bill-with-sub-bills",
        #                 "name": "議事系統專法一讀",
        #                 "list": [
        #                     {
        #                         "type": "bill-with-sub-bills",
        #                         "name": "第一條",
        #                         "list": [
        #                             {
        #                                 "type": "bill",
        #                                 "name": "第一條之一",
        #                                 "vote-result": {
        #                                     "同意": 10,
        #                                     "不同意": 1,
        #                                     "棄權": 0,
        #                                 }
        #                             },
        #                             {
        #                                 "type": "bill",
        #                                 "name": "第一條之二",
        #                                 "vote-result": {
        #                                     "同意": 10,
        #                                     "不同意": 1,
        #                                     "棄權": 0,
        #                                 }
        #                             },
        #                         ]
        #                     }
        #                 ]
        #             },
        #             {
        #                 "type": "bill-with-sub-bills",
        #                 "name": "議事系統專法一讀",
        #                 "list": [
        #                     {
        #                         "type": "bill-with-sub-bills",
        #                         "name": "第一條",
        #                         "list": [
        #                             {
        #                                 "type": "bill",
        #                                 "name": "第一條之一",
        #                                 "vote-result": {
        #                                     "同意": 10,
        #                                     "不同意": 1,
        #                                     "棄權": 0,
        #                                 }
        #                             },
        #                         ]
        #                     }
        #                 ]
        #             },
        #             {
        #                 "type": "bill-with-sub-bills",
        #                 "name": "議事系統專法二讀",
        #                 "list": [
        #                     {
        #                         "type": "bill",
        #                         "name": "第二條",
        #                         "vote-result": {}
        #                     }
        #                 ]
        #             }
        #         ]
        #     },
        #     {
        #         "type": "interpellations",
        #         "name": "會務詢答",
        #         "list": [
        #             {
        #                 "type": "interpellation",
        #                 "member": "105",
        #                 "officials": []
        #             },
        #         ]
        #     },
        #     {
        #         "type": "impromptu-motion",
        #         "name": "臨時動議",
        #         "list": [  # 在database中只存bill id
        #             {
        #                 "type": "impromptu-bill-with-sub-bills",
        #                 "member": "208",
        #                 "second-motion-count": 2,
        #                 "name": "議事系統專法二讀",
        #                 "list": [
        #                     {
        #                         "type": "bill-with-sub-bills",
        #                         "name": "第一條",
        #                         "list": [
        #                             {
        #                                 "type": "bill",
        #                                 "name": "第一條之一"
        #                             },
        #                         ]
        #                     }
        #                 ]
        #             },
        #             {
        #                 "type": "impromptu-bill",
        #                 "member": "208",
        #                 "second-motion-count": 3,
        #                 "name": "......for ",
        #                 "vote-result": {
        #
        #                 }
        #             }
        #         ]
        #     },
        # ]

        self.time_tags: List[Dict] = []

    async def core_prepare(self):
        self.config = await SysConfigService.inst.get_config()

        async with Sessions() as session:
            stmt = select(Sittings.sitting, Sittings.sitting_type, Sittings.start_time, Sittings.end_time).where(
                Sittings.id == self.sitting_id)
            res = (await session.execute(stmt)).fetchone()
            self.sittings = res[0]
            self.sitting_type = res[1]
            if res[2] is not None:
                self.start_time = res[2]
                self.is_start = True

            if res[3] is not None:
                self.end_time = res[3]
                self.is_end = True

        async with Sessions() as session:
            stmt = select(Member.id, Member.name,
                          Member.is_global_constituency, Member.official_name,
                          Member.class_seat_number, Member.group).where(
                Member.appointed_dates == self.config['appointed_dates']).where(
                Member.sessions == self.config['sessions']).order_by(Member.id)

            members = await session.execute(stmt)

            for row in members:
                member_id, name, is_global, official, number, group = row
                self.participated_members[member_id] = {
                    "name": name,
                    "is_global": is_global,
                    "official_name": official,
                    "number": number,
                    "checkin_status": int(CheckinStatus.NotEnter),
                    "group": group,
                    "session_id": None
                }

        async with Sessions() as session:
            stmt = select(AbsenceRecord).order_by(AbsenceRecord.member_id)

            res = await session.execute(stmt)
            for record in res:
                record = record[0]
                if record.entry_time is not None:
                    # NOTE: for dev
                    # self.participated_members[record.member_id]['checkin_status'] = int(CheckinStatus.Checkin)
                    pass

                if record.exit_time is not None:
                    # NOTE: for dev
                    # self.participated_members[record.member_id]['checkin_status'] = int(CheckinStatus.Checkout)
                    pass

        self.agenda_add_text("主席致詞")
        self.proposal = ProposalAgenda(self.participated_members, self.send_boardcast, self.add_timetag)
        await self.proposal.load_bills_from_db(self.sitting_id)
        self.agenda.append(self.proposal)

        self.interpellation = InterpellationAgenda(self.participated_members, self.send_boardcast, self.add_timetag)
        self.agenda.append(self.interpellation)

        self.impromptu = ImpromptuAgenda(self.send_boardcast, self.add_timetag, self.sitting_id)
        self.agenda.append(self.impromptu)
        self.agenda_add_text("散會")

    async def save_to_db(self):
        await self.impromptu.save_to_db()
        await self.proposal.save_to_db()

        agenda_json = []
        for agenda in self.agenda:
            if agenda.get_type() == "text":
                agenda_json.append({
                    "type": "text",
                    "text": agenda.get_name()
                })

            elif agenda.get_type() == "interpellations":
                agenda_json.append({
                    "type": "interpellation",
                    "list": agenda.get_interpellations()
                })

            elif agenda.get_type() == "impromptu-motion":
                l = []
                for pre_impromptu in agenda.get_pre_impromptus():
                    if pre_impromptu['is_append'] is False:
                        l.append(pre_impromptu)

                agenda_json.append({
                    "type": "impromptu-motion",
                    "pre-impromptu": l
                })

            elif agenda.get_type() == "proposal-discussion":
                agenda_json.append({
                    "type": "proposal-discussion",
                })
        agenda_json.append(self.time_tags)

        async with Sessions() as session:
            async with session.begin():
                start_time = datetime.datetime.fromtimestamp(self.start_time)
                end_time = datetime.datetime.fromtimestamp(self.end_time)
                stmt = update(Sittings).values(start_time=start_time, end_time=end_time,
                                               agenda=ujson.dumps(agenda_json))
                await session.execute(stmt)

    def is_sitting_start(self):
        return self.is_start

    def set_sitting_start(self):
        if self.is_start or self.is_end:  # 如果已經開會或結束
            return

        self.is_start = True
        self.start_time = time.time()
        self.time_tags.append({
            "type": "sitting-start",
            "time": 0
        })

    def is_sitting_end(self):
        return self.is_end

    async def set_sitting_end(self):
        if not self.is_start or self.is_end:
            return

        self.is_end = True
        self.end_time = time.time()
        self.add_timetag("sitting-end")

        await self.save_to_db()

    def set_sitting_pause(self, duration: int):
        self.add_timetag("sitting-pause")
        self.is_pause = True
        self.send_boardcast(ujson.dumps({
            "action": "notify",
            "data": {
                "type": "sitting-pause",
                "duration": duration
            }
        }), ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)

        def callback():
            self.is_pause = False
            self.add_timetag("sitting-pause-end")
            self.send_boardcast(ujson.dumps({
                "action": "notify",
                "data": {
                    "type": "sitting-pause-end"
                }
            }), ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)

        self.timer = Timer().set_duration(duration).set_timer_type("sitting-pause")
        self.timer.set_completed_callback(callback)
        self.timer.start()

    def register_callback_func(self, func, func_id, client_type: ClientType):
        if client_type == ClientType.MEMBER:
            self.member_callback[func_id] = func
        elif client_type == ClientType.SECRETARIAT:
            self.secretariat_callback[func_id] = func
        elif client_type == ClientType.CHAIRPERSON:
            self.chairperson_callback[func_id] = func
        elif client_type == ClientType.PPT:
            self.ppt_callback[func_id] = func

    def unregister_callback_func(self, func_id, client_type: ClientType):
        if client_type == ClientType.MEMBER:
            self.member_callback.pop(func_id)
        elif client_type == ClientType.SECRETARIAT:
            self.secretariat_callback.pop(func_id)
        elif client_type == ClientType.CHAIRPERSON:
            self.chairperson_callback.pop(func_id)

    def add_timetag(self, typ: str, data: Dict = None):
        if data is None:
            self.time_tags.append({
                "type": typ,
                "time": time.time() - self.start_time,
            })

        else:
            self.time_tags.append({
                "type": typ,
                "time": time.time() - self.start_time,
                "data": data
            })

    def send_boardcast(self, data: str, boardcast_type: ClientType):
        """
        這裡不會處理任何邏輯，只負責廣播而已
        :param data:
        :param boardcast_type:
        :return: None
        """

        boardcast_group = []
        if boardcast_type in ClientType.MEMBER:
            boardcast_group.append(self.member_callback)

        elif boardcast_type in ClientType.SECRETARIAT:
            boardcast_group.append(self.secretariat_callback)

        elif boardcast_type in ClientType.PPT:
            boardcast_group.append(self.ppt_callback)

        elif boardcast_type in (ClientType.MEMBER | ClientType.SECRETARIAT):
            boardcast_group.append(self.member_callback)
            boardcast_group.append(self.secretariat_callback)

        elif boardcast_type in (ClientType.MEMBER | ClientType.PPT):
            boardcast_group.append(self.member_callback)
            boardcast_group.append(self.ppt_callback)

        elif boardcast_type in (ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT):
            boardcast_group.append(self.member_callback)
            boardcast_group.append(self.secretariat_callback)
            boardcast_group.append(self.ppt_callback)

        func_removes = []
        for callback_list in boardcast_group:
            for func_id, func in callback_list.items():
                # TODO: 可以的話，不要使用try except
                try:
                    func(data)
                except tornado.websocket.WebSocketClosedError:
                    func_removes.append(func_id)

            for func_id in func_removes:
                callback_list.pop(func_id)

    def next_agenda(self):
        if not self.is_start or self.is_end:
            return True

        if self.is_pause:
            return True

        if self.agenda_index + 1 >= len(self.agenda):
            return True

        if self.current_agenda is None:
            self.agenda_index += 1
            self.current_agenda = self.agenda[self.agenda_index]
            self.add_timetag("next-agenda", {
                "type": self.current_agenda.get_type()
            })

        elif isinstance(self.current_agenda, TextAgenda):
            self.agenda_index += 1
            self.current_agenda = self.agenda[self.agenda_index]
            self.add_timetag("next-agenda", {
                "type": self.current_agenda.get_type()
            })

        elif isinstance(self.current_agenda, ProposalAgenda):
            if self.current_agenda.next_agenda():
                self.agenda_index += 1
                self.current_agenda = self.agenda[self.agenda_index]
                self.add_timetag("next-agenda", {
                    "type": self.current_agenda.get_type()
                })

        elif isinstance(self.current_agenda, InterpellationAgenda):
            if self.current_agenda.next_agenda():
                self.agenda_index += 1
                self.current_agenda = self.agenda[self.agenda_index]
                self.add_timetag("next-agenda", {
                    "type": self.current_agenda.get_type()
                })

        elif isinstance(self.current_agenda, ImpromptuAgenda):
            if self.current_agenda.next_agenda():
                self.agenda_index += 1
                self.current_agenda = self.agenda[self.agenda_index]
                self.add_timetag("next-agenda", {
                    "type": self.current_agenda.get_type()
                })

        return False

    def agenda_add_text(self, texts: str):
        text = TextAgenda()
        text.set_name(texts)
        self.agenda.append(text)

    def agenda_reorder(self, order: List[int]):
        if self.is_start:
            return

        # FIXME: int error
        new_order = []
        for i in order:
            new_order.append(self.agenda[int(i)])
        self.agenda = new_order
