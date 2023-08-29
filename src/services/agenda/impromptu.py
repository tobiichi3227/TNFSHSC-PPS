from collections import defaultdict
from typing import Dict, List, DefaultDict

from sqlalchemy import select, insert, bindparam
import ujson

from models.models import Sessions, Bill, BillSource
from .base import AgendaBase
from utils.timer import Timer
from .util import Vote


class ImpromptuAgenda(AgendaBase):
    def get_agenda_4_frontend(self):
        if self.i == -1:
            return {}

        return {
            "impromptu_index": self.i,
            "is_voting": self._vote.is_start
        }

    async def save_to_db(self):
        if len(self._impromptus) == 0:
            return

        l = []
        for bill in self._impromptus:
            l.append({
                "name": bill['bill_name'],
                "sitting_id": self._sitting_id,
                "data": {
                    "proposer_id": bill['member_id'],
                    "result": bill['result'],
                },
                "source": BillSource.Impromptu,
            })

        async with Sessions() as session:
            async with session.begin():
                stmt = insert(Bill).execution_options(synchronize_session=None)
                await session.execute(stmt, l)

    @classmethod
    def load_from_json(cls, str: str):
        pass

    def __init__(self, send_boardcast_func, add_timetag_func, sitting_id):
        self._type = 'impromptu-motion'
        self._name = '臨時動議'
        self._timer = Timer()
        self._timer.set_timer_type("impromptu")
        self._send_boardcast = send_boardcast_func
        self._add_timetag = add_timetag_func
        self._sitting_id = sitting_id

        self._pre_impromptus = []
        self._already_seconded_motion: DefaultDict[int | set] = defaultdict(set)
        self._is_start = False

        self._impromptus: List = []
        self.i = -1
        self.current_bill = None
        self._vote = Vote()

        self._html_data: Dict = {}

    def get_type(self):
        return self._type

    def get_name(self):
        return self._name

    def set_name(self, agenda_name: str):
        pass

    def to_html_dict(self):
        pass

    def to_json(self):
        pass

    def set_without_objection(self):
        if self.current_bill is None:
            return

        if self.current_bill['result'] is not None:
            return

        self.current_bill['result'] = "without-objection"
        self._vote.is_end = True
        self._vote.is_start = True

    def get_timer_info(self):
        if self._timer is None:
            return {}

        return {
            "timer_type": self._timer.timer_type,
            "duration": self._timer.duration,
            "current_times": self._timer.run_times,
        }

    def get_vote_info(self):
        return {
            'is_start': self._vote.is_start,
            'is_end': self._vote.is_end,
            'is_free': self._vote.is_free_vote,
        }

    def get_curr_bill_id(self):
        return self.current_bill['temp_id']

    def next_agenda(self):
        # FIXME: 這裡應該會有問題，資料不同步的問題？？？
        self.i += 1
        if self.i >= len(self._impromptus):
            return True

        self.current_bill = self._impromptus[self.i]
        self._add_timetag("next-bill", {
            "bill_name": self.current_bill['bill_name']
        })

    def get_pre_impromptus(self):
        return self._pre_impromptus

    def get_impromptus(self):
        return self._impromptus

    def start_impromptu(self):
        self._is_start = True

    def close_impromptu(self):
        self._is_start = False

    def add_impromptu(self, member_id: int, bill_name: str):
        if not self._is_start:
            return

        self._pre_impromptus.append({
            "temp_id": len(self._pre_impromptus),
            "member_id": member_id,
            "bill_name": bill_name,
            "count": 0,
            "result": None,
            "is_append": False,
        })

        # -member_id表示提案者 member_id表示附議者
        self._already_seconded_motion[int(len(self._pre_impromptus) - 1)].add(-member_id)

    def to_second_motion_impromptu(self, member_id: int, to_second_motion_index: int):
        if not self._is_start:
            return

        to_second_motion_index = int(to_second_motion_index)
        # 自己不能附議自己的提案
        if -member_id in self._already_seconded_motion[to_second_motion_index]:
            return

        # 不能重複附議
        elif member_id in self._already_seconded_motion[to_second_motion_index]:
            return

        # 競爭有可能會發生
        self._pre_impromptus[to_second_motion_index]['count'] += 1
        self._already_seconded_motion[to_second_motion_index].add(member_id)

        if self._pre_impromptus[to_second_motion_index]['count'] >= 1 and not \
                self._pre_impromptus[to_second_motion_index]['is_append']:
            self._impromptus.append(self._pre_impromptus[to_second_motion_index])
            self._pre_impromptus[to_second_motion_index]['is_append'] = True

    def vote_init(self, options, duration: int, free: bool):
        if self._vote.is_start or self._vote.is_end:
            return

        if duration <= 0:
            return

        self._vote = Vote()
        self._vote.set_free_vote(free)
        for option in options:
            self._vote.add_vote_option(option['option'])

        self._timer.set_duration(duration)

    def get_vote_name(self):
        return self.current_bill['bill_name']

    def update_vote_count(self, member_id: int, vote_option_index: int):
        self._vote.update_vote_count(int(member_id), int(vote_option_index))

    def get_vote_options(self):
        return self._vote.get_vote_options()

    def vote_start(self):
        self._vote.is_start = True

        def callback():
            from ..core import ClientType
            self._add_timetag("vote-end", {
                "name": self._impromptus[self.i]['name']
            })
            self._vote.is_end = True
            self._send_boardcast(ujson.dumps({
                "action": "notify",
                "data": {
                    "type": "vote-end",
                    "bill_id": self._impromptus[self.i]['temp_id'],
                }
            }), ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)

            # save vote result
            self._impromptus[self.i]['result'] = self._vote.get_vote_options()

        self._timer.set_completed_callback(callback)
        self._timer.start()
