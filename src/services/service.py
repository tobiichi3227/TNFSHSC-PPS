import asyncio
import importlib

from .core import SittingCoreManageService, SittingCore
from .log import LogService
from .sysconfig import SysConfigService
from .permission import PermissionService


class Service:
    pass


async def services_init(service):
    import services.core
    import handlers.base
    import services.agenda.impromptu
    import services.agenda.interpellation
    import services.agenda.proposal
    importlib.reload(services.core)
    importlib.reload(handlers.base)
    importlib.reload(services.agenda.proposal)
    importlib.reload(services.agenda.interpellation)
    importlib.reload(services.agenda.impromptu)

    print("services init")
    service.Log = LogService()
    service.SysConfig = SysConfigService()
    service.CoreManage = SittingCoreManageService()
    service.Permission = PermissionService()
    service.Core = SittingCore
    await service.SysConfig.Init()

    import handlers.core.checkin
    importlib.reload(handlers.core.checkin)
