# -*- coding: utf-8 -*-
"""EPL Lào — máy chủ. Chạy:

    cd D:\\Demo_Lao\\EPL_LAO_REAL
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log

Giao diện phục vụ ở `/` (thư mục frontend), API ở `/api/...`. Mỗi module một tệp route,
mỗi module một thư mục giao diện — sai đâu sửa đó.
"""
import io
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sqlalchemy import text  # noqa: E402

from database import engine, tao_bang  # noqa: E402
from routes import (acc_code, anh, ban_hang, bao_cao, chung_tu, dang_nhap, danh_muc, kho, kho_hang,  # noqa: E402
                    nha_cung_cap, phieu,
                    phieu_linh, quy_trinh, sua_chua, tat_toan, the_cao_toc, theo_doi, tuyen, vi_tri, chu_xe, hoa_don, hop_dong, giao_nhan, can_mo, lien_thong, kho_xem)  # noqa: E402

FRONTEND = os.path.normpath(os.path.join(APP_DIR, "..", "..", "frontend"))

app = FastAPI(title="EPL Lào — Quản lý vận tải", version="1.0", docs_url="/api/docs", redoc_url=None)


@app.on_event("startup")
def khoi_dong():
    tao_bang()
    # tính sẵn báo cáo tháng này / tháng trước trong luồng riêng — người mở báo cáo đầu tiên không phải chờ (24/09)
    from services import lam_nong
    lam_nong.bat_dau()


@app.exception_handler(Exception)
async def loi_chung(request: Request, exc: Exception):
    # Không lộ stack trace lẫn chuỗi kết nối ra trình duyệt
    return JSONResponse(status_code=500, content={"detail": {"ma": "LOI_MAY_CHU", "loi": "Máy chủ gặp lỗi. Xem log."}})


@app.get("/api/suc-khoe")
def suc_khoe():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"ok": db_ok, "db": engine.url.database, "phien_ban": app.version}


for r in (dang_nhap, danh_muc, tuyen, phieu, phieu_linh, tat_toan, theo_doi, vi_tri, bao_cao,
          kho, kho_hang, nha_cung_cap, quy_trinh, acc_code, chung_tu, ban_hang, chu_xe, hoa_don, sua_chua,
          the_cao_toc, anh, hop_dong, giao_nhan, can_mo, lien_thong, kho_xem):
    app.include_router(r.router)

# Giao diện: / → index.html ; mọi tệp khác lấy thẳng từ thư mục frontend
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND, "js")), name="js")
app.mount("/modules", StaticFiles(directory=os.path.join(FRONTEND, "modules")), name="modules")
app.mount("/img", StaticFiles(directory=os.path.join(FRONTEND, "img")), name="img")
# Thư viện ngoài để SẴN trong dự án, không gọi CDN: máy chủ bên Lào có lúc không ra được Internet.
app.mount("/vendor", StaticFiles(directory=os.path.join(FRONTEND, "vendor")), name="vendor")


# ---------------------------------------------------------------- dấu phiên bản cho tệp giao diện
# Trình duyệt giữ css/js rất dai: sửa giao diện xong mà không Ctrl+F5 thì người dùng vẫn thấy bản cũ
# (markup mới mà kiểu cũ → hỏng màu, lệch khung). Đóng số phiên bản = lần sửa mới nhất của thư mục
# frontend vào đường dẫn tệp, đổi tệp là đổi đường dẫn, trình duyệt tự tải lại. Nhớ 5 giây cho nhẹ.
_ver = {"luc": 0.0, "ma": ""}


def phien_ban_giao_dien():
    import time
    if time.time() - _ver["luc"] < 5 and _ver["ma"]:
        return _ver["ma"]
    moi_nhat = 0.0
    for goc, _thu_muc, tep in os.walk(FRONTEND):
        if "vendor" in goc:
            continue
        for t in tep:
            if t.rsplit(".", 1)[-1].lower() in ("css", "js", "html"):
                try:
                    moi_nhat = max(moi_nhat, os.path.getmtime(os.path.join(goc, t)))
                except OSError:
                    pass
    _ver["luc"], _ver["ma"] = time.time(), format(int(moi_nhat), "x")
    return _ver["ma"]


@app.get("/")
def trang_chu():
    html = io.open(os.path.join(FRONTEND, "index.html"), encoding="utf-8").read()
    return HTMLResponse(html.replace("__VER__", phien_ban_giao_dien()),
                        headers={"Cache-Control": "no-cache"})
