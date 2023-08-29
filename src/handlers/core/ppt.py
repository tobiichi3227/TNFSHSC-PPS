"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
import ujson
from urllib.parse import urlparse

import tornado.websocket
import ujson

from handlers.base import RequestHandler, reqenv
from services.core import SittingCoreManageService, ClientType, SittingCore
from models.models import MemberGroup
from utils.error import NotExistError


class PPTPeviewHandler(RequestHandler):
    @reqenv
    async def get(self, sitting_id):
        if (core := SittingCoreManageService.inst.get_sittingcore(int(sitting_id))) == NotExistError:
            await self.render(error=NotExistError)
            # await self.error(NotExistError)
            return

        sessions = core.config['sessions']
        appointed_dates = core.config['appointed_dates']
        sittings = core.sittings
        sitting_type = core.sitting_type

        try:
            page = self.get_argument("page")
        except tornado.web.HTTPError:
            page = None

        kwargs = {
            'sitting_id': sitting_id,
            'appointed_dates': appointed_dates,
            'sessions': sessions,
            'sittings': sittings,
            'sitting_type': sitting_type,
        }

        if page is None:
            await self.render('ppt/default.html', **kwargs)
            return
        else:
            if page == "text":
                pass
            elif page == "no-free-vote":
                await self.render('ppt/no-free-vote.html', **kwargs)
            elif page == "free-vote":
                await self.render('ppt/free-vote.html', **kwargs)
            elif page == "interpellation":
                await self.render('ppt/interpellation.html', **kwargs)
            elif page == "sleep":
                await self.render('ppt/sleep.html', **kwargs)


class PPTWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sitting_id = None

    async def action_handle(self, action: str, data):
        core: SittingCore = SittingCoreManageService.inst.get_sittingcore(self.sitting_id)

        if action == "query":
            if data['type'] == "current-agenda":
                boardcast_data = {
                    "action": "update",
                    "data": {

                    }
                }

                if core.is_pause:
                    boardcast_data['data']['type'] = "sleep"
                    boardcast_data['data']['duration'] = core.timer.duration
                    boardcast_data['data']['run_times'] = core.timer.run_times

                elif core.current_agenda is not None:
                    if core.current_agenda.get_type() == "text":
                        boardcast_data['data']['type'] = "text"
                        boardcast_data['data']['text'] = core.current_agenda.get_name()

                    elif core.current_agenda.get_type() == "proposal-discussion":
                        boardcast_data['data']['type'] = "proposal"
                        boardcast_data['data']['text'] = core.current_agenda.get_name()
                        if core.current_agenda.current_bill is not None:
                            boardcast_data['data']['bill_name'] = core.current_agenda.current_bill.bill.get_name()
                            boardcast_data['data']['vote_info'] = core.current_agenda.get_vote_info()

                    elif core.current_agenda.get_type() == "interpellations":
                        boardcast_data['data']['type'] = "interpellations"
                        boardcast_data['data']['text'] = core.current_agenda.get_name()
                        current_idx = core.current_agenda.i
                        if current_idx != -1:
                            interpellations_order = core.current_agenda.get_interpellations_order()
                            interpellations = core.current_agenda.get_interpellations()
                            member_id = interpellations_order[current_idx]
                            participated_members = core.participated_members
                            boardcast_data['data']['current_status'] = interpellations[member_id]['status']
                            boardcast_data['data']['current_name'] = participated_members[member_id]['name']
                            boardcast_data['data']['timer_info'] = core.current_agenda.get_timer_info()
                            l = []
                            for member_id in interpellations_order[current_idx + 1:len(interpellations_order)]:
                                l.append(participated_members[member_id]['name'])
                            boardcast_data['data']['pendings'] = l

                    elif core.current_agenda.get_type() == "impromptu-motion":
                        boardcast_data['data']['type'] = "impromptu"
                        boardcast_data['data']['text'] = core.current_agenda.get_name()
                        if core.current_agenda.current_bill is not None:
                            boardcast_data['data']['bill_name'] = core.current_agenda.current_bill['bill_name']
                            boardcast_data['data']['vote_info'] = core.current_agenda.get_vote_info()

                await self.write_message(ujson.dumps(boardcast_data))

            elif data['type'] == "no-free-vote-info":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion']:
                    return

                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "no-free-vote-info",
                        "is_start": core.current_agenda.get_vote_info()['is_start'],
                        "is_end": core.current_agenda.get_vote_info()['is_end'],
                        "list": core.current_agenda.get_vote_options(),
                        # "bill_name": core.current_agenda.current_bill.bill.get_name(),
                        "timer_info": core.current_agenda.get_timer_info(),
                    }
                }

                if core.current_agenda.get_type() == "impromptu-motion":
                    boardcast_data['data']['bill_name'] = core.current_agenda['bill_name']
                else:
                    boardcast_data['data']['bill_name'] = core.current_agenda.current_bill.bill.get_name()

                await self.write_message(ujson.dumps(boardcast_data))

            elif data['type'] == "free-vote-info":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion']:
                    return

                d = {}
                for member_id, member in core.participated_members.items():
                    if member['group'] == int(MemberGroup.MEMBER):
                        d[member_id] = {
                            'name': str(member['number'])[0:3] + member['name'],
                            'checkin_status': member['checkin_status']
                        }

                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "free-vote-info",
                        "is_start": core.current_agenda.get_vote_info()['is_start'],
                        "is_end": core.current_agenda.get_vote_info()['is_end'],
                        "list": core.current_agenda.get_vote_options(),
                        # "bill_name": core.current_agenda.current_bill.bill.get_name(),
                        "timer_info": core.current_agenda.get_timer_info(),
                        "members": d
                    }
                }

                if core.current_agenda.get_type() == "impromptu-motion":
                    boardcast_data['data']['bill_name'] = core.current_agenda['bill_name']
                else:
                    boardcast_data['data']['bill_name'] = core.current_agenda.current_bill.bill.get_name()

                await self.write_message(ujson.dumps(boardcast_data))

            elif data['type'] == "interpellation-timer-info":
                pass

    async def on_message(self, message):
        """

        vote interpellations temporary-absence speak impromptu-motion

        :param message:
        :return:
        """
        receive = ujson.loads(message)
        data = receive['data']
        if receive['action'] == "connection":
            sitting_id = int(data['sitting_id'])
            if (core := SittingCoreManageService.inst.get_sittingcore(int(sitting_id))) == NotExistError:
                self.close(reason="啊哈哈，您參加的會議不存在喔～")
                return

            core.register_callback_func(self.write_message, id(self), ClientType.PPT)
            self.sitting_id = sitting_id

        else:
            if self.sitting_id is None:
                self.close(reason="啊哈哈，您加入錯會議的")
                return

            await self.action_handle(receive['action'], data)

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        return True

    def on_close(self) -> None:
        if self.sitting_id is None:
            return

        core = SittingCoreManageService.inst.get_sittingcore(self.sitting_id)
        core.unregister_callback_func(id(self), ClientType.PPT)
