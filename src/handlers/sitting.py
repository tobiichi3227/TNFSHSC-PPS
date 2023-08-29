"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
from urllib.parse import urlparse

import tornado.websocket
import ujson

from models.models import Sessions, Member, MemberGroup

from .base import RequestHandler, reqenv, require_permission
from utils.error import CanNotAccessError, Error, NotExistError
from services.core import SittingCoreManageService, ClientType
from .core.checkin import CheckinStatus


class _SittingEndError(Error):
    def __str__(self):
        return 'Eend'


SittingEndError = _SittingEndError()


class SittingHandler(RequestHandler):
    @reqenv
    @require_permission(MemberGroup.MEMBER)
    async def get(self, sitting_id):
        core = SittingCoreManageService.inst.get_sittingcore(int(sitting_id))
        if core == NotExistError:
            await self.error(NotExistError)
            return

        if core.participated_members[self.member['id']]['checkin_status'] in [int(CheckinStatus.NotEnter),
                                                                              int(CheckinStatus.Checkout)]:
            await self.error(CanNotAccessError)
            return

        await self.render('sitting.html', sitting_id=sitting_id)

    @reqenv
    @require_permission(MemberGroup.MEMBER, use_error_code=True)
    async def post(self, sitting_id):
        pass


class SittingWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sitting_id = None

    async def action_handle(self, action: str, data):
        core = SittingCoreManageService.inst.get_sittingcore(self.sitting_id)

        if action == "update":
            update_type = data['type']

            if update_type == "speak":
                member_id = data['member_id']

            elif update_type == "temporary-absence":
                member_id = data['member_id']

            elif update_type == "interpellation":
                member_id = data['member_id']
                officials = data['list']
                core.interpellation.add_interpellation_member(member_id, officials)

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

                core.send_boardcast(ujson.dumps({
                    "action": "update",
                    "data": {
                        "type": "update-interpellation",
                        "list": l,
                    }
                }), ClientType.SECRETARIAT)

            elif update_type == "new-impromptu-motion":
                member_id = data['member_id']
                bill_name = data['bill_name']
                if bill_name.strip() == "":
                    return

                core.impromptu.add_impromptu(member_id, bill_name)
                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "new-impromptu-motion",
                        "list": [{"count": i['count'], "bill_name": i['bill_name'],
                                  "name": core.participated_members[i['member_id']]['name']} for i in
                                 core.impromptu.get_pre_impromptus()]
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data),
                                    ClientType.MEMBER | ClientType.SECRETARIAT)

            elif update_type == "to-second-motion":
                index = data['index']
                member_id = data['member_id']
                core.impromptu.to_second_motion_impromptu(member_id, index)
                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "to-second-motion",
                        "list": [{"count": i['count'], "bill_name": i['bill_name'],
                                  "name": core.participated_members[i['member_id']]['name']} for i in
                                 core.impromptu.get_pre_impromptus()]
                    }
                }
                core.send_boardcast(ujson.dumps(boardcast_data),
                                    ClientType.MEMBER | ClientType.SECRETARIAT)

            elif update_type == "update-vote-count":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion']:
                    return

                member_id = data['member_id']
                index = data['index']
                res = core.current_agenda.update_vote_count(member_id, index)
                counts = []
                for option in core.current_agenda.get_vote_options():
                    counts.append(option['count'])

                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "update-vote-count",
                        "counts": counts
                    }
                }

                if core.current_agenda.get_vote_info()['is_free'] and res != False:
                    boardcast_data['data']['member_id'] = member_id
                    boardcast_data['data']['index'] = index

                core.send_boardcast(ujson.dumps(boardcast_data),
                                    ClientType.MEMBER | ClientType.SECRETARIAT | ClientType.PPT)

            elif update_type == "":
                pass
            elif update_type == "":
                pass

        elif action == "query":
            # 工廠模型？
            if data['type'] == "interpellation-officials":
                await self.write_message(ujson.dumps({
                    "action": "update",
                    "data": {
                        "type": "update-officials",
                        "officials": core.interpellation.get_officials()
                    }
                }))

            elif data['type'] == "impromptus":
                await self.write_message(ujson.dumps({
                    "action": "update",
                    "data": {
                        "type": "new-impromptu-motion",
                        "list": [{"count": i['count'], "bill_name": i['bill_name'],
                                  "name": core.participated_members[i['member_id']]['name']} for i in
                                 core.impromptu.get_pre_impromptus()],
                    }
                }))

            elif data['type'] == "vote-info":
                if core.current_agenda is None or core.current_agenda.get_type() not in ['impromptu-motion',
                                                                                         'proposal-discussion']:
                    return

                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "vote-info"
                    }
                }

                vf = core.current_agenda.get_vote_info()
                if vf['is_start'] and not vf['is_end']:
                    boardcast_data['data']['is_voting'] = True
                    boardcast_data['data']['options'] = core.current_agenda.get_vote_options()

                else:
                    boardcast_data['data']['is_voting'] = False

                await self.write_message(ujson.dumps(boardcast_data))

    async def on_message(self, message):
        """

        vote interpellations temporary-absence speak impromptu-motion

        :param message:
        :return:
        """
        print("sitting", message)
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

            if member['group'] not in [MemberGroup.MEMBER, MemberGroup.ASSOCIATION]:
                self.close(reason="啊哈哈，您沒有權限喔～")
                return

            if member['checkin_status'] in [int(CheckinStatus.NotEnter), int(CheckinStatus.Checkout)]:
                self.close(reason="啊哈哈，您沒簽到或是已經離場了～")
                return

            core.register_callback_func(self.write_message, id(self), ClientType.MEMBER)
            self.sitting_id = sitting_id

        else:
            if self.sitting_id is None:
                self.close(reason="啊哈哈，你沒有拿到session_id喔～")
                return

            await self.action_handle(receive['action'], data)

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        # print(parsed_origin.netloc.endswith(":3227"))
        return True

    def on_close(self) -> None:
        if self.sitting_id is None:
            return

        core = SittingCoreManageService.inst.get_sittingcore(self.sitting_id)
        core.unregister_callback_func(id(self), ClientType.MEMBER)


class JoinSittingHandler(RequestHandler):

    @reqenv
    @require_permission(MemberGroup.MEMBER)
    async def get(self, sitting_id):
        await self.render('join-sitting.html', sitting_id=sitting_id)
