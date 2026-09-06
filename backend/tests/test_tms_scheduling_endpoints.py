"""Bon endpoint xep lich chua co mot dau vet nao trong bo test.

Doi chieu 172 endpoint cua backend voi noi dung cac tep test cho ra 10 duong
khong tim thay dau vet. Bon duong duoi day thuoc nhom xep lich, va chung ghi
truc tiep vao bang `driver_shifts` — thu nuoi ca man lich tai xe lan phep
kiem trung lich luc dieu xe:

    POST   /api/tms/scheduling/driver-shifts/weekly-schedule
    PUT    /api/tms/scheduling/driver-shifts/{shift_id}
    DELETE /api/tms/scheduling/driver-shifts/{shift_id}
    GET    /api/tms/scheduling/vehicle-availability

Bai kiem nay di qua HTTP that chu khong goi thang service, vi phan chua duoc
phu chinh la TANG ROUTE: `_scheduling_command` bat IntegrityError doi thanh
409, va `raise_http` doi DomainError thanh ma trang thai. Goi thang service
thi hai lop do khong chay.
"""
import datetime as dt

BASE = "/api/tms/scheduling"


def _tai_xe(client, ma="DRV-SCHED-1"):
    r = client.post(
        "/api/drivers",
        json={"id": ma, "name": "Tai xe lich", "status": "Ranh (San sang)"},
    )
    assert r.status_code in (200, 201), r.text
    return ma


def _tuan_toi():
    """Mot tuan tron ven trong tuong lai, de khong dung lich cu trong CSDL."""
    hom_nay = dt.date.today()
    dau = hom_nay + dt.timedelta(days=(7 - hom_nay.weekday()))
    return dau, dau + dt.timedelta(days=6)


def _liet_ke(client, dau, cuoi, ma=None):
    r = client.get(
        BASE + "/driver-shifts",
        params={"start": dau.isoformat(), "end": cuoi.isoformat()},
    )
    assert r.status_code == 200, r.text
    rows = r.json()["data"]
    return [c for c in rows if ma is None or c.get("driver_id") == ma]


# --- weekly-schedule ---------------------------------------------------


def test_lich_tuan_tao_dung_so_ca_theo_thu_da_chon(app_client):
    client, _, _ = app_client
    ma = _tai_xe(client)
    dau, cuoi = _tuan_toi()

    r = client.post(
        BASE + "/driver-shifts/weekly-schedule",
        json={
            "driver_id": ma,
            "weekdays": [0, 2, 4],  # thu Hai, thu Tu, thu Sau
            "effective_start": dau.isoformat(),
            "effective_end": cuoi.isoformat(),
            "start_time": "06:00",
            "end_time": "14:00",
            "shift_type": "morning",
        },
    )
    assert r.status_code in (200, 201), r.text

    # Ba thu trong dung mot tuan = ba ca, khong nhieu hon.
    ca = _liet_ke(client, dau, cuoi + dt.timedelta(days=1), ma)
    assert len(ca) == 3, ca


def test_lap_lai_cung_mot_tuan_khong_nhan_doi_so_ca(app_client):
    """Ma ban ghi la `WEEKLY-<tai xe>-<ngay>-...`, nen goi hai lan phai ghi de
    chu khong tao them. Bam nut hai lan la chuyen binh thuong."""
    client, _, _ = app_client
    ma = _tai_xe(client, "DRV-SCHED-2")
    dau, cuoi = _tuan_toi()
    than = {
        "driver_id": ma,
        "weekdays": [1, 3],
        "effective_start": dau.isoformat(),
        "effective_end": cuoi.isoformat(),
        "start_time": "06:00",
        "end_time": "14:00",
        "shift_type": "morning",
    }
    for _ in range(2):
        r = client.post(BASE + "/driver-shifts/weekly-schedule", json=than)
        assert r.status_code in (200, 201), r.text

    ca = _liet_ke(client, dau, cuoi + dt.timedelta(days=1), ma)
    assert len(ca) == 2, ca


def test_ca_qua_nua_dem_ket_thuc_sang_ngay_hom_sau(app_client):
    """`end_time <= start_time` thi service tu dat end_day_offset = 1. Neu
    khong, ca dem 22:00-06:00 se co gio ket thuc TRUOC gio bat dau."""
    client, _, _ = app_client
    ma = _tai_xe(client, "DRV-SCHED-3")
    dau, cuoi = _tuan_toi()
    r = client.post(
        BASE + "/driver-shifts/weekly-schedule",
        json={
            "driver_id": ma,
            "weekdays": [0],
            "effective_start": dau.isoformat(),
            "effective_end": cuoi.isoformat(),
            "start_time": "22:00",
            "end_time": "06:00",
            "shift_type": "night",
        },
    )
    assert r.status_code in (200, 201), r.text

    ca = _liet_ke(client, dau, cuoi + dt.timedelta(days=2), ma)
    assert len(ca) == 1, ca
    assert ca[0]["shift_end"] > ca[0]["shift_start"], ca[0]


def test_lich_tuan_tu_choi_du_lieu_sai(app_client):
    client, _, _ = app_client
    ma = _tai_xe(client, "DRV-SCHED-4")
    dau, cuoi = _tuan_toi()
    goc = {
        "driver_id": ma,
        "weekdays": [0],
        "effective_start": dau.isoformat(),
        "effective_end": cuoi.isoformat(),
        "start_time": "06:00",
        "end_time": "14:00",
    }

    def gui(**doi):
        return client.post(
            BASE + "/driver-shifts/weekly-schedule", json={**goc, **doi}
        )

    assert gui(driver_id="KHONG-CO-AI").status_code == 404
    assert gui(weekdays=[]).status_code == 422
    assert gui(weekdays=[9]).status_code == 422
    assert gui(
        effective_start=cuoi.isoformat(), effective_end=dau.isoformat()
    ).status_code == 422
    assert gui(
        effective_end=(dau + dt.timedelta(days=400)).isoformat()
    ).status_code == 422
    assert gui(start_time="khong-phai-gio").status_code == 422
    assert gui(shift_type="ca-tu-bia").status_code == 422
    assert gui(timezone_offset_minutes=9999).status_code == 422


# --- PUT / DELETE mot ca -----------------------------------------------


def test_sua_va_huy_mot_ca(app_client):
    client, _, _ = app_client
    ma = _tai_xe(client, "DRV-SCHED-5")
    dau, _ = _tuan_toi()
    bd = dt.datetime.combine(dau, dt.time(6, 0), tzinfo=dt.timezone.utc)

    tao = client.post(
        BASE + "/driver-shifts",
        json={
            "id": "SHIFT-SUA-1",
            "driver_id": ma,
            "shift_type": "morning",
            "availability_kind": "work",
            "shift_start": bd.isoformat(),
            "shift_end": (bd + dt.timedelta(hours=8)).isoformat(),
        },
    )
    assert tao.status_code in (200, 201), tao.text

    sua = client.put(
        BASE + "/driver-shifts/SHIFT-SUA-1",
        json={
            "driver_id": ma,
            "shift_type": "afternoon",
            "availability_kind": "work",
            "shift_start": (bd + dt.timedelta(hours=8)).isoformat(),
            "shift_end": (bd + dt.timedelta(hours=16)).isoformat(),
        },
    )
    assert sua.status_code == 200, sua.text

    ca = [
        c
        for c in _liet_ke(client, dau, dau + dt.timedelta(days=2))
        if c["id"] == "SHIFT-SUA-1"
    ]
    # Sua phai GHI DE dung ban ghi do, khong tao ban thu hai.
    assert len(ca) == 1, ca
    assert ca[0]["shift_type"] == "afternoon", ca[0]

    xoa = client.delete(BASE + "/driver-shifts/SHIFT-SUA-1")
    assert xoa.status_code == 200, xoa.text
    con = [
        c
        for c in _liet_ke(client, dau, dau + dt.timedelta(days=2))
        if c["id"] == "SHIFT-SUA-1"
    ]
    assert con == [], con


def test_huy_ca_khong_ton_tai_thi_bao_404(app_client):
    client, _, _ = app_client
    r = client.delete(BASE + "/driver-shifts/SHIFT-KHONG-CO")
    assert r.status_code == 404, r.text


# --- vehicle-availability ----------------------------------------------


def test_lich_ranh_cua_xe_tra_ve_dung_phong_bi(app_client):
    client, _, _ = app_client
    r = client.post(
        "/api/vehicles",
        json={"id": "VEH-AVAIL-1", "type": "Xe tai", "status": "San sang"},
    )
    assert r.status_code in (200, 201), r.text

    dau, cuoi = _tuan_toi()
    r = client.get(
        BASE + "/vehicle-availability",
        params={"start": dau.isoformat(), "end": cuoi.isoformat()},
    )
    assert r.status_code == 200, r.text
    than = r.json()
    assert "data" in than and "message" in than, than


def test_lich_ranh_tu_choi_khoang_ngay_sai(app_client):
    client, _, _ = app_client
    r = client.get(
        BASE + "/vehicle-availability",
        params={"start": "khong-phai-ngay", "end": "cung-vay"},
    )
    # Phai la loi cua nguoi goi, khong duoc la 500.
    assert r.status_code in (400, 422), (r.status_code, r.text)


def test_thieu_tham_so_thi_bao_422_chu_khong_no(app_client):
    client, _, _ = app_client
    assert client.get(BASE + "/vehicle-availability").status_code == 422
    assert client.get(BASE + "/driver-shifts").status_code == 422
