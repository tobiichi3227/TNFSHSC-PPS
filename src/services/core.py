from typing import List, Dict
from enum import IntEnum, IntFlag
from collections import defaultdict
from datetime import datetime

import tornado.websocket


class ClientType(IntFlag):
    MEMBER = 1,
    SECRETARIAT = 2,
    CHAIRPERSON = 4,
    PPT = 8,


class AgendaType(IntEnum):
    TEXT = 0
    pass


class SittingCoreService(object):

    @staticmethod
    def st():
        pass

    def __init__(self):
        SittingCoreService.inst = self
        SittingCoreService.active_sitting = []

        self.member_session_id: Dict = {}
        self.is_end = False
        self.current_sitting_id = 0  # for multiple sitting
        self.member_callback: Dict = {}
        self.secretariat_callback: Dict = {}
        self.chairperson_callback: Dict = {}
        self.ppt_callback: Dict = {}

        self.agenda: List[Dict] = []
        self.agenda_times: List[Dict] = []
        self.interpellation_pending_queue: List[Dict] = []

        self.pre_impromptus = []
        self.already_seconded_motion = defaultdict(set)

        self.vote_options = []
        self.vote_multidict = defaultdict(set)
        self.already_voted = set()

    def is_sitting_end(self):
        return self.is_end

    def set_sitting_end(self, end: bool):
        self.is_end = end

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

    def new_agenda(self, agenda_type: AgendaType):
        if agenda_type == AgendaType.TEXT:
            pass
        pass

    def next_agenda(self):
        # send_boardcast(ppt_data, ClientType.PPT | ClientType.MEMBER)
        # self.agenda_times.append(datetime)
        pass

    def agenda_add_text(self, text: str):
        self.agenda.append({
            "type": "text",
            "name": text,
        })

    def agenda_add_proposal(self):
        self.agenda.append({
            "type": "proposal-discussion",
            "name": "提案討論",
            "list": []  # 在database中只存bill id
        })

    def agenda_add_interpellation(self):
        self.agenda.append({
            "type": "interpellations",
            "name": "會務詢答",
            "list": []
        })

    def agenda_add_impromptu(self):
        self.agenda.append({
            "type": "impromptu-motion",
            "name": "臨時動議",
            "list": []  # 在database中只存bill id
        })

    def add_interpellation_member(self, member_id: int, officials: List[int]):
        self.interpellation_pending_queue.append({
            "member_id": member_id,
            "officials": officials
        })
        # TODO: 升冪排列 101 202 303 全校選區 議長

    def get_impromptus(self):
        return self.pre_impromptus

    def add_impromptu(self, member_id: int, bill_name: str):
        self.pre_impromptus.append({
            "member_id": member_id,
            "bill_name": bill_name,
            "count": 0
        })

        # -member_id表示提案者 member_id表示附議者
        self.already_seconded_motion[int(len(self.pre_impromptus) - 1)].add(-member_id)

    def to_second_motion_impromptu(self, member_id: int, to_second_motion_index: int):
        to_second_motion_index = int(to_second_motion_index)
        # 自己不能附議自己的提案
        if -member_id in self.already_seconded_motion[to_second_motion_index]:
            return

        # 不能重複附議
        elif member_id in self.already_seconded_motion[to_second_motion_index]:
            return

        # 競爭有可能會發生
        self.pre_impromptus[to_second_motion_index]['count'] += 1
        self.already_seconded_motion[to_second_motion_index].add(member_id)

    def vote_init(self):
        self.vote_options.clear()
        self.vote_multidict.clear()
        self.already_voted.clear()

    def add_vote_option(self, vote_name: str):
        self.vote_options.append({
            "vote_name": vote_name,
            "count": 0
        })

    def add_vote_count(self, member_id: int, vote_option_index: int):
        member_id = int(member_id)
        vote_option_index = int(vote_option_index)
        if member_id in self.already_voted or member_id in self.vote_multidict[vote_option_index]:
            return

        self.already_voted.add(member_id)
        self.vote_multidict[vote_option_index].add(member_id)
        self.vote_options[vote_option_index]['count'] += 1


def bill_html_gen(bill: Dict, run_cnt: int, loop_run_cnt: int) -> str:
    html = ''
    button_html = f"""
    <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{loop_run_cnt}-1\">
        無異議通過
    </button>
    <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{loop_run_cnt}-2\">
        投票
    </button>
    <button class=\"btn btn-secondary px-sm-1 py-sm-0\" id=\"{loop_run_cnt}-3\">
        取消
    </button>
    """
    if bill.get("list") is not None:
        if run_cnt == 0:
            html += f"<span>{bill['name']}</span>"
        else:
            html += f"\n<br>\n" \
                    f"<span style=\"padding-left: 10%;\">{bill['name']}</span>"

        for i, bill in enumerate(bill['list']):
            html += bill_html_gen(bill, run_cnt + 1, i)
        return html
    else:
        html += f"\n<br>\n" \
                f"<span style=\"padding-left: 20%;\">{bill['name']} {button_html}</span>"
        return html
