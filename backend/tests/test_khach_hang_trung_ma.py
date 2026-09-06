"""Tao khach hang voi ma da ton tai phai bao 409, khong phai 500.

Truoc day `create_customer` di thang tu `data.get("id")` xuong `db.add()` ->
`db.commit()`. Khoa chinh trung lam SQLAlchemy nem IntegrityError, FastAPI
tra ve 500 Internal Server Error, va nguoi dung nhan mot "loi may chu" cho
mot viec ho tu sua duoc trong ba giay: doi ma khac.

Ma trung khong phai chuyen hiem. Giao dien tung de xuat ma bang cach dem SO
LUONG khach roi cong mot, nen chi can xoa mot khach o giua la ma de xuat
trung ngay voi mot khach dang co.
"""


def test_ma_trung_tra_ve_409_va_noi_ro_ma_nao(app_client):
    client, _, _ = app_client

    dau = client.post("/api/customers", json={"id": "CUS-TRUNG", "name": "Khách A"})
    assert dau.status_code in (200, 201), dau.text

    lai = client.post("/api/customers", json={"id": "CUS-TRUNG", "name": "Khách B"})
    assert lai.status_code == 409, lai.text
    than = lai.json()
    chi_tiet = str(than.get("detail") or than.get("error") or than)
    assert "CUS-TRUNG" in chi_tiet, chi_tiet


def test_lan_hai_khong_ghi_de_ten_cua_khach_dang_co(app_client):
    """409 phai la TU CHOI, khong phai ghi de am tham."""
    client, _, _ = app_client
    client.post("/api/customers", json={"id": "CUS-GIU", "name": "Tên gốc"})
    client.post("/api/customers", json={"id": "CUS-GIU", "name": "Tên đè lên"})

    ds = client.get("/api/customers").json()
    ten = [k["name"] for k in ds if k["id"] == "CUS-GIU"]
    assert ten == ["Tên gốc"], ten


def test_thieu_ma_van_la_400(app_client):
    """Nhanh 400 cu khong duoc bi nhanh 409 moi lam hong."""
    client, _, _ = app_client
    assert client.post("/api/customers", json={"name": "Không mã"}).status_code == 400
