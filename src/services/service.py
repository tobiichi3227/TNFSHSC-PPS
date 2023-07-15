import asyncio

from .core import SittingCoreService
from .log import LogService
from .sysconfig import SysConfigService
from .permission import PermissionService


class Service:
    pass


async def services_init(service):
    print("services init")
    service.Log = LogService()
    service.SysConfig = SysConfigService()
    service.Core = SittingCoreService()
    service.Permission = PermissionService()
    await service.SysConfig.Init()
