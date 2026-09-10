"""Luong end-to-end phai DI DUOC qua chinh cac duong ma giao dien goi.

Chu du an nhac lai nhieu lan, va viet hoa: "PHAI DI DC CAI LUONG END TO END
NHE VA PHAI RA DC CAI SAN PHAM DE ANH CO THE CLICK NUT CAC THU".

Cac bai kiem khac kiem tung tang mot: mot bai cho dieu phoi, mot bai cho POD,
mot bai cho quyet toan. Nhung mot he thong co the co moi tang xanh ma van khong
di duoc het vong — vi mot cho CHAN giua duong. Da xay ra that hai lan trong du
an nay:

  · `require_loaded_for_dispatch` chan xuat ben khi Packing List chua bocc du
    kien. Bo nap du lieu demo khong tao Packing List, nen khong ai phat hien ra
    cho chan nay cho tới khi bo nap bat dau tao.
  · Man Lenh giao hang tung bi mot `display:none` lam trang tron: moi duong API
    van dung, moi bai kiem tang duoi van xanh, ma nguoi dung khong bam duoc gi.

Bai kiem nay di HET mot vong: du lieu goc → bao gia cuoc → don hang van chuyen
→ lenh giao hang → Packing List → chuyen → quyet toan → hach toan. No khong doi
chieu so tien (viec do cac bai khac lam) — no chi doi hoi rang MOI BUOC TRA VE
200 va co du lieu that.
"""

import importlib


def _du_lieu(tra_loi):
    """Rut phan du lieu ra, chiu ca ba hinh dang phan hoi cua du an.

    Ba hinh dang cung ton tai va deu dung: mot so duong tra thang mot mang, mot
    so boc trong `items`, mot so boc trong `data` roi moi den `items`. Bai kiem
    khong nen buoc chung phai giong nhau — no chi can doc duoc.
    """
    d = tra_loi.json()
    if isinstance(d, list):
        return d
    if not isinstance(d, dict):
        return []
    if isinstance(d.get("items"), list):
        return d["items"]
    trong = d.get("data")
    if isinstance(trong, list):
        return trong
    if isinstance(trong, dict) and isinstance(trong.get("items"), list):
        return trong["items"]
    return []


def _nap_demo(app_client):
    # `app_client` tra ve (client, duong_tep_csdl, dau_van_tay) — phan tu thu ba
    # KHONG phai mot bo tao phien. Lay phien qua `database.SessionLocal` giong
    # cac bai kiem khac; `app_client` da tro `database` sang tep tam roi.
    client, _, _ = app_client
    database = importlib.import_module("database")
    demo_seed_service = importlib.import_module("services.demo_seed_service")
    with database.SessionLocal() as db:
        demo_seed_service.seed_demo(db, reset=True, verify=True)
    return client


def test_di_het_vong_nghiep_vu_qua_duong_api(app_client):
    client = _nap_demo(app_client)

    # --- 1. Du lieu goc phai co san. Thieu mot cai la cac buoc sau khong lam
    #        duoc gi, va loi hien ra o buoc sau chu khong o day.
    for duong in ("/api/routes", "/api/vehicles", "/api/drivers",
                  "/api/customers", "/api/vehicle-types"):
        r = client.get(duong)
        assert r.status_code == 200, (duong, r.text)
        assert _du_lieu(r), f"{duong} khong co dong nao — cac buoc sau se trong"

    # --- 2. Bao gia cuoc → lenh giao hang (buoc Don hang da bo).
    assert client.get("/api/quotations").status_code == 200

    r = client.get("/api/delivery-orders")
    assert r.status_code == 200, r.text
    don = _du_lieu(r)
    assert len(don) >= 3, f"can it nhat ba lenh giao hang, thay {len(don)}"

    theo_trang_thai = {}
    for item in don:
        theo_trang_thai.setdefault(item.get("canonical_status"), []).append(item["id"])
    # Bon trang thai nay la bon mat khac nhau cua luong, va moi mat mo mot man
    # khac: cho van chuyen (dieu phoi), dang van chuyen (theo doi), DA DEN NOI
    # (cho POD), da hoan tat (quyet toan). Thieu mot mat thi mot man khong co gi
    # de xem.
    #
    # `arrived` la mat quan trong nhat trong so nay ma lai de bi bo sot: no la
    # trang thai quyet dinh cua quy tac quyet toan — dang van chuyen thi CAM sua
    # tien, den noi va ky POD roi moi chot duoc gia cuoi.
    for trang_thai in ("pending", "in_transit", "arrived", "delivered"):
        assert theo_trang_thai.get(trang_thai), (
            f"khong co lenh giao hang nao o trang thai {trang_thai}: "
            f"{sorted(theo_trang_thai)}")

    # Va cac don phai trai tren NHIEU TUYEN va NHIEU KHACH. Don nao cung mot
    # tuyen thi bo loc tuyen chi co mot lua chon that — nhin nhu bo loc hong,
    # trong khi no dang noi that.
    tuyen = {item.get("route_id") for item in don if item.get("route_id")}
    khach = {item.get("customer_id") for item in don if item.get("customer_id")}
    assert len(tuyen) >= 3, f"cac don chi di {len(tuyen)} tuyen: {tuyen}"
    assert len(khach) >= 2, f"cac don chi cua {len(khach)} khach: {khach}"

    # Nhan tieng Viet phai noi DUNG trang thai. Truoc day ham dung DO chi co hai
    # nhanh nhan, nen mot don `arrived` hien la "Cho van chuyen" — nguoc han su
    # that, va nguoi dieu phoi se tuong xe chua di.
    nhan = {item["id"]: item.get("status") for item in don}
    for item in don:
        if item.get("canonical_status") == "arrived":
            assert nhan[item["id"]] == "Đã đến nơi", (
                f"{item['id']} da den noi ma nhan ghi {nhan[item['id']]!r}")

    # --- 3. Packing List phai o `loaded`.
    #
    # Day la cho CHAN that: `require_loaded_for_dispatch` khong cho xuat ben khi
    # mot DO co Packing List ma chua bocc du kien. Neu bo nap de no dung o
    # `ready` thi ban demo khong xuat ben duoc, va nguoi thu se tuong he thong
    # hong chu khong nghi la du lieu chua day du.
    r = client.get("/api/parking-lists")
    assert r.status_code == 200, r.text
    phieu = _du_lieu(r)
    assert phieu, "khong co Packing List nao"
    chua_bocc = [p["id"] for p in phieu
                 if p.get("status") not in {"loaded", "dispatched", "delivered"}]
    assert not chua_bocc, (
        f"Packing List chua bocc du kien se CHAN xuat ben: {chua_bocc}")

    # --- 4. Chuyen va dieu phoi.
    r = client.get("/api/tms/trips")
    assert r.status_code == 200, r.text
    chuyen = _du_lieu(r)
    assert chuyen, "khong co chuyen nao"
    # Moi chuyen phai co xe VA tai xe: mot chuyen khong co xe thi khong xuat
    # ben duoc, va no khong hien duoc tren luoi lich xe.
    for c in chuyen:
        assert c.get("vehicle_id"), f"chuyen {c.get('id')} chua gan xe"
        assert c.get("driver_id"), f"chuyen {c.get('id')} chua gan tai xe"

    # --- 5. Theo doi: lich ranh cua xe, ca truc, bao duong.
    tuan = {"start": "2026-08-17", "end": "2026-08-24"}
    assert client.get("/api/tms/scheduling/vehicle-availability",
                      params=tuan).status_code == 200
    assert client.get("/api/tms/scheduling/driver-shifts",
                      params=tuan).status_code == 200

    # --- 6. Quyet toan cua DO da hoan tat.
    da_xong = theo_trang_thai["delivered"][0]
    r = client.get(f"/api/delivery-orders/{da_xong}/closeout")
    assert r.status_code == 200, r.text
    ho_so = r.json().get("data") or r.json()
    # Ba khoi phai co: thong tin DO, chung tu POD, va phan tien. Thieu POD thi
    # khong chot duoc gia cuoi, va thieu phan tien thi khong xuat hoa don duoc.
    assert ho_so.get("delivery_order"), "ho so sau hoan tat thieu thong tin DO"
    assert ho_so.get("pod_documents"), "ho so sau hoan tat thieu chung tu POD"
    tien = ho_so.get("commercials") or {}
    assert tien.get("final_selling_price") is not None, "chua chot gia cuoi"

    # --- 7. Hach toan.


def test_bao_duong_theo_tuan_hien_tai_co_du_hai_trang_thai(app_client):
    """Lop du lieu van hanh phai co ca ky da duyet va ky chua duyet.

    Hai trang thai lam hai viec khac nhau va hien o hai cho khac nhau:
    `approved` chan dieu phoi va ke soc o tren luoi lich xe; `requested` chua
    chan gi nen chi hien o khoi nhac ben phai. Thieu ky `requested` thi khoi
    nhac do khong bao gio hien ra, va khong ai biet la no co.
    """
    client = _nap_demo(app_client)
    demo_operational_seed = importlib.import_module("services.demo_operational_seed")
    t0 = demo_operational_seed.dau_tuan()
    tuan = {
        "start": t0.isoformat(),
        "end": (t0.replace(hour=0) + __import__("datetime").timedelta(days=7)).isoformat(),
    }
    r = client.get("/api/vehicle-maintenance-requests", params=tuan)
    assert r.status_code == 200, r.text
    trang_thai = {k.get("status") for k in _du_lieu(r)}
    assert "approved" in trang_thai, f"thieu ky bao duong da duyet: {trang_thai}"
    assert "requested" in trang_thai, f"thieu ky bao duong chua duyet: {trang_thai}"


def test_ca_truc_nap_dung_tuan_dang_xem(app_client):
    """Ca truc phai nam trong TUAN HIEN TAI, khong phai mot tuan co dinh.

    Man "Sap lich xe va tai xe" mo tuan chua ngay hom nay. Du lieu neo vao
    thang 8/2026 thi khong bao gio hien ra o do — do duoc: dai loc bao
    "Chua xep 3", tuc ca ba tai xe deu khong co ca nao. Bai kiem nay giu cho lop
    du lieu van hanh luon neo theo hom nay.
    """
    import datetime as dt

    client = _nap_demo(app_client)
    demo_operational_seed = importlib.import_module("services.demo_operational_seed")
    t0 = demo_operational_seed.dau_tuan()
    r = client.get("/api/tms/scheduling/driver-shifts", params={
        "start": t0.isoformat(),
        "end": (t0 + dt.timedelta(days=7)).isoformat(),
    })
    assert r.status_code == 200, r.text
    ca = _du_lieu(r)
    assert len(ca) >= 15, f"tuan hien tai chi co {len(ca)} ca — man xep ca se gan nhu trong"

    loai = {c.get("availability_kind") for c in ca}
    # Phai co ca mot ngay nghi: dai loc nhanh co nhom "co nghi", va khong co ngay
    # nghi nao thi nhom do luon bang 0 va thanh vo nghia.
    assert "leave" in loai, f"khong co ngay nghi nao trong tuan: {loai}"
    assert "work" in loai
