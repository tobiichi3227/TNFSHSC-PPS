"""
    @author: tobiichi3227
    @day: 2023/7/3
"""

from handlers.index import IndexHandler
from handlers.login import LoginHandler
from handlers.about import AboutHandler
from handlers.info import InfoHandler
from handlers.sitting import SittingHandler, JoinSittingHandler, SittingWebSocketHandler

from handlers.manage.manage import ManageHandler
from handlers.manage.sittings import SittingsManageHandler
from handlers.manage.member import MemberManageHandler
from handlers.manage.bill import BillsManageHandler
from handlers.manage.sysconfig import SysConfigHandler
from handlers.manage.log import LogManageHandler

from handlers.core.sitting import SittingManageHandler
from handlers.core.checkin import CheckinManageHandler
from handlers.core.agenda import AgendaManageHandler, AgendaWebSocketHandler
from handlers.core.config import SittingConfigManageHandler
from handlers.core.ppt import PPTPeviewHandler
from handlers.core.ppt import PPTWebSocketHandler

urls = [
    ('/info', InfoHandler),
    ('/index', IndexHandler),
    ('/login', LoginHandler),
    ('/sitting/(\d+)', SittingHandler),
    ('/sitting/ppt/(\d+)', PPTPeviewHandler),
    ('/sitting/pptws/(\d+)', PPTWebSocketHandler),
    ('/sittingws/(\d+)', SittingWebSocketHandler),
    ('/join-sitting/(\d+)', JoinSittingHandler),
    ('/about', AboutHandler),

    ('/manage', ManageHandler),
    ('/manage/bills', BillsManageHandler),
    ('/manage/sysconfig', SysConfigHandler),
    ('/manage/sittings', SittingsManageHandler),
    ('/manage/member', MemberManageHandler),
    ('/manage/log', LogManageHandler),

    ('/core/sitting/(\d+)', SittingManageHandler),
    ('/core/sitting/checkin/(\d+)', CheckinManageHandler),
    ('/core/sitting/agenda/(\d+)', AgendaManageHandler),
    ('/core/sitting/agendaws/(\d+)', AgendaWebSocketHandler),
    ('/core/sitting/config/(\d+)', SittingConfigManageHandler),
]
