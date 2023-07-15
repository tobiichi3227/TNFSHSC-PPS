import hashlib
import json
from urllib.parse import urlparse

import tornado

from services.core import SittingCoreService, ClientType
from ..base import RequestHandler, reqenv

from models.models import Sessions, Member, AbsenceRecord
from ..manage import bill


class AgendaManageHandler(RequestHandler):
    @reqenv
    async def get(self, sitting_id):
        agenda = [
            {
                "type": "text",
                "name": "主席致詞"
            },
            {
                "type": "text",
                "name": "施政報告"
            },
            {
                "type": "proposal-discussion",
                "name": "提案討論",
                "list": [  # 在database中只存bill id
                    {
                        "type": "bill-with-sub-bills",
                        "name": "議事系統專法一讀",
                        "list": [
                            {
                                "type": "bill-with-sub-bills",
                                "name": "第一條",
                                "list": [
                                    {
                                        "type": "bill",
                                        "name": "第一條之一",
                                        "vote-result": {
                                            "同意": 10,
                                            "不同意": 1,
                                            "棄權": 0,
                                        }
                                    },
                                    {
                                        "type": "bill",
                                        "name": "第一條之二",
                                        "vote-result": {
                                            "同意": 10,
                                            "不同意": 1,
                                            "棄權": 0,
                                        }
                                    },
                                ]
                            }
                        ]
                    },
                    {
                        "type": "bill-with-sub-bills",
                        "name": "議事系統專法一讀",
                        "list": [
                            {
                                "type": "bill-with-sub-bills",
                                "name": "第一條",
                                "list": [
                                    {
                                        "type": "bill",
                                        "name": "第一條之一",
                                        "vote-result": {
                                            "同意": 10,
                                            "不同意": 1,
                                            "棄權": 0,
                                        }
                                    },
                                ]
                            }
                        ]
                    },
                    {
                        "type": "bill-with-sub-bills",
                        "name": "議事系統專法二讀",
                        "list": [
                            {
                                "type": "bill",
                                "name": "第二條",
                                "vote-result": {}
                            }
                        ]
                    }
                ]
            },
            {
                "type": "interpellations",
                "name": "會務詢答",
                "list": [
                    {
                        "type": "interpellation",
                        "member": "105",
                        "officials": []
                    },
                ]
            },
            {
                "type": "impromptu-motion",
                "name": "臨時動議",
                "list": [  # 在database中只存bill id
                    {
                        "type": "impromptu-bill-with-sub-bills",
                        "member": "208",
                        "second-motion-count": 2,
                        "name": "議事系統專法二讀",
                        "list": [
                            {
                                "type": "bill-with-sub-bills",
                                "name": "第一條",
                                "list": [
                                    {
                                        "type": "bill",
                                        "name": "第一條之一"
                                    },
                                ]
                            }
                        ]
                    },
                    {
                        "type": "impromptu-bill",
                        "member": "208",
                        "second-motion-count": 3,
                        "name": "......for ",
                        "vote-result": {

                        }
                    }
                ]
            },
            {"type": "text",
             "name": "主席結語"},
            {"type": "text",
             "name": "散會"}
        ]

        await self.render('core/agenda.html', sitting_id=sitting_id, agenda=agenda)

    @reqenv
    async def post(self):
        reqtype = self.get_argument("reqtype")
        if reqtype == "new-agenda":
            pass
        elif reqtype == "sitting-start":
            # SittingCoreService.
            pass
        elif reqtype == "sitting-stop":
            pass
        elif reqtype == "sitting-pause":
            pass


class AgendaWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        SittingCoreService.inst.register_callback_func(self.write_message, id(self), ClientType.SECRETARIAT)

    async def action_handle(self, action: str, data):
        if action == "new-vote-option":
            pass
        pass

    async def on_message(self, message):
        print(message)
        receive = json.loads(message)
        data = receive['data']
        await self.action_handle(receive['action'], data)

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        # print(parsed_origin.netloc.endswith(":3227"))
        return True

    def on_close(self) -> None:
        SittingCoreService.inst.unregister_callback_func(id(self), ClientType.SECRETARIAT)
