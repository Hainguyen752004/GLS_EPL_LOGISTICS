# -*- coding: utf-8 -*-
"""`GET /api/acc-codes` nối API THẬT của bên công nợ (Golden SME).

Anh Khang cấp: `GET {gốc}/api/v1/common/country-accounts?tryAutoId=11&onlyActive=true`,
Bearer JWT, gói `{"Success", "Code", "Message", "Result": [{AccCode, AccName,
AccDescription, AccParentId, AccAccountWrite, AccIsActive, ...}]}` — ~500 tài
khoản kế toán Lào, 4 cấp, 405 tài khoản được hạch toán.

Bài kiểm khoá: dựng đúng URL (gốc → đường + tryAutoId + onlyActive), gửi Bearer,
chuẩn hoá về `{code, name, description, parent, postable}`, `Success:false` là
lỗi chứ không phải danh mục rỗng, và bộ nhớ 10 phút trả `cached`.
"""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import API_TEST_HEADERS


def _client():
    from routes.fleet_routes import router
    app = FastAPI()
    app.include_router(router)

    @app.middleware("http")
    async def principal(request, call_next):
        request.state.principal = "nguoi-kiem"
        return await call_next(request)

    return TestClient(app)


class _Tra:
    def __init__(self, than): self._t = json.dumps(than).encode("utf-8")
    def read(self): return self._t
    def __enter__(self): return self
    def __exit__(self, *a): return False


GOI_THAT = {"Success": True, "Code": 200, "Message": "OK", "Result": [
    {"TryAutoId": 11, "AccCode": "10", "AccParentId": None, "AccName": "ເງິນສົດ", "AccDescription": "Tiền mặt",
     "AccAccountWrite": 0, "AccIsActive": True},
    {"TryAutoId": 11, "AccCode": "1011", "AccParentId": 101, "AccName": "ເງິນສົດເປັນເງິນກິບ",
     "AccDescription": "Tiền mặt trong quỹ - LAK", "AccAccountWrite": 1, "AccIsActive": True},
    {"TryAutoId": 11, "AccCode": "", "AccName": "rác"},
]}


def _mock(monkeypatch, goi, ghi_nhan):
    import routes.fleet_routes as mod
    import urllib.request as ur
    mod._BO_NHO_ACC_CODE.update({"khoa": None, "luc": 0.0, "goi": None})

    def _urlopen(req, timeout=15):
        ghi_nhan.append((req.full_url, dict(req.header_items())))
        return _Tra(goi)
    monkeypatch.setattr(ur, "urlopen", _urlopen)


def test_dung_url_bearer_va_chuan_hoa_goi_golden_sme(monkeypatch):
    monkeypatch.setenv("EPL_ACC_CODE_API", "https://demo-lao-api.example.invalid")
    monkeypatch.setenv("EPL_ACC_CODE_TOKEN", "jwt-kiem")
    monkeypatch.setenv("EPL_ACC_CODE_COUNTRY", "11")
    goi_di = []
    _mock(monkeypatch, GOI_THAT, goi_di)
    g = _client().get("/api/acc-codes", headers=API_TEST_HEADERS).json()
    assert g["source"] == "remote" and g["count"] == 2
    url, dau = goi_di[0]
    assert url.startswith("https://demo-lao-api.example.invalid/api/v1/common/country-accounts?")
    assert "tryAutoId=11" in url and "onlyActive=true" in url
    assert {k.lower(): v for k, v in dau.items()}["authorization"] == "Bearer jwt-kiem"
    assert g["data"][0] == {"code": "10", "name": "ເງິນສົດ", "description": "Tiền mặt",
                            "parent": None, "postable": False, "active": True}
    assert g["data"][1]["code"] == "1011" and g["data"][1]["parent"] == "101" and g["data"][1]["postable"] is True


def test_lan_hai_lay_tu_bo_nho(monkeypatch):
    monkeypatch.setenv("EPL_ACC_CODE_API", "https://demo-lao-api.example.invalid")
    goi_di = []
    _mock(monkeypatch, GOI_THAT, goi_di)
    c = _client()
    assert c.get("/api/acc-codes", headers=API_TEST_HEADERS).json()["source"] == "remote"
    g = c.get("/api/acc-codes", headers=API_TEST_HEADERS).json()
    assert g["source"] == "cached" and g["count"] == 2 and len(goi_di) == 1
    g = c.get("/api/acc-codes?refresh=true", headers=API_TEST_HEADERS).json()
    assert g["source"] == "remote" and len(goi_di) == 2


def test_success_false_la_loi_khong_phai_danh_muc_rong(monkeypatch):
    monkeypatch.setenv("EPL_ACC_CODE_API", "https://demo-lao-api.example.invalid")
    _mock(monkeypatch, {"Success": False, "Code": 401, "Message": "Unauthorized", "Result": None}, [])
    g = _client().get("/api/acc-codes", headers=API_TEST_HEADERS).json()
    assert g["source"] == "error" and g["data"] == [] and "Unauthorized" in g["message"]
