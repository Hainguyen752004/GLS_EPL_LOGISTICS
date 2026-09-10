# -*- coding: utf-8 -*-
"""`GET /api/acc-codes` — danh muc Acc code cho o chon tren cong thuc gia thanh.

Chu du an chot: Acc code la ma tai khoan ke toan cua ben cong no, chon tu danh
muc do API ben do cap; API chua co thi o chon CHO, khong tu sinh ma. Ba trang
thai phai phan biet duoc: chua noi (`unconfigured`), noi ma khong doc duoc
(`error`), doc duoc (`remote`) — "danh muc rong" va "chua noi API" la hai cau
khac nhau voi nguoi dung.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import API_TEST_HEADERS


def _client():
    """App tran + mot middleware dat principal — duong `_require_api_principal`
    doc `request.state.principal`, ma middleware xac thuc that nam o `main.py`."""
    from routes.fleet_routes import router
    app = FastAPI()
    app.include_router(router)

    @app.middleware("http")
    async def principal(request, call_next):
        request.state.principal = "nguoi-kiem"
        return await call_next(request)

    return TestClient(app)


def test_chua_noi_api_thi_tra_rong_va_noi_ro(monkeypatch):
    monkeypatch.delenv("EPL_ACC_CODE_API", raising=False)
    r = _client().get("/api/acc-codes", headers=API_TEST_HEADERS)
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["data"] == [] and g["source"] == "unconfigured"
    assert "EPL_ACC_CODE_API" in g["message"]


def test_noi_ma_khong_doc_duoc_thi_bao_error_khong_bia_ma(monkeypatch):
    # Cong khong ai nghe -> loi mang. Khong duoc lui ve mot danh muc tu che.
    monkeypatch.setenv("EPL_ACC_CODE_API", "http://127.0.0.1:9/khong-co")
    g = _client().get("/api/acc-codes", headers=API_TEST_HEADERS).json()
    assert g["data"] == [] and g["source"] == "error"


def test_doc_duoc_thi_chuan_hoa_ve_code_name(monkeypatch):
    import json
    import routes.fleet_routes as mod

    class _Tra:
        def __init__(self, than): self._t = json.dumps(than).encode("utf-8")
        def read(self): return self._t
        def __enter__(self): return self
        def __exit__(self, *a): return False

    import urllib.request as ur
    monkeypatch.setenv("EPL_ACC_CODE_API", "http://ben-cong-no/acc-codes")
    monkeypatch.setattr(ur, "urlopen", lambda req, timeout=5: _Tra(
        {"data": [{"code": "6421", "name": "Chi phí nhiên liệu"}, "6422", {"id": "5111", "label": "Doanh thu vận tải"}]}))
    g = _client().get("/api/acc-codes", headers=API_TEST_HEADERS).json()
    assert g["source"] == "remote"
    assert g["data"] == [{"code": "6421", "name": "Chi phí nhiên liệu"},
                         {"code": "6422", "name": "6422"},
                         {"code": "5111", "name": "Doanh thu vận tải"}]
