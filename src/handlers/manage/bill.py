"""
    議案管理
    @author: tobiichi3227
    @day: 2023/7/3
"""
import json
from typing import Dict, List, DefaultDict

import tornado.web
from sqlalchemy import select, insert, update, or_, bindparam

from services.agenda.bill import BillNode, Bill, tree_build
from utils.error import Success, WrongParamError
from models.models import MemberGroup, BillSource
from ..base import RequestHandler, reqenv, require_permission

from models.models import Sessions, Bill as BillMapper


class BillsManageHandler(RequestHandler):
    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT])
    async def get(self):
        try:
            page = self.get_argument('page')
        except tornado.web.HTTPError:
            page = None

        if page is None:
            async with Sessions() as session:
                async with session.begin():
                    stmt = select(BillMapper.id, BillMapper.name).where(BillMapper.parent_id == -1).where(
                        BillMapper.root_id == -1).where(BillMapper.delete_status == False).where(
                        BillMapper.source == int(BillSource.Default)).order_by(
                        BillMapper.id)
                    res = await session.execute(stmt)
            await self.render("manage/manage-bills.html", bills=res)
            return

        elif page == "update":
            bill_id = self.get_optional_number_arg('bill_id')
            if bill_id is None:
                await self.error(WrongParamError)
                return

            async with Sessions() as session:
                async with session.begin():
                    stmt = select(BillMapper.id.label("id"), BillMapper.name.label("name"),
                                  BillMapper.root_id.label("root_id"),
                                  BillMapper.parent_id.label("parent_id"), BillMapper.desc.label("desc"),
                                  BillMapper.data.label("data")).where(
                        or_(BillMapper.root_id == bill_id, BillMapper.id == bill_id)).where(
                        BillMapper.delete_status == False).where(BillMapper.source == int(BillSource.Default))
                    res = (await session.execute(stmt))
                    stmt = select(BillMapper.sitting_id).where(BillMapper.id == bill_id)
                    res1 = (await session.execute(stmt)).fetchone()
                l, r = tree_build(res)
                bill_html = await self.gen_tree_html(l, r)

            await self.render("manage/manage-bill.html", bill_html=bill_html, root_bill=l[r[0]], sitting_id=res1[0])
            return

    @reqenv
    @require_permission([MemberGroup.SECRETARIAT, MemberGroup.ROOT], use_error_code=True)
    async def post(self):
        reqtype = self.get_argument('reqtype')

        if reqtype == "create":
            bill_name = self.get_argument('bill_name')
            root_id = self.get_optional_number_arg('root_id')
            parent_id = self.get_optional_number_arg('parent_id')
            sitting_id = self.get_optional_number_arg('sitting_id')

            err = await self.create_bill(bill_name, root_id, parent_id, sitting_id)
            await self.error(err)

        elif reqtype == "update":
            bill_name = self.get_argument('bill_name')
            root_id = self.get_optional_number_arg('root_id')
            parent_id = self.get_optional_number_arg('parent_id')
            sitting_id = self.get_optional_number_arg('sitting_id')

            err = await self.update_bill(bill_name, root_id, parent_id, sitting_id)
            await self.error(err)

        elif reqtype == "update_tree":
            root_id = self.get_optional_number_arg('root_id')
            sitting_id = self.get_optional_number_arg('sitting_id')
            appends = self.get_argument('appends')
            try:
                appends = json.loads(appends)
            except json.JSONDecoder:
                await self.error(WrongParamError)
                return

            removes = self.get_argument('removes')
            try:
                removes = json.loads(removes)
            except json.JSONDecoder:
                await self.error(WrongParamError)
                return

            await self.update_tree(root_id, sitting_id, appends, removes)

    async def gen_tree_html(self, bills_map, root_bills: List[int]):
        _html_data = ''
        button_html = """
                <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{id}\" type=\"1\">
                    新增
                </button>
                <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{id}\" type=\"2\">
                    刪除
                </button>
                <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{id}\" type=\"3\">
                    編輯
                </button>
            """

        # vis: DefaultDict[int | bool] = defaultdict(bool)
        # 因為是樹，所以不用vis
        # 節點v的父節點p會先被dfs，且當v被dfs時，p是v唯一走過的鄰節點，所以不用vis

        # 高階dfs（沒
        def _dfs(p: int, depth: int, par_tree_sz: int, cur_size: int):
            html = ''
            bill_id = bills_map[p].bill.bill_id
            if depth == 0:
                if cur_size == 0:
                    html = f"<span depth=\"{depth}\" id=\"{bill_id}\">{bills_map[p].bill.name} {button_html.format(id=bill_id)}"
                else:
                    html = f"<span depth=\"{depth}\" id=\"{bill_id}\">{bills_map[p].bill.name} {button_html.format(id=bill_id)}</span>"

            else:
                if cur_size == 0:
                    html = f"\n<br>\n" \
                           f"<span depth=\"{depth}\" id=\"{bill_id}\" style=\"padding-left: {depth}0%;\">{bills_map[p].bill.name} {button_html.format(id=bill_id)}"
                else:
                    html = f"\n<br>\n" \
                           f"<span depth=\"{depth}\" id=\"{bill_id}\" style=\"padding-left: {depth}0%;\">{bills_map[p].bill.name} {button_html.format(id=bill_id)}</span>"

            sub_tree_sz = len(bills_map[p].child_indices)
            for cur_sz, u in enumerate(bills_map[p].child_indices):
                # if not vis[u]:
                html += _dfs(u, depth + 1, sub_tree_sz - 1, cur_sz)

            return html + "</span>"

        for root in root_bills:
            _html_data += _dfs(root, depth=0, par_tree_sz=0, cur_size=0)

        return _html_data

    async def create_bill(self, bill_name: str, root_id: int, parent_id: int, sitting_id=None):
        # log
        async with Sessions() as session:
            async with session.begin():
                stmt = insert(BillMapper).values(name=bill_name, root_id=root_id, parent_id=parent_id,
                                                 sitting_id=sitting_id,
                                                 source=BillSource.Default, desc="", data="")
                await session.execute(stmt)

        return Success

    async def update_bill(self, bill_name: str, root_id: int, parent_id: int, sitting_id: int):
        async with Sessions() as session:
            try:
                stmt = update(BillMapper).values(name=bill_name, root_id=root_id, parent_id=parent_id,
                                                 sitting_id=sitting_id)
                await session.execute(stmt)
                await session.commit()  # 來發commit
            except Exception as _:
                await session.rollback()
                # Log error
                return WrongParamError

            # Log success
            return Success

    async def delete_bill(self, bill_id: int):
        async with Sessions() as session:
            async with session.begin():
                stmt = update(BillMapper).values(delete_status=True)
                await session.execute(stmt)

    async def update_tree(self, root_id, sitting_id, appends, removes):
        async with Sessions() as session:
            async with session.begin():
                stmt = select(BillMapper.id.label("id"), BillMapper.name.label("name"),
                              BillMapper.root_id.label("root_id"),
                              BillMapper.parent_id.label("parent_id"), BillMapper.desc.label("desc"),
                              BillMapper.data.label("data")).where(
                    or_(BillMapper.root_id == root_id, BillMapper.id == root_id)).where(
                    BillMapper.delete_status == False).where(BillMapper.source == int(BillSource.Default))
                res = (await session.execute(stmt))
            g, r = tree_build(res)

        for temp_id, new_bill in appends.items():
            g[int(new_bill['parent_id'])].child_indices.append(temp_id)
            g[temp_id] = BillNode(int(new_bill['parent_id']), Bill(temp_id, new_bill['name'], None, None))

        real_appends = []
        for temp_id, new_bill in appends.items():
            if int(new_bill['parent_id']) in g:
                real_appends.append({
                    "root_id": int(root_id),
                    "parent_id": int(new_bill['parent_id']),
                    "sitting_id": int(sitting_id),
                    "name": new_bill['name'],
                    "desc": "",
                    "data": "",
                    "source": BillSource.Default or ValueError,
                })

        real_removes = []

        def _dfs(p: int):
            if p not in g:
                return

            for u in g[p].child_indices:
                _dfs(int(u))
            g[g[p].parent_id].child_indices.remove(p)
            g.pop(p)
            real_removes.append({
                "id": p,
                "delete_status": True
            })

        for remove_bill in removes:
            _dfs(int(remove_bill))

        if len(real_removes) > 0:
            async with Sessions() as session:
                async with session.begin():
                    stmt = update(BillMapper).execution_options(synchronize_session=None)
                    await session.execute(stmt, real_removes)

        if len(real_appends) > 0:
            async with Sessions() as session:
                async with session.begin():
                    stmt = insert(BillMapper).execution_options(synchronize_session=None)
                    await session.execute(stmt, real_appends)
