# -*- coding: utf-8 -*-
"""Chạy bộ kiểm trong tiến trình trên DB BẢN SAO máy thử (epl_lao_d<số>) mà KHÔNG để lại gì trên DB (06/10).

Vì sao: 8011 + Web anh Tune đang dùng d7 để bấm tay; DB thật / DB tải (epl_lao, epl_lao_tai, epl_ketoan) không chạy bộ kiểm nữa.
Luật: mọi ghi nằm trong giao dịch, cuối bài ROLLBACK; chỉ ghi dòng THỬ do bài tự tạo, không sửa / xoá dòng đang có.

    from _d7_trong_gd import mo, dong
    gd = mo()                 # trước khi import mã app — đặt DATABASE_URL = .may_thu/url_epl_lao_d7.txt (hoặc tệp EPL_KIEM_URL)
    db = gd.db                # Session: commit() = nhả SAVEPOINT, rollback() = về SAVEPOINT — giao dịch ngoài không bao giờ commit
    ...
    dong(gd)                  # ROLLBACK cả hai giao dịch

Bộ đệm báo cáo (services/dem_bao_cao) đọc / ghi bản lưu bằng `db.get_bind().connect()` — kết nối RIÊNG có commit. Ở đây kết nối
đó bị thay bằng một giao dịch thứ hai (cũng ROLLBACK cuối bài): bản lưu vẫn đọc / ghi được để thử "khởi động lại máy chủ", nhưng
không có gì tới DB. Câu dọn bản lưu cũ (2 % ngẫu nhiên) bị tắt — không đụng dòng đang có. lock_timeout 3 s: gặp dòng 8011 đang
khoá thì báo lỗi ngay chứ không chờ (không làm người đang bấm tay phải đợi).
"""
import os
import re
import sys

KIEM = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(KIEM)
APP = os.path.join(GOC, "backend", "app")


class _GiaoDichPhu:
    """Thay cho `bind.connect()` của bộ đệm: mỗi lần là một SAVEPOINT trong giao dịch phụ; `commit()` không làm gì."""

    def __init__(self, c):
        self.c = c

    def __enter__(self):
        self.sp = self.c.begin_nested()
        return self

    def execute(self, *a, **k):
        return self.c.execute(*a, **k)

    def commit(self):
        pass

    def __exit__(self, kieu, *_):
        if self.sp.is_active:
            (self.sp.rollback if kieu else self.sp.commit)()
        return False


class _KhongDon:
    @staticmethod
    def random():
        return 1.0                           # dem_bao_cao: random() < 0.02 thì dọn bản lưu cũ — không bao giờ


class GiaoDich:
    pass


def mo(tep=None):
    tep = tep or os.environ.get("EPL_KIEM_URL", "url_epl_lao_d7.txt")
    url = open(os.path.join(GOC, ".may_thu", tep), encoding="utf-8").read().strip()
    from sqlalchemy.engine import make_url
    ten = make_url(url).database or ""
    if not re.search(r"_d\d+$", ten):
        raise SystemExit("DỪNG: %s trỏ DB «%s» — bộ kiểm này chỉ chạy trên DB bản sao (…_d<số>)." % (tep, ten))
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("EPL_LAO_CHAM_MS", "999999")
    if APP not in sys.path:
        sys.path.insert(0, APP)
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from database import engine
    from services import dem_bao_cao as DEM
    gd = GiaoDich()
    gd.ten = ten
    gd.c1, gd.c2 = engine.connect(), engine.connect()
    gd.t1, gd.t2 = gd.c1.begin(), gd.c2.begin()
    for c in (gd.c1, gd.c2):
        c.execute(text("SET LOCAL lock_timeout = '3s'"))
    gd.c1.connect = lambda: _GiaoDichPhu(gd.c2)
    if not DEM._CO_BANG:
        DEM._CO_BANG.append(True)
    DEM.random = _KhongDon
    gd.db = Session(bind=gd.c1, join_transaction_mode="create_savepoint", autoflush=False)
    return gd


def dong(gd):
    try:
        gd.db.close()
    finally:
        for t in (gd.t1, gd.t2):
            if t.is_active:
                t.rollback()
        gd.c1.close(); gd.c2.close()
    print("(đã ROLLBACK — %s không đổi)" % gd.ten, flush=True)
