# -*- coding: utf-8 -*-
"""Chạy bài HTTP kiem/thu_ban_giao.py NGAY TRONG tiến trình trên bản sao _d7 (06/10) — để thử mã bàn giao mới mà không phải
khởi động lại máy 8011 (máy đó chạy mã đã nạp lúc bật).

    python kiem/thu_ban_giao_trong_gd.py

Lời gọi urlopen của bài đi vào FastAPI TestClient; mọi thứ bài ghi (đăng nhập, tạo khoá bàn giao) nằm trong MỘT giao dịch ngoài
(phiên chạy savepoint), cuối ROLLBACK — d7 không đổi, khoá máy 8011 đang cầm không bị thay. Không gọi mạng, không chạy sự kiện
khởi động. Chỉ thay `urllib` của riêng bài thu_ban_giao (không đụng urllib của ứng dụng).
"""
import io
import os
import sys
import types
import urllib.error
import urllib.parse
import urllib.request

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ.pop("KHOA_BAN_GIAO_TEP", None)               # tạo khoá thử TRONG giao dịch, rollback bỏ
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
sys.path.insert(0, os.path.join(GOC, "kiem"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, text              # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402

GOC_GIA = "http://thu-trong-giao-dich"


class _TraLoi:
    def __init__(self, r):
        self.status, self._than = r.status_code, r.content

    def read(self):
        return self._than

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def main():
    import thu_ban_giao as TB
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    c = TestClient(app, raise_server_exceptions=False)

    def urlopen(yc, timeout=None):
        r = c.request(yc.get_method(), yc.full_url[len(GOC_GIA):], content=yc.data, headers=dict(yc.header_items()))
        if r.status_code >= 400:
            raise urllib.error.HTTPError(yc.full_url, r.status_code, r.reason_phrase, None, io.BytesIO(r.content))
        return _TraLoi(r)
    TB.urllib = types.SimpleNamespace(request=types.SimpleNamespace(Request=urllib.request.Request, urlopen=urlopen),
                                      error=urllib.error, parse=urllib.parse)
    TB.GOC = GOC_GIA
    ma = 1
    try:
        TB.main()
    except SystemExit as e:
        ma = e.code or 0
    finally:
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
    print("đã ROLLBACK — bản sao d7 không đổi")
    sys.exit(ma)


if __name__ == "__main__":
    main()
