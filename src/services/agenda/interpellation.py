from enum import IntEnum
from typing import List, Dict

import ujson

from models.models import MemberGroup
from utils.timer import Timer
from .base import AgendaBase


class InterpellationStatus(IntEnum):
    NotStarted = 0,
    Started = 1,
    Paused = 2,
    Done = 3,


# TODO: 官員必須簽到才能被質詢


class InterpellationAgenda(AgendaBase):
    def get_agenda_4_frontend(self):
        if self.i == -1:
            return {}

        return {"current_idx": self.i, "is_timing": self._timer.is_started}

    @classmethod
    def load_from_json(cls, str: str):
        pass

    def __init__(self, participated_members, sendboard_func, add_timetag_func):
        self._type = 'interpellations'
        self._name = '會務詢答'
        self._timer = Timer()
        self._timer.set_timer_type("interpellation")
        self._interpellation_pendings: Dict[int | Dict] = {}
        self._interpellation_order: List[int] = []
        self._participated_members = participated_members
        self._accept_register: bool = False
        self._send_boardcast = sendboard_func
        self._add_timetag = add_timetag_func

        self._html_data = None

        self.i = -1

    def get_type(self):
        return self._type

    def get_name(self):
        return self._name

    def set_name(self, agenda_name: str):
        pass

    def to_html_dict(self):
        return self._html_data

    def to_json(self):
        return ujson.dumps(self._html_data)

    def next_agenda(self):
        self.i += 1
        if self.i >= len(self._interpellation_pendings):
            return True

        if self.i > 0:
            if self._interpellation_pendings[self._interpellation_order[self.i - 1]]['status'] not in [
                InterpellationStatus.NotStarted, InterpellationStatus.Done]:
                self.i -= 1
                return False

        self._add_timetag("next-interpellation", {
            "name": self._participated_members[self._interpellation_order[self.i]]['name']
        })

        return False

    def get_timer_info(self):
        if self._timer is None:
            return {}

        return {
            "timer_type": self._timer.timer_type,
            "duration": self._timer.duration,
            "current_times": self._timer.run_times,
        }

    def _update(self):
        l = []
        for member_id in self._interpellation_order:
            l.append({
                "member_id": member_id
            })

        self._html_data = l

    def close_register(self):
        self._accept_register = False

    def open_register(self):
        self._accept_register = True

    def add_interpellation_member(self, member_id: int, officials: List[int]):
        if not self._accept_register:
            return

        member_id = int(member_id)
        if len(officials) == 0:
            return

        if member_id not in self._interpellation_pendings:
            self._interpellation_pendings[member_id] = {
                'status': int(InterpellationStatus.NotStarted),
                'officials': officials
            }

            self._interpellation_order.append(member_id)

        else:
            if self._interpellation_pendings[member_id]['status'] == int(InterpellationStatus.Done):
                return

            self._interpellation_pendings[member_id]['officials'] = officials

        self._update()

        def cmp(a):
            return int(self._participated_members[a]['number']), self._participated_members[a]['is_global']

        self._interpellation_order.sort(key=cmp)
        # TODO: 升冪排列 101 202 303 全校選區 議長 (coverage index)

    def get_officials(self):
        from handlers.core.checkin import CheckinStatus
        officials = []
        for member_id, member in self._participated_members.items():
            if member['group'] == int(MemberGroup.ASSOCIATION) and member['checkin_status'] == int(
                    CheckinStatus.Checkin):
                officials.append({
                    "official_name": member['official_name'],
                    "name": member['name'],
                    "id": member_id
                })

        return officials

    def get_interpellations(self):
        return self._interpellation_pendings

    def get_interpellations_order(self):
        return self._interpellation_order

    def member_start_interpellation(self, idx: int):
        if idx != self.i:
            return

        if self._interpellation_pendings[self._interpellation_order[idx]]['status'] != int(
                InterpellationStatus.NotStarted):
            return

        self._interpellation_pendings[self._interpellation_order[idx]]['status'] = int(InterpellationStatus.Started)
        self._timer.set_duration(480)

        def callback():
            from ..core import ClientType
            self._send_boardcast(ujson.dumps({
                "action": "notify",
                "data": {
                    "type": "interpellation-end",
                    "index": self.i,
                }
            }), ClientType.SECRETARIAT, ClientType.PPT)
            pass

        self._timer.set_completed_callback(callback)
        self._timer.start()

    def member_pause_interpellation(self, idx: int):
        if idx != self.i:
            return

        if self._interpellation_pendings[self._interpellation_order[idx]]['status'] != int(
                InterpellationStatus.Started):
            return

        self._interpellation_pendings[self._interpellation_order[idx]]['status'] = int(InterpellationStatus.Paused)
        self._timer.pause()

    def member_keep_interpellation(self, idx: int):
        if idx != self.i:
            return

        if self._interpellation_pendings[self._interpellation_order[idx]]['status'] != int(
                InterpellationStatus.Paused):
            return

        self._interpellation_pendings[self._interpellation_order[idx]]['status'] = int(InterpellationStatus.Started)
        self._timer.keep()

    def member_end_interpellation(self, idx: int):
        if idx != self.i:
            return

        if self._interpellation_pendings[self._interpellation_order[idx]]['status'] in [int(InterpellationStatus.Done),
                                                                                        int(InterpellationStatus.NotStarted)]:
            return

        self._interpellation_pendings[self._interpellation_order[idx]]['status'] = int(InterpellationStatus.Done)
        self._timer.stop()
