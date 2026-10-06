# -*- coding: utf-8 -*-
"""Thử BÚT TOÁN CHỜ GỬI (chủ dự án 01/10/2026) — khoản không qua tiền mà sổ kế toán phải ghi, giữ ở trang điều xe chờ hệ anh
Tune có API bút toán tổng hợp.

    python kiem/thu_but_toan_cho.py                     (mặc định 06/10: trong tiến trình, bản sao _d7, cuối ROLLBACK)
    python kiem/thu_but_toan_cho.py http://127.0.0.1:8014  (cách cũ: gọi một máy thử đang chạy — lập rồi xoá phiếu thử)

Chạy mặc định (06/10): FastAPI TestClient trên bản sao _d7, MỌI THỨ trong một giao dịch ngoài (phiên chạy savepoint), cuối ROLLBACK
— không ghi gì vào d7, không cần máy 8014; mọi lời gọi mạng ra ngoài bị chặn (urllib), không chạy sự kiện khởi động.

Lúc KHOÁ PHIẾU:
  · xe thuê: Nợ 621 chi phí vận chuyển / Có 4022 phải trả chủ xe, bằng TIỀN THUÊ (theo tiền thuê), đối tượng chủ xe;
  · mỗi dòng chi ghi nợ nhà cung cấp (định khoản …/4021): Nợ 625 · 614 (xe thuê 4022) / Có 4021 — dầu trạm VN ghi nợ, chipping
    (trả theo đợt), lốp nợ cửa hàng. Tiền theo NGUYÊN TỆ của dòng (06/10, G12: dầu trạm VN ghi VND) kèm tỷ giá khoá trên phiếu
    (`ty_gia`) và số quy Kíp (`tien_lak`); dòng Kíp như cũ. KHÔNG gồm: khoản QUỸ TRẢ NGAY mục V (vào chi phí qua
    phiếu chi bên kế toán), tiền mặt tạm ứng, trả cùng lương, chủ xe tự trả.
Lúc MỞ KHOÁ: huỷ bút toán chưa gửi; khoá lại → sống lại đúng một bản theo số mới. Xoá phiếu → huỷ.
Đường đọc GET /api/but-toan-cho: chỉ KT Thu/Chi VC, KT Chi phí VC, Sếp (bảng 12 vai). Gói phiếu mang khối but_toan_cho chỉ với
ba vai đó. Giao ước service (ghi · huy · rut · danh_sach) kiểm phần không cần DB: khoá nguồn, dạng dòng.

Không gọi hệ anh Tune: phiếu thử không có tiền mặt tạm ứng, không ghi sổ mục chi. Lập rồi xoá hai phiếu thử THU-BTC-A/B.
"""
import json
import os
import sys
import urllib.error
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")          # trống = trong tiến trình (TestClient, _d7, ROLLBACK)
if GOC.endswith((":8010", ":8020", ":8001")):
    sys.exit("Không chạy bài này trên máy thật.")
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app")
C = None                                   # TestClient khi chạy trong tiến trình
if not GOC:
    URL = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
    if "_d7" not in URL.rsplit("/", 1)[-1]:
        sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
    os.environ["DATABASE_URL"] = URL
    os.environ.pop("QLSX_GUI_BUT_TOAN", None)                           # cờ gửi tắt: bút toán chỉ nằm chờ gửi
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    def _cam_mang(*a, **k):
        raise OSError("bài kiểm không được gọi mạng ra ngoài")
    urllib.request.urlopen = _cam_mang
TK, LOI = {}, []
SO_A, SO_B = "THU-BTC-A/EPL", "THU-BTC-B/EPL"
VAI = {"admin": "admin", "ketoan": "acct", "ketoancp": "expacct", "khonl": "fuel", "khotb": "depot", "khopt": "parts",
       "totsua": "repair", "quyvc": "treasury", "quytb": "cash", "doanhthu": "rev", "thabok": "yard", "tx01": "driver"}
XEM = ("admin", "ketoan", "ketoancp")


def goi(duong, body=None, u=None, method=None):
    if C is not None:                      # trong tiến trình: TestClient, cùng phiên trong giao dịch ROLLBACK
        r = C.request(method or ("POST" if body is not None else "GET"), duong, json=body,
                      headers={"Authorization": "Bearer " + TK[u]} if u else {})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}
    r = urllib.request.Request(GOC + duong, data=json.dumps(body).encode() if body is not None else None,
                               method=method or ("POST" if body is not None else "GET"),
                               headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TK[u]} if u else {})})
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}


def dung(dk, buoc, them=""):
    print("  %s %s %s" % ("✓" if dk else "SAI", buoc, them))
    sys.stdout.flush()
    if not dk:
        LOI.append(buoc)


def phai(s, mong, buoc, g=None):
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, json.dumps(g, ensure_ascii=False)[:400]))
    print("  ✓ %s %s" % (buoc, s))


def don():
    for so in (SO_A, SO_B):
        s, ds = goi("/api/trips?q=%s" % so.split("/")[0], u="admin")
        for p in [x for x in (ds or []) if x["doc_no"] == so]:
            goi("/api/trips/%s/mo-khoa" % p["id"], {}, u="admin")
            s, g = goi("/api/trips/" + p["id"], u="admin", method="DELETE")
            print("  · dọn phiếu thử %s → %s" % (so, s))


def giao_uoc():
    """Phần giao ước không cần DB: khoá nguồn, dạng dòng (services/but_toan_cho.py)."""
    sys.path.insert(0, APP)
    from services import but_toan_cho as B
    bat = lambda f: (lambda: (f(), False))
    for ten, f in (("nguồn rỗng", lambda: B._khoa("", "x")), ("nguồn quá 16 ký tự", lambda: B._khoa("x" * 17, "x")),
                   ("mã nguồn quá 80 ký tự", lambda: B._khoa("tat_toan", "x" * 81)),
                   ("dòng thiếu vế Có", lambda: B._chuan_dong([{"no": "625", "tien": 1, "ccy": "LAK"}])),
                   ("Nợ = Có", lambda: B._chuan_dong([{"no": "625", "co": "625", "tien": 1, "ccy": "LAK"}])),
                   ("tiền âm", lambda: B._chuan_dong([{"no": "625", "co": "1601", "tien": -5, "ccy": "LAK"}])),
                   ("tiền lạ XYZ", lambda: B._chuan_dong([{"no": "625", "co": "1601", "tien": 5, "ccy": "XYZ"}])),
                   ("đối tượng thiếu ref_id", lambda: B._chuan_dong([{"no": "625", "co": "1601", "tien": 5, "ccy": "LAK",
                                                                       "doi_tuong": {"loai": "tai_xe"}}]))):
        try:
            f()
            dung(False, "giao ước: %s → ValueError" % ten)
        except ValueError:
            dung(True, "giao ước: %s → ValueError" % ten)
    del bat
    # khuôn agent A dùng lúc chốt tất toán: ma_nguon "<driver_id>:<YYYY-MM>:<id bản chốt>"
    n, m = B._khoa("tat_toan", "0123456789ab:2026-09:ba9876543210")
    dong = B._chuan_dong([{"no": "625", "co": "1601", "tien": 1234567.4, "ccy": "LAK", "doi_tuong": {"loai": "tai_xe", "ref_id": "x"},
                           "dien_giai": "quyết toán"}, {"no": "625", "co": "1601", "tien": 0, "ccy": "LAK"}])
    dung(len(dong) == 1 and dong[0]["tien"] == 1234567 and dong[0]["doi_tuong"] == {"loai": "tai_xe", "ref_id": "x"}
         and "canh_bao_tk" not in dong[0], "giao ước: khuôn tất toán nhận được, LAK làm tròn đồng, dòng tiền 0 bỏ qua")
    d2 = B._chuan_dong([{"no": "70", "co": "4022", "tien": 10.556, "ccy": "USD"}])
    dung(d2[0]["tien"] == 10.56 and d2[0].get("canh_bao_tk"), "giao ước: USD hai số lẻ; tài khoản NHÓM (70) mang cảnh báo",
         d2[0].get("canh_bao_tk"))


def lap(so, cong_ty, xe, tx, kh, ncc, tram):
    """Sếp lập phiếu (đặt được cả giá) — dòng chi đủ các cách trả."""
    dong = [
        # dầu đổ trạm VN GHI NỢ → …/4021 (có trong bút toán)
        {"section": "fuel", "item_key": "diesel", "qty": 100, "unit_price": 25000, "currency": "VND", "place_id": tram, "ghi_no": True},
        # chipping Lào: mặc định ghi nợ NCC trả theo đợt → …/4021 (có)
        {"section": "travel", "item_key": "x_chip_lao", "qty": 1, "unit_price": 150000, "currency": "LAK"},
        # tiền ăn: tiền mặt tài xế cầm đi (tạm ứng) → không có — giá 0 để phiếu không sinh tạm ứng bên kế toán
        {"section": "travel", "item_key": "x_food", "qty": 1, "unit_price": 0, "currency": "LAK"},
        # sửa ngoài garage, quỹ trả ngay → …/4021 nhưng KHÔNG vào bút toán (đi phiếu chi bên kế toán)
        {"section": "repair", "item_name": "thử BTC: garage", "qty": 1, "unit_price": 200000, "currency": "LAK", "source": "mua"},
    ]
    if "x_tire" in ncc:
        # lốp: khoản mục nhà cung cấp theo dõi nợ, không ghi rõ NCC → nợ cửa hàng lốp trả theo đợt → …/4021 (có)
        dong.append({"section": "repair", "item_key": "x_tire", "qty": 2, "unit_price": 1000000, "currency": "LAK", "source": "mua"})
    if cong_ty == "joint":
        # chủ xe tự trả → không phải tiền EPL → không có
        dong.append({"section": "travel", "item_key": "x_chip_vn", "qty": 1, "unit_price": 99000, "currency": "LAK", "paid_by_epl": False})
    else:
        # tiền nước trả cùng lương (625/4201) → không qua NCC → không có
        dong.append({"section": "travel", "item_key": "x_water", "qty": 1, "unit_price": 60000, "currency": "LAK"})
    body = {"doc_no": so, "kind": "giao", "company": cong_ty, "vehicle_id": xe["id"], "driver_id": tx["id"], "customer_id": kh["id"],
            "doc_date": "2026-09-27", "out_date": "2026-09-27", "weight_origin": 40, "odo_out": 1000, "price": 40, "price_ccy": "USD",
            "pod_no": "BTC-POD", "expenses": dong}
    if cong_ty == "joint":
        body.update({"hire_price": 30, "hire_ccy": "USD"})
    s, p = goi("/api/trips", body, u="admin")
    phai(s, 200, "Sếp lập phiếu thử %s (%s)" % (so, "xe thuê" if cong_ty == "joint" else "xe nhà"), p)
    s, g = goi("/api/trips/%s/transport-status" % p["id"], {"status": "arrived", "weight_dest": 40, "odo_back": 1500,
                                                           "back_date": "2026-09-28"}, u="admin")
    phai(s, 200, "Sếp báo xe tới", g)
    return p["id"]


def ty(p):
    return {"USD": p["rate_usd"], "THB": p["rate_thb"], "VND": p["rate_vnd"], "CNY": p["rate_cny"], "LAK": 1}


def mong_ncc(p):
    """Các dòng phải vào bút toán ghi nợ NCC — đọc lại từ chính phiếu: (định khoản Nợ, tiền theo NGUYÊN TỆ, tiền tệ, quy Kíp).
    06/10 (G12): dòng ngoại tệ ghi đúng nguyên tệ (VND làm tròn đồng, tiền khác hai số lẻ) — trước đây quy Kíp."""
    r = ty(p)
    ra = {}
    for e in p["expenses"]:
        if e.get("paid_by_epl") is False or not (e.get("acct_code") or "").endswith("/4021"):
            continue
        if e["section"] == "repair" and not e.get("item_key"):
            continue                                     # garage quỹ trả ngay
        ccy = (e["currency"] or "LAK").upper()
        goc = (e["qty"] or 0) * (e["unit_price"] or 0)
        ra[e["id"]] = (e["acct_code"].split("/")[0], round(goc) if ccy in ("LAK", "VND") else round(goc, 2), ccy, round(goc * r[ccy]))
    return ra


def kiem_khoa(tid, cong_ty):
    s, p = goi("/api/trips/" + tid, u="ketoan")
    s, bt = goi("/api/but-toan-cho?trip_id=" + tid, u="ketoan")
    phai(s, 200, "KT Thu/Chi đọc bút toán chờ của phiếu", bt)
    cho = {b["nguon"]: b for b in bt["ds"] if b["status"] == "cho_gui"}
    if cong_ty == "joint":
        t = cho.get("thue_xe")
        d = (t or {}).get("dong") or [{}]
        # 06/10: cùng chứng từ có thêm phí quản lý Nợ 4022 / Có 715 (phiếu thử 40 t — không quá tải nên không có dòng 4022/758;
        # bài riêng kiem/thu_phi_qua_tai_thue_xe.py kiểm đủ ba dòng)
        dung(t and len(d) == (2 if p["tinh"]["phi"] else 1) and d[0]["no"] == "621" and d[0]["co"] == "4022" and d[0]["ccy"] == p["tinh"]["hire_ccy"]
             and abs(d[0]["tien"] - p["tinh"]["tien_thue"]) < 0.005 and d[0]["doi_tuong"] == {"loai": "chu_xe", "ref_id": p["owner_id"]},
             "xe thuê: Nợ 621 / Có 4022 = tiền thuê %s %s, đối tượng chủ xe" % (p["tinh"]["tien_thue"], p["tinh"]["hire_ccy"]))
        phi = next((x for x in d if x.get("co") == "715"), None)
        dung(not p["tinh"]["phi"] or phi and phi["no"] == "4022" and abs(phi["tien"] - p["tinh"]["phi"]) < 0.005 and phi["ccy"] == d[0]["ccy"],
             "xe thuê: phí quản lý Nợ 4022 / Có 715 = %s %s (06/10)" % (p["tinh"]["phi"], p["tinh"]["hire_ccy"]))
        dung(t and t["source_ref"] == "EPLLAO-thue_xe-" + tid and abs(t["tong"] - sum(x["tien"] for x in d)) < 0.005,
             "khoá chống trùng EPLLAO-thue_xe-<id>, tổng = Σ dòng")
    else:
        dung("thue_xe" not in cho, "xe nhà: không có bút toán tiền thuê")
    n = cho.get("no_ncc")
    mong = mong_ncc(p)
    co = {x.get("ref"): (x["no"], x["tien"], x["ccy"], x["tien"] if x["ccy"] == "LAK" else x.get("tien_lak"))
          for x in (n or {}).get("dong") or []}
    r = ty(p)
    dung(n and co == mong and all(x["co"] == "4021" for x in n["dong"])
         and all(x["ccy"] == "LAK" and "ty_gia" not in x or x["ccy"] != "LAK" and x.get("ty_gia") == r[x["ccy"]] for x in n["dong"]),
         "ghi nợ NCC: đúng các dòng …/4021, Nợ %s / Có 4021, theo nguyên tệ (ngoại tệ kèm tỷ giá phiếu + quy Kíp)" % (
             "4022" if cong_ty == "joint" else "625 · 614"), "%s dòng · %s" % (len(co), sorted(co.values())))
    ten = {e["id"]: (e.get("item_key") or e.get("item_name")) for e in p["expenses"]}
    bo = [ten[i] for i in ten if i not in co]
    dung("thử BTC: garage" in bo and "x_food" in bo, "không gồm garage quỹ trả ngay, tiền mặt tạm ứng, %s" % (
        "chủ xe tự trả" if cong_ty == "joint" else "trả cùng lương"), ", ".join(str(x) for x in bo))
    tram = next((x for x in n["dong"] if x["section"] == "fuel"), None) if n else None
    dung(tram and tram["ccy"] == "VND" and tram["tien"] == 2500000 and tram.get("ty_gia") == p["rate_vnd"]
         and tram.get("tien_lak") == round(2500000 * p["rate_vnd"]) and "ccy_goc" not in tram
         and (tram.get("doi_tuong") or {}).get("loai") == "ncc",
         "dòng dầu trạm VN (G12): ghi 2.500.000 VND, tỷ giá khoá trên phiếu %s, quy Kíp %s, đối tượng nhà cung cấp" % (
             p["rate_vnd"], tram and tram.get("tien_lak")))
    return p


def trong_tien_trinh():
    """TestClient trên _d7: một kết nối, một giao dịch ngoài, phiên chạy savepoint (route commit chỉ chốt savepoint), hết request
    thì bỏ phần chưa commit (như database.get_db). Bảng mới mà d7 chưa có thì dựng TRONG giao dịch (ROLLBACK xoá luôn).
    → hàm dọn (ROLLBACK)."""
    global C
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    import models as M
    from database import get_db
    from main import app
    eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
    conn = eng.connect()
    ngoai = conn.begin()
    conn.execute(text("SET LOCAL lock_timeout = '10s'"))       # máy 8011 chạy song song: chờ khoá quá 10 giây thì hỏng, không treo
    M.Base.metadata.create_all(bind=conn, checkfirst=True)
    # bộ đếm báo cáo tự dựng bảng bằng KẾT NỐI RIÊNG (db.get_bind().connect()) — phiên ở đây gắn một Connection nên không làm
    # được: dựng (nếu thiếu) ngay trong giao dịch này rồi báo bộ đếm là đã có
    from services import dem_bao_cao as DEM
    conn.execute(text(DEM._BANG_SQL))
    if not DEM._CO_BANG:
        DEM._CO_BANG.append(True)
    import json as _j

    def _khong_dem(db, viec, theo_ngay=False, tinh_lo=None):
        # bản lưu của bộ đệm đọc / ghi bằng kết nối riêng — trong bài tính thẳng (cùng dạng JSON như bản lưu)
        kq = tinh_lo(list(range(len(viec)))) if tinh_lo is not None else [t() for _, _, t in viec]
        return [_j.loads(_j.dumps(v, default=str)) for v in kq]
    DEM.lay_nhieu = _khong_dem
    db = Session(bind=conn, join_transaction_mode="create_savepoint", autoflush=False)

    def _db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = _db
    C = TestClient(app, raise_server_exceptions=False)

    def xong():
        app.dependency_overrides.clear()
        db.close()
        ngoai.rollback()
        conn.close()
        print("đã ROLLBACK — bản sao d7 không đổi")
    return xong


def main():
    giao_uoc()
    xong = trong_tien_trinh() if not GOC else None
    try:
        chay()
    finally:
        if xong:
            xong()
    print("\n%s" % ("BÚT TOÁN CHỜ: ĐẠT" if not LOI else "BÚT TOÁN CHỜ: SAI %d chỗ:\n  - " % len(LOI) + "\n  - ".join(LOI)))
    sys.exit(1 if LOI else 0)


def chay():
    for u in VAI:
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"})
        if s != 200:
            sys.exit("Không đăng nhập được %s: %s" % (u, g))
        TK[u] = g["token"]
    don()
    s, xe = goi("/api/vehicles", u="admin"); s, tx = goi("/api/drivers", u="admin"); s, kh = goi("/api/customers", u="admin")
    s, ncc_ds = goi("/api/suppliers", u="admin"); s, diem = goi("/api/fuel-places", u="admin")
    ncc = {x.get("item_key") for x in ncc_ds if x.get("item_key")}
    tram = next(x for x in diem if x["owner_type"] == "ngoai" and x.get("supplier_id"))["id"]
    thue = next(v for v in xe if v["owner_type"] == "joint" and v["active"])
    nha = next(v for v in xe if v["owner_type"] == "EPL" and v["active"])
    taixe = [t for t in tx if t["active"]]
    A = lap(SO_A, "joint", thue, taixe[0], kh[0], ncc, tram)
    B = lap(SO_B, "EPL", nha, taixe[-1], kh[0], ncc, tram)
    try:
        print("1. Trước khi khoá: chưa có bút toán")
        s, bt = goi("/api/but-toan-cho?trip_id=" + A, u="ketoan")
        dung(s == 200 and not bt["ds"], "phiếu chưa khoá → không có bút toán chờ")

        print("2. Khoá phiếu → bút toán chờ")
        for tid in (A, B):
            s, g = goi("/api/trips/%s/khoa" % tid, {"xac_nhan": True}, u="ketoan"); phai(s, 200, "KT Thu/Chi khoá phiếu", g)
        pa = kiem_khoa(A, "joint")
        kiem_khoa(B, "EPL")

        print("3. Phân quyền — 12 vai")
        for u, vai in VAI.items():
            s, g = goi("/api/but-toan-cho", u=u)
            dung(s == (200 if u in XEM else 403), "GET /api/but-toan-cho — %-8s (%s) → %s" % (u, vai, s))
            if u == "tx01":
                continue
            s, p = goi("/api/trips/" + A, u=u)
            dung(("but_toan_cho" in p) == (u in XEM), "gói phiếu mang khối but_toan_cho — %s: %s" % (u, "but_toan_cho" in p))
        dung(goi("/api/but-toan-cho")[0] == 401, "không đăng nhập → 401")
        s, g = goi("/api/but-toan-cho?status=xyz", u="ketoan")
        dung(s == 422, "lọc trạng thái lạ → 422", s)
        s, g = goi("/api/but-toan-cho?nguon=thue_xe&status=cho_gui&thang=2026-10", u="ketoancp")
        dung(s == 200 and all(b["nguon"] == "thue_xe" and b["status"] == "cho_gui" for b in g["ds"]) and g["co_duong_gui"] is False,
             "lọc nguồn · trạng thái · tháng; chưa có đường gửi", "%d bút toán" % len(g["ds"]))

        print("4. Mở khoá → huỷ; sửa số; khoá lại → một bản theo số mới")
        s, bt0 = goi("/api/but-toan-cho?trip_id=" + A, u="ketoan")
        id_cu = {b["nguon"]: b["id"] for b in bt0["ds"]}
        s, g = goi("/api/trips/%s/mo-khoa" % A, {}, u="ketoan"); phai(s, 200, "KT Thu/Chi mở khoá (chưa có SO)", g)
        s, bt = goi("/api/but-toan-cho?trip_id=" + A, u="ketoan")
        dung(bt["ds"] and all(b["status"] == "huy" and b["huy_by"] for b in bt["ds"]), "mở khoá: mọi bút toán chưa gửi → huỷ, có người huỷ")
        chip = next(e for e in pa["expenses"] if e.get("item_key") == "x_chip_lao")
        s, g = goi("/api/trips/" + A, {"hire_price": 31}, u="ketoan", method="PUT")
        phai(s, 200, "KT Thu/Chi sửa giá thuê 31 USD/t", g)
        s, g = goi("/api/trips/" + A, {"expenses": [{"id": chip["id"], "section": "travel", "unit_price": 175000, "currency": "LAK"}]},
                   u="ketoancp", method="PUT")
        phai(s, 200, "KT Chi phí sửa đơn giá chipping 175.000 (giữ nguyên dòng)", g)
        s, g = goi("/api/trips/%s/khoa" % A, {"xac_nhan": True}, u="ketoan"); phai(s, 200, "Khoá lại", g)
        s, bt = goi("/api/but-toan-cho?trip_id=" + A, u="ketoan")
        cho = {b["nguon"]: b for b in bt["ds"] if b["status"] == "cho_gui"}
        dung(len(bt["ds"]) == len(id_cu) and {b["nguon"]: b["id"] for b in bt["ds"]} == id_cu,
             "khoá lại: cùng bản ghi (không sinh trùng), sống lại cho_gui")
        s, p = goi("/api/trips/" + A, u="ketoan")
        dung(abs(cho["thue_xe"]["dong"][0]["tien"] - p["tinh"]["tien_thue"]) < 0.005 and p["tinh"]["tien_thue"] == round(40 * 31, 2),
             "tiền thuê theo số mới: %s USD" % p["tinh"]["tien_thue"])
        dung(any(x.get("ref") == chip["id"] and x["tien"] == 175000 for x in cho["no_ncc"]["dong"]), "chipping theo số mới 175.000")

        print("5. Xoá phiếu → bút toán huỷ")
        s, g = goi("/api/trips/%s/mo-khoa" % B, {}, u="admin")
        s, g = goi("/api/trips/" + B, u="admin", method="DELETE"); phai(s, 200, "Sếp xoá phiếu thử B", g)
        s, g = goi("/api/but-toan-cho?nguon=no_ncc&status=huy&gioi_han=1000", u="admin")
        dung(any(b["ma_nguon"] == B for b in g["ds"]), "bút toán của phiếu đã xoá còn dấu vết, trạng thái huỷ")
    finally:
        if GOC:                            # máy thử đang chạy: xoá phiếu thử; trong tiến trình thì ROLLBACK lo
            don()


if __name__ == "__main__":
    main()
