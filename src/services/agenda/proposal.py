from typing import Dict, List

from sqlalchemy import select, update, bindparam

from models.models import Sessions, Bill as BillMapper, BillSource
from .base import AgendaBase, IVote, ujson
from .bill import Bill, BillNode, tree_build, gen_tree_html
from .util import Vote
from utils.timer import Timer


class ProposalAgenda(AgendaBase, IVote):
    def get_agenda_4_frontend(self):
        return {
            "current_bill_id": self.get_curr_bill_id(),
            "is_voting": self._vote.is_start
        }

    def to_html_dict(self):
        pass

    async def save_to_db(self):
        l = []
        for bill_id, bill in self.bills_map.items():
            l.append({
                "id": bill_id,
                "data": bill.bill.get_vote_result()
            })

        async with Sessions() as session:
            async with session.begin():
                stmt = update(BillMapper).execution_options(synchronize_session=None)
                await session.execute(stmt, l)

    @classmethod
    def load_from_json(cls, str: str):
        pass

    def __init__(self, participated_members, send_boardcast_func, add_timatag_func):
        self._type = 'proposal-discussion'
        self._name = '提案討論'
        self._timer = Timer()
        self._timer.set_timer_type("proposal")
        self.participated_members = participated_members
        self.root_bills: List[int] = []
        self.bills_map: Dict[int | BillNode] = {}
        self._vote = Vote()
        self.first_call = True
        self.current_bill = None
        self.send_boardcast = send_boardcast_func
        self._add_timetag = add_timatag_func

        self._html_data: str = ''

        self._dfs_route: List[int] = []
        self.i = -1

    async def load_bills_from_db(self, sitting_id: int):
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

        self.bills_map, self.root_bills = tree_build(res)

        self._gen_html_data()
        self._prepare_dfs_route()

    def _prepare_dfs_route(self):
        def _dfs(p):
            self._dfs_route.append(p)

            for u in self.bills_map[p].child_indices:
                _dfs(u)

        for root in self.root_bills:
            _dfs(root)

    def _next_bill(self):
        pass

    def get_type(self):
        return self._type

    def get_name(self):
        return self._name

    def set_name(self, agenda_name: str):
        pass

    def _gen_html_data(self):
        self._html_data = gen_tree_html(self.bills_map, self.root_bills)

    def get_html_content(self):
        return self._html_data

    def to_json(self):
        pass

    def get_curr_bill_id(self):
        if self.current_bill is None:
            return None

        return self.current_bill.bill.bill_id

    def next_agenda(self):
        self._vote = Vote()
        self.i += 1
        if self.i >= len(self._dfs_route):
            return True

        self.current_bill = self.bills_map[self._dfs_route[self.i]]
        self._add_timetag("next-bill", {
            "name": self.current_bill.bill.name
        })

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

    def set_without_objection(self):
        if self.current_bill is None:
            return

        if self.current_bill.bill.get_vote_result() is not None:
            return

        self.current_bill.bill.set_vote_result("without-objection")
        self._vote.is_end = True
        self._vote.is_start = True

    def vote_init(self, options, duration: int, free: bool):
        if self._vote.is_start or self._vote.is_end:
            return

        if duration <= 0:
            return

        # self._vote = Vote() # invoke next agenda 時已經初始化了
        self._vote.set_free_vote(free)
        for option in options:
            self._vote.add_vote_option(option['option'])

        self._timer.set_duration(duration)

    def get_vote_name(self):
        return self.current_bill.bill.name

    def update_vote_count(self, member_id: int, vote_option_index: int):
        self._vote.update_vote_count(int(member_id), int(vote_option_index))

    def get_vote_options(self):
        return self._vote.get_vote_options()

    def vote_start(self):
        self._vote.is_start = True

        def callback():
            from ..core import ClientType
            self._add_timetag("vote-end", {
                "bill_id": self.current_bill.bill.bill_id
            })

            self._vote.is_end = True
            self.send_boardcast(ujson.dumps({
                "action": "notify",
                "data": {
                    "type": "vote-end",
                    "bill_id": self.current_bill.bill.bill_id,
                }
            }), ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)

            # save vote result
            self.current_bill.bill.set_vote_result(self._vote.get_vote_options())

        self._timer.set_completed_callback(callback)
        self._timer.start()
