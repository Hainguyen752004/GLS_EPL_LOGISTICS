# -*- coding: utf-8 -*-
"""Handler route dùng Session đồng bộ KHÔNG được khai `async def` nếu không có `await`.

Đo trên máy chủ 8001 ngày 11/09: 20 yêu cầu GET song song → 17 hết giờ (45 s), health
sau đó 17 s, máy chủ nghẹn vài phút. Nguyên nhân: 83 handler khai `async def` nhưng gọi
SQLAlchemy đồng bộ ngay trên vòng lặp sự kiện. Khi pool (5 + 10) cạn, handler đứng chờ
kết nối tới 30 s và CHẶN vòng lặp, các coroutine đang giữ kết nối không chạy được để trả
→ kẹt dây chuyền. Trình duyệt mở tối đa 6 kết nối nên một người dùng chưa thấy; hai ba
người cùng mở là thấy.

`def` thường → FastAPI chạy trong threadpool, chờ pool chỉ chặn một luồng. Handler CÓ
`await` (upload, form) được phép giữ async — chúng nằm trong danh sách cho phép dưới đây,
thêm cái mới vào đó phải có lý do.
"""
import ast
import glob
import io
import os

GOC = os.path.join(os.path.dirname(__file__), "..", "app", "routes")

#: async def dùng Session nhưng CÓ await thật (đọc form/file, gọi gateway) — được phép.
CHO_PHEP_ASYNC = {
    "ai_upload_routes.py:gateway_chat", "ai_upload_routes.py:query_agent_api", "ai_upload_routes.py:action_agent_api",
    "bao_gia_routes.py:them_chung_tu",
    "fleet_routes.py:approve_vehicle_maintenance_request", "fleet_routes.py:start_vehicle_maintenance_request",
    "fleet_routes.py:complete_vehicle_maintenance_request", "fleet_routes.py:cancel_vehicle_maintenance_request",
    "workflow_routes.py:complete_delivery_order",
}


def _dung_session(node):
    for a in node.args.args + node.args.kwonlyargs:
        ann = a.annotation
        if (isinstance(ann, ast.Name) and ann.id == "Session") or (isinstance(ann, ast.Attribute) and ann.attr == "Session"):
            return True
    return False


def _la_route(node):
    return any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
               and d.func.attr in ("get", "post", "put", "delete", "patch") for d in node.decorator_list)


def test_khong_co_async_handler_dung_session_ma_khong_await():
    vi_pham, async_khong_await_cho_phep = [], []
    for tep in sorted(glob.glob(os.path.join(GOC, "*.py"))):
        ten_tep = os.path.basename(tep)
        cay = ast.parse(io.open(tep, encoding="utf-8-sig").read())
        for node in ast.walk(cay):
            if not (isinstance(node, ast.AsyncFunctionDef) and _dung_session(node) and _la_route(node)):
                continue
            co_await = any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for n in ast.walk(node))
            khoa = "%s:%s" % (ten_tep, node.name)
            if not co_await:
                (async_khong_await_cho_phep if khoa in CHO_PHEP_ASYNC else vi_pham).append("%s:%d" % (khoa, node.lineno))
            elif khoa not in CHO_PHEP_ASYNC:
                vi_pham.append(khoa + " (có await nhưng chưa ghi vào danh sách cho phép — xem có blocking DB trên vòng lặp không)")
    assert not vi_pham, "async def dùng Session đồng bộ mà không await → đổi sang def:\n  " + "\n  ".join(vi_pham)
    assert not async_khong_await_cho_phep, "mục trong CHO_PHEP_ASYNC không còn await, bỏ khỏi danh sách: %s" % async_khong_await_cho_phep


def test_khong_await_mot_handler_dong_bo():
    """Đo 11/09: sau khi đổi 83 handler sang `def`, `ban_giao_do` vẫn `await get_delivery_order_closeout(...)`
    → `await` một dict → TypeError → API bàn giao chi tiết trả 500 cho MỌI DO. Bài này gom tên mọi hàm
    `def` (đồng bộ) trong routes rồi bắt bất kỳ `await <tên>(` nào trong routes/ và services/."""
    dong_bo = set()
    for tep in glob.glob(os.path.join(GOC, "*.py")):
        cay = ast.parse(io.open(tep, encoding="utf-8-sig").read())
        for node in ast.walk(cay):
            if isinstance(node, ast.FunctionDef):
                dong_bo.add(node.name)
    vi_pham = []
    for thu_muc in (GOC, os.path.join(GOC, "..", "services")):
        for tep in glob.glob(os.path.join(thu_muc, "*.py")):
            cay = ast.parse(io.open(tep, encoding="utf-8-sig").read())
            for node in ast.walk(cay):
                if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
                    f = node.value.func
                    ten = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                    if ten in dong_bo:
                        vi_pham.append("%s:%d await %s(...)" % (os.path.basename(tep), node.lineno, ten))
    assert not vi_pham, "await một hàm đồng bộ (trả giá trị, không phải coroutine):\n  " + "\n  ".join(vi_pham)
