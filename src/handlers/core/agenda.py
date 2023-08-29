from urllib.parse import urlparse

import tornado.websocket
import ujson

from models.models import MemberGroup
from services.agenda.impromptu import ImpromptuAgenda
from services.agenda.interpellation import InterpellationAgenda
from services.agenda.proposal import ProposalAgenda
from services.core import SittingCoreManageService, SittingCore, ClientType
from utils.error import NotExistError, Success, WrongParamError
from ..base import RequestHandler, reqenv, require_permission


class AgendaManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self, sitting_id):
        if (core := SittingCoreManageService.inst.get_sittingcore(int(sitting_id))) is NotExistError:
            await self.render(error=NotExistError)
            return

        await self.render('core/agenda.html', sitting_id=sitting_id, agenda=core.agenda,
                          proposal_html=core.proposal.get_html_content(), sitting_pause=core.is_pause,
                          is_start=core.is_start, is_end=core.is_end)

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self, sitting_id):
        if (core := SittingCoreManageService.inst.get_sittingcore(int(sitting_id))) is NotExistError:
            await self.error(NotExistError)
            return

        reqtype = self.get_argument("reqtype")
        if reqtype == "new-agenda-text":
            text = self.get_argument("text")
            core.agenda_add_text(text)
            await self.error(Success)

        elif reqtype == "sitting-start":
            core.set_sitting_start()

        elif reqtype == "sitting-stop":
            await core.set_sitting_end()

        elif reqtype == "sitting-pause":
            duration = self.get_optional_number_arg("duration")
            if duration is None or duration <= 0:
                await self.error(WrongParamError)

            core.set_sitting_pause(duration * 60)


class AgendaWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sitting_id = None

    async def action_handle(self, action: str, data):
        core: SittingCore = SittingCoreManageService.inst.get_sittingcore(self.sitting_id)

        if action == "update":
            data_type = data['type']

            if data_type == "start-vote":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion']:
                    return

                bill_id = int(data['bill_id'])
                options = data['options']
                duration = int(data['duration'])
                free = data['free']

                if bill_id != core.current_agenda.get_curr_bill_id():
                    return

                core.current_agenda.vote_init(options, duration, free)
                core.current_agenda.vote_start()

                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "vote-start",
                        "is_free": free,
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data),
                                    ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)
                core.add_timetag(data_type)

            elif data_type == "without-objection":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion']:
                    return

                core.current_agenda.set_without_objection()
                core.add_timetag(data_type)

            elif data_type == "next-agenda":
                is_end = core.next_agenda()
                if is_end:
                    return

                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "next-agenda"
                    }
                }

                core.send_boardcast(ujson.dumps(boardcast_data),
                                    ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)

            elif data_type == "reorder-agenda":
                core.agenda_reorder(data['orders'])

                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "agenda-reorder"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.PPT)

            elif data_type == "interpellation-start":
                if core.current_agenda is None or not core.current_agenda.get_type() == "interpellations":
                    return

                idx = int(data['idx'])
                core.current_agenda.member_start_interpellation(idx)
                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "interpellation-start"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.SECRETARIAT | ClientType.PPT)
                core.add_timetag(data_type)

            elif data_type == "interpellation-pause":
                if core.current_agenda is None or not core.current_agenda.get_type() == "interpellations":
                    return

                idx = int(data['idx'])
                core.current_agenda.member_pause_interpellation(idx)
                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "interpellation-pause"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.SECRETARIAT | ClientType.PPT)
                core.add_timetag(data_type)

            elif data_type == "interpellation-keep":
                if core.current_agenda is None or not core.current_agenda.get_type() == "interpellations":
                    return

                idx = int(data['idx'])
                core.current_agenda.member_keep_interpellation(idx)
                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "interpellation-keep"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.SECRETARIAT | ClientType.PPT)
                core.add_timetag(data_type)

            elif data_type == "interpellation-stop":
                if core.current_agenda is None or not core.current_agenda.get_type() == "interpellations":
                    return

                idx = int(data['idx'])
                core.current_agenda.member_end_interpellation(idx)
                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "interpellation-stop"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.SECRETARIAT | ClientType.PPT)
                core.add_timetag(data_type)

            elif data_type == "interpellation-start-submit":
                core.interpellation.open_register()

                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "interpellation-start-submit"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.MEMBER)

            elif data_type == "interpellation-close-submit":
                core.interpellation.close_register()

                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "interpellation-close-submit"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.MEMBER)

            elif data_type == "impromptu-start-submit":
                core.impromptu.start_impromptu()

                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "impromptu-start-submit"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.MEMBER)

            elif data_type == "impromptu-close-submit":
                core.impromptu.close_impromptu()

                boardcast_data = {
                    "action": "notify",
                    "data": {
                        "type": "impromptu-close-submit"
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data), ClientType.MEMBER)

        elif action == "query":
            data_type = data['type']
            if data_type == "interpellations":
                l = []
                for member_id, interpellation in core.interpellation.get_interpellations().items():
                    m = []
                    for official_id in interpellation['officials']:
                        m.append({
                            "name": core.participated_members[official_id]['name'],
                            "official_name": core.participated_members[official_id]['official_name']
                        })

                    l.append({
                        "officials": m,
                        "status": interpellation['status'],
                        "member_name": core.participated_members[member_id]['name']
                    })

                await self.write_message(ujson.dumps({
                    "action": "update",
                    "data": {
                        "type": "update-interpellation",
                        "list": l,
                    }
                }))

            elif data_type == "pre-impromptu":
                await self.write_message(ujson.dumps({
                    "action": "update",
                    "data": {
                        "type": "new-impromptu-motion",
                        "list": [{"count": i['count'], "bill_name": i['bill_name'],
                                  "name": core.participated_members[i['member_id']]['name']} for i in
                                 core.impromptu.get_pre_impromptus()],
                    }
                }))

            elif data_type == "impromptu":
                l = []
                for i in core.impromptu.get_impromptus():
                    l.append({
                        "name": i['bill_name'],
                        "id": i['temp_id'],
                    })

                await self.write_message(ujson.dumps({
                    "action": "update",
                    "data": {
                        "type": "impromptu",
                        "list": l
                    }
                }))

            elif data_type == "get-timer-info":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion',
                                                                                         'interpellations']:
                    return
                boardcast_data = {"action": "update", 'data': core.current_agenda.get_timer_info()}
                boardcast_data['data']['type'] = 'timer-info'
                await self.write_message(ujson.dumps(boardcast_data))

            elif data_type == "get-vote-result":
                q_type = data['q_type']
                bill_id = int(data['bill_id'])
                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "vote-result"
                    }
                }

                if q_type == "impromptu":
                    impromptus = core.impromptu.get_impromptus()
                    # TODO: 理論上temp_id會是嚴格遞增，所以可以二分temp_id，至少這樣最多要O(logn)而不是O(n)就可以找到了
                    for impromptu in impromptus:
                        if impromptu['temp_id'] == bill_id:
                            boardcast_data['data']['result'] = impromptu['result']
                            break

                elif q_type == "proposal":
                    if (bill := core.proposal.bills_map.get(bill_id)) is not None:
                        boardcast_data['data']['result'] = bill.bill.get_vote_result()
                else:
                    pass

                await self.write_message(ujson.dumps(boardcast_data))

            elif data_type == "current-agenda":
                boardcast_data = {
                    "action": "update",
                    "data": {
                    }
                }
                if core.current_agenda is not None:
                    boardcast_data['data'] = core.current_agenda.get_agenda_4_frontend()
                    boardcast_data['data']['index'] = core.agenda_index
                    boardcast_data['data']['type'] = "current-agenda"
                    boardcast_data['data']['agenda'] = core.current_agenda.get_type()

                await self.write_message(ujson.dumps(boardcast_data))

    async def on_message(self, message):
        receive = ujson.loads(message)
        data = receive['data']
        if receive['action'] == "connection":
            # 這他喵到底什麼東西
            sitting_id = int(data['sitting_id'])
            if (core := SittingCoreManageService.inst.get_sittingcore(int(sitting_id))) == NotExistError:
                self.close(reason="啊哈哈，您參加的會議不存在喔～")
                return

            if (member := core.participated_members.get(int(data['member_id']))) is None:
                self.close(reason="啊哈哈，您的id不存在喔～")
                return

            if member['group'] < int(MemberGroup.SECRETARIAT):
                self.close(reason="啊哈哈，您沒有權限喔～")
                return

            core.register_callback_func(self.write_message, id(self), ClientType.SECRETARIAT)
            self.sitting_id = sitting_id

        else:
            if self.sitting_id is None:
                self.close(reason="啊哈哈，你沒有拿到session_id喔～")
                return

            await self.action_handle(receive['action'], data)

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        return True

    def on_close(self) -> None:
        if self.sitting_id is None:
            return

        core = SittingCoreManageService.inst.get_sittingcore(self.sitting_id)
        core.unregister_callback_func(id(self), ClientType.SECRETARIAT)
