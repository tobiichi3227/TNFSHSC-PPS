from collections import defaultdict
from typing import List, DefaultDict, Dict


class Bill:
    def __init__(self, bill_id: int, name: str, desc: str, data: str):
        self.vote_result = None
        self.data = data
        self.name = name
        self.desc = desc
        self.bill_id = bill_id
        self.parse_data()

    def get_name(self):
        return self.name

    def set_name(self, name: str):
        self.name = name

    def set_vote_result(self, result):
        self.vote_result = result

    def get_vote_result(self):
        return self.vote_result

    def parse_data(self):
        # 把vote reuslt提取出來
        pass


class BillNode:
    def __init__(self, parent_id, bill: Bill):
        self.child_indices: List[int] = []
        self.parent_id: int = parent_id
        self.bill = bill

    def add_child_bill(self, child_idx: int):
        self.child_indices.append(child_idx)

    def get_child_bills(self):
        return self.child_indices


def tree_build(res):
    bills_map: Dict[int | BillNode] = {}
    vis: DefaultDict[int | bool] = defaultdict(bool)
    root_bills: List[int] = []

    for bill in res:
        if bill.root_id == -1:
            root_bills.append(bill.id)
            bills_map[bill.id] = BillNode(bill.id, Bill(bill.id, bill.name, bill.desc, bill.data))
            vis[bill.id] = True
            continue

        if vis[bill.id]:
            bill_node = bills_map[bill.id]
            bill_node.bill.bill_id = bill.id
            bill_node.bill.name = bill.name

            bill_node.parent_id = bill.parent_id

        else:
            bills_map[bill.id] = BillNode(bill.parent_id, Bill(bill.id, bill.name, bill.desc, bill.data))
            vis[bill.id] = True

        if not vis[bill.parent_id]:
            bills_map[bill.parent_id] = BillNode(-2, Bill(bill.parent_id, 'null', 'null', 'null'))
            bills_map[bill.parent_id].child_indices.append(bill.id)
            vis[bill.parent_id] = True

        else:
            bills_map[bill.parent_id].child_indices.append(bill.id)

    return bills_map, root_bills


def gen_tree_html(bills_map, root_bills: List[int]):
    _html_data = ''
    button_html = """
        <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{id}\" type=\"1\">
            無異議通過
        </button>
        <button class=\"btn btn-primary px-sm-1 py-sm-0\" id=\"{id}\" type=\"2\">
            投票
        </button>
        <button class=\"btn btn-secondary px-sm-1 py-sm-0\" id=\"{id}\" type=\"3\">
            取消
        </button>
    """

    # vis: DefaultDict[int | bool] = defaultdict(bool)
    # 因為是樹，所以不用vis
    # 節點v的父節點p會先被dfs，且當v被dfs時，p是v唯一走過的鄰節點，所以不用vis

    def _dfs(p: int, depth: int):
        html = ''
        if depth == 0:
            html = f"<span id={p}>{bills_map[p].bill.name} " + "{button}</span>"
        elif depth == 1:
            html = f"\n<br>\n" \
                   f"<span id={p} style=\"padding-left: {depth}0%;\">{bills_map[p].bill.name}" + "{button}</span>"
        elif depth == 2:
            html = f"\n<br>\n" \
                   f"<span id={p} style=\"padding-left: {depth}0%;\">{bills_map[p].bill.name}" + "{button}</span>"

        if len(bills_map[p].child_indices) == 0 and bills_map[p].bill.get_vote_result() is None:
            return html.format(button=button_html.format(id=p))

        elif len(bills_map[p].child_indices) == 0 and bills_map[p].bill.get_vote_result() is not None:
            return html + "<span>已經表決完了</span>"

        for u in bills_map[p].child_indices:
            # if not vis[u]:
            html += _dfs(u, depth + 1)

        return html

    for root in root_bills:
        _html_data += _dfs(root, depth=0)

    return _html_data
