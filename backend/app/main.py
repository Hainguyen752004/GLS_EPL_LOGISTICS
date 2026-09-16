# -*- coding: utf-8 -*-
"""EPL Lào — máy chủ. Chạy:

    cd D:\\Demo_Lao\\EPL_LAO_REAL
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8010 --no-access-log

Giao diện phục vụ ở `/` (thư mục frontend), API ở `/api/...`. Mỗi module một tệp route,
mỗi module một thư mục giao diện — sai đâu sửa đó.
"""
import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from sqlalchemy import text  # noqa: E402

from database import engine, tao_bang  # noqa: E402
from routes import acc_code, bao_cao, dang_nhap, danh_muc, kho, nha_cung_cap, phieu, quy_trinh, tuyen  # noqa: E402

FRONTEND = os.path.normpath(os.path.join(APP_DIR, "..", "..", "frontend"))

app = FastAPI(title="EPL Lào — Quản lý vận tải", version="1.0", docs_url="/api/docs", redoc_url=None)


@app.on_event("startup")
def khoi_dong():
    tao_bang()


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


for r in (dang_nhap, danh_muc, tuyen, phieu, bao_cao, kho, nha_cung_cap, quy_trinh, acc_code):
    app.include_router(r.router)

# Giao diện: / → index.html ; mọi tệp khác lấy thẳng từ thư mục frontend
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND, "js")), name="js")
app.mount("/modules", StaticFiles(directory=os.path.join(FRONTEND, "modules")), name="modules")
app.mount("/img", StaticFiles(directory=os.path.join(FRONTEND, "img")), name="img")


@app.get("/")
def trang_chu():
    return FileResponse(os.path.join(FRONTEND, "index.html"))
