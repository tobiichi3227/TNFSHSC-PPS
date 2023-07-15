from services.sysconfig import SysConfigService
from .base import RequestHandler, reqenv


class InfoHandler(RequestHandler):
    @reqenv
    async def get(self):
        config = (await SysConfigService.inst.get_config())
        await self.render('info.html', current_appointed_dates=config['appointed_dates'],
                          current_sessions=config['sessions'])

    @reqenv
    async def post(self):
        pass
