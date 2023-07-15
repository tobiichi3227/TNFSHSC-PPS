"""
    @author: tobiichi3227
    @day: 2023/7/3
"""
import json
from urllib.parse import urlparse

import tornado.websocket

from sqlalchemy import select

from models.models import Sessions, Member, MemberGroup

from .base import RequestHandler, reqenv

from util.error import CanNotAccessError, Error

from services.core import SittingCoreService, ClientType
from services.log import LogService


class _SittingEndError(Error):
    def __str__(self):
        return 'Eend'


SittingEndError = _SittingEndError()


class SittingHandler(RequestHandler):
    @reqenv
    async def get(self, sitting_id):
        member_session_id = SittingCoreService.inst.member_session_id
        # for dev
        # if member_session_id.get(self.member['id']) is None or member_session_id[self.member['id']] == "checkout":
        #     await self.error(CanNotAccessError)

        # official select
        async with Sessions() as session:
            async with session.begin():
                stmt = select(Member.id.label("id"), Member.official_name.label("official_name")).where(
                    Member.group == int(MemberGroup.ASSOCIATION))
                officials = await session.execute(stmt)

        # prevent user from seconding motions which have already been seconded

        await self.render('sitting.html', sitting_id=sitting_id, officials=officials,
                          impromptus=SittingCoreService.inst.pre_impromptus,
                          to_second_motion_list=SittingCoreService.inst.to_second_motion_impromptu)

    @reqenv
    async def post(self, sitting_id):
        reqtype = self.get_argument('reqtype')
        if reqtype == "request_session_id":
            member_session_id = SittingCoreService.inst.member_session_id
            member_id = int(self.get_argument('member_id'))

            if not SittingCoreService.inst.is_sitting_end():
                if (session_id := member_session_id.get(member_id)) is None:
                    await self.error(CanNotAccessError)
                else:
                    await self.finish(session_id)
            else:
                await self.error(SittingEndError)


class SittingWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        SittingCoreService.inst.register_callback_func(self.write_message, id(self), ClientType.MEMBER)

    async def action_handle(self, action: str, data):
        if action == "update":
            update_type = data['type']

            if update_type == "speak":
                member_id = data['member_id']

            elif update_type == "temporary-absence":
                member_id = data['member_id']

            elif update_type == "interpellation":
                member_id = data['member_id']
                officials = data['list']
                SittingCoreService.inst.add_interpellation_member(member_id, officials)

            elif update_type == "new-impromptu-motion":
                member_id = data['member_id']
                bill_name = data['bill_name']
                if bill_name.strip() == "":
                    return

                SittingCoreService.inst.add_impromptu(member_id, bill_name)
                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "new-impromptu-motion",
                        "list": SittingCoreService.inst.get_impromptus()
                    }
                }
                SittingCoreService.inst.send_boardcast(json.dumps(boardcast_data),
                                                       ClientType.MEMBER | ClientType.SECRETARIAT)

            elif update_type == "to-second-motion":
                index = data['index']
                member_id = data['member_id']
                SittingCoreService.inst.to_second_motion_impromptu(member_id, index)
                boardcast_data = {
                    "action": "update",
                    "data": {
                        "type": "to-second-motion",
                        "list": SittingCoreService.inst.get_impromptus()
                    }
                }
                SittingCoreService.inst.send_boardcast(json.dumps(boardcast_data),
                                                       ClientType.MEMBER | ClientType.SECRETARIAT)

            elif update_type == "update-vote-count":
                pass
            elif update_type == "":
                pass
            elif update_type == "":
                pass

    async def on_message(self, message):
        """

        vote interpellations temporary-absence speak impromptu-motion

        :param message:
        :return:
        """
        print(message)
        receive = json.loads(message)
        data = receive['data']
        if receive['action'] == "connection":
            # for dev
            # if CoreService.inst.member_session_id.get(data['member_id']) != data['session_id']:
            #     self.close()
            pass
        else:
            await self.action_handle(receive['action'], data)

        # CoreService.inst.send_boardcast('boardcast test data', 1)

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        # print(parsed_origin.netloc.endswith(":3227"))
        return True

    def on_close(self) -> None:
        SittingCoreService.inst.unregister_callback_func(id(self), ClientType.MEMBER)


class JoinSittingHandler(RequestHandler):

    @reqenv
    async def get(self, sitting_id):
        await self.render('join-sitting.html', sitting_id=sitting_id)
