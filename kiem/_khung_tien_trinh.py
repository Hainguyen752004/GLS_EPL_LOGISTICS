# -*- coding: utf-8 -*-
"""Khung bài kiểm TRONG TIẾN TRÌNH trên bản sao d7 — chạy được cả khi chủ dự án đang bấm tay trên 8011 / Web (06/10).

Thay cho các bài cũ gọi máy 8010 / 8013 / 8014 bằng HTTP thật: ở đó mỗi lần khoá phiếu, ghi sổ mục IV, cấp dầu… là một lần ghi
thật sang hệ kế toán anh Tune (DB demo) và để lại dữ liệu trên DB trang điều xe.

Luật (chủ dự án duyệt 06/10):
  · KHÔNG gọi mạng: urllib.request.urlopen bị chặn và đếm (MANG). Hệ kế toán anh Tune GIẢ LẬP: phiếu chi / công nợ / danh mục
    đối tượng (chi_tune._goi), bút toán (gui_but_toan_tune._goi — cờ gửi BẬT như máy 8011), kho QLSX (kho_qlsx._goi). Kho tạm
    8031 (goi_ke_toan.goi) đã bỏ — gọi là bài hỏng.
  · d7: một giao dịch ngoài, phiên chạy savepoint, cuối ROLLBACK. CHỈ ghi trên dữ liệu thử dựng mới (xe, rơ-moóc, tài xế, tài khoản
    tài xế, khách, chủ xe, nhà cung cấp, trạm… tên «THU-…» / «ທົດລອງ») và DO thử ở một THÁNG d7 chưa có DO. Không xoá / sửa dòng
    đang có — khoá dòng đó sẽ làm màn của người đang bấm tay treo tới lúc bài xong.
  · Bộ đệm báo cáo: KHÔNG ghi bảng bao_cao_dem (bộ đệm ghi bằng kết nối riêng — lọt ra ngoài giao dịch): báo cáo tính thẳng.
    Số phiên bản (phien_ban_thang) chỉ tăng khoá của THÁNG THỬ; khoá chung ('*', 'tx', 'the', 'ncc', 'thu'…) bỏ — để không giữ
    khoá dòng mà máy 8011 cũng cần lúc người dùng ghi phiếu.
  · Giao dịch ngắn: lock_timeout 5 giây.

Dùng:
    import _khung_tien_trinh as K           # đặt DATABASE_URL = d7, chặn mạng, cài bộ giả — TRƯỚC khi nạp mã máy chủ
    with K.Khung() as m:
        xe = m.xe("THU-XX-01"); tx = m.tai_xe("ທ້າວ ທົດລອງ", tai_khoan=True); kh = m.khach("ລູກຄ້າ ທົດລອງ")
        s, p = m.goi("/api/trips", {...}, vai="thabok")
    K.ket_thuc()                            # in tổng, thoát mã 0 / 1
"""
import datetime as dt
import json
import os
import sys
import urllib.request

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
os.environ["KHO_NGUON"] = "qlsx"
os.environ["QLSX_GUI_BUT_TOAN"] = "1"                   # như máy 8011: khoá phiếu là gửi bút toán — sang bộ giả
os.environ.pop("EPL_CHI_TAM_UNG", None)                 # tạm ứng chi ở hệ kế toán (mặc định) — sang bộ giả
os.environ.pop("QLSX_WEB_URL", None)
for _d in (os.path.join(GOC, "backend", "app"), os.path.join(GOC, "kiem")):
    if _d not in sys.path:
        sys.path.insert(0, _d)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MANG = []                                               # mọi lần định gọi mạng (bị chặn)


def _cam_mang(yc, *a, **k):
    MANG.append(getattr(yc, "full_url", str(yc)))
    raise OSError("bài kiểm không được gọi mạng ra ngoài: %s" % MANG[-1])


urllib.request.urlopen = _cam_mang

KQ = []


def dung(dk, ten, ct=""):
    KQ.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:400]) if ct != "" else ""))
    sys.stdout.flush()
    return bool(dk)


def ma(g):
    d = g.get("detail") if isinstance(g, dict) else None
    return d.get("ma", "") if isinstance(d, dict) else ""


def phai(s, mong, buoc, g=None):
    """Bước bắt buộc để bài đi tiếp: sai thì ghi SAI rồi dừng bài (ROLLBACK vẫn chạy)."""
    if not dung(s == mong, "%s → %s" % (buoc, s), ma(g) if s == mong else json.dumps(g, ensure_ascii=False, default=str)[:300]):
        raise RuntimeError("DỪNG: %s trả %s, mong %s" % (buoc, s, mong))


def ket_thuc(ten):
    print("đã ROLLBACK — bản sao d7 không đổi; lời gọi mạng bị chặn: %d" % len(MANG))
    print("%s — TỔNG: %d/%d đạt" % (ten, sum(KQ), len(KQ)))
    sys.exit(0 if KQ and all(KQ) and not MANG else 1)


# ================================================================ hệ kế toán anh Tune GIẢ LẬP
class GIA:
    ke_toan = []            # (method, đường, thân) — chi_tune._goi
    but_toan = []           # (method, đường, thân) — gui_but_toan_tune._goi
    kho = []                # (method, đường, thân, khoá) — kho_qlsx._goi
    ton = {}                # (mã kho, mã hàng) → [số lượng, giá bình quân]
    phieu_kho = {}          # SourceRef → kết quả phiếu xuất
    n = 0


def _so():
    GIA.n += 1
    return GIA.n


def gia_ke_toan(method, duong, body=None):
    d = duong.split("?")[0]
    GIA.ke_toan.append((method, d, body))
    if d.startswith("/api/v1/master-data/") and d.endswith("/list"):
        return {"Data": [{"ObjId": 70000 + abs(hash((body or {}).get("ObjKey"))) % 9999, "ObjectNo": (body or {}).get("ObjKey")}]}
    if d.startswith("/api/v1/master-data/") and d.endswith("/upsert"):
        return 70000 + _so()
    if d == "/api/v1/accounting/cmpayment-receipt/save-and-commit":
        return {"RealId": 880000 + _so(), "Success": True}
    if d == "/api/v1/accounting/cmpayment-receipt/list":
        return {"Data": [], "Rows": [], "Total": 0}
    if d == "/api/v1/accounting/cmpayment-receipt/delete":
        return {"Success": True}
    if method == "GET" and d.startswith("/api/v1/accounting/cmpayment-receipt/"):
        so = d.rsplit("/", 1)[-1]
        return {"Master": {"STATUS": 1, "DOCUMENTNO": "1368-THU-%s" % so, "POSTNAME": None, "POSTDATE": None}}
    if d == "/api/v1/sales/debt/customer-detail":
        return {"Summary": {}, "Aging": [], "Debts": [], "Orders": [], "Collections": []}
    if d == "/api/v1/common/GetAllCurrency":
        return [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}, {"CUR_AUTOID": 2, "CUR_NAME": "USD"}, {"CUR_AUTOID": 3, "CUR_NAME": "VND"},
                {"CUR_AUTOID": 4, "CUR_NAME": "THB"}]
    if d == "/api/v1/common/GetFinancyCicle":
        return [{"FICI_AUTOID": 1, "FICI_NAME": "2026", "FICI_DATEFROM": "2000-01-01", "FICI_DATETO": "2099-12-31",
                 "FICI_ISACTIVE": True, "FICI_ISCLOSE": False}]
    raise AssertionError("bộ giả hệ kế toán không có đường %s %s" % (method, duong))


def gia_but_toan(method, duong, body=None, key=None, cho=None):
    GIA.but_toan.append((method, duong, body))
    if method == "POST" and duong.endswith("/reverse"):
        return 200, {"Success": True, "Result": {"Reversed": True, "DocumentId": None}}
    if method == "POST":
        n = _so()
        return 200, {"Success": True, "Result": {"DocumentId": 950000 + n, "DocumentNo": "GL-THU-%04d" % n, "StatusId": 1}}
    return 404, {"Success": False, "Code": 404, "ErrorDetail": {"ErrorCode": "JOURNAL_ENTRY_NOT_FOUND"}}


def _env(ma_, kq=None, loi=None, cau=None):
    if loi:
        return ma_, {"Success": False, "Code": ma_, "Message": cau, "ErrorDetail": {"ErrorCode": loi}}
    return ma_, {"Success": True, "Code": ma_, "Message": "OK", "Result": kq}


def gia_kho(method, duong, body=None, key=None):
    from services import kho_qlsx as KQ_
    GIA.kho.append((method, duong, body, key))
    if duong.startswith(KQ_.DUONG + "/stock-balance"):
        from urllib.parse import parse_qs, unquote, urlsplit
        q = parse_qs(urlsplit(duong).query)
        kho = set(unquote(q["warehouseCodes"][0]).split(",")) if "warehouseCodes" in q else None
        hang = set(unquote(q["itemCodes"][0]).split(",")) if "itemCodes" in q else None
        rows = [{"warehouseCode": k, "itemCode": h, "qty": v[0], "avgUnitCost": v[1], "amount": round(v[0] * v[1])}
                for (k, h), v in GIA.ton.items() if (kho is None or k in kho) and (hang is None or h in hang)]
        return _env(200, {"rows": rows})
    if duong == KQ_.DUONG + "/stock-issues" and method == "POST":
        if key in GIA.phieu_kho:
            return _env(200, dict(GIA.phieu_kho[key], replayed=True))
        for d in body["Lines"]:
            v = GIA.ton.get((d["WarehouseCode"], d["ItemCode"]), [0, 0])
            if v[0] + 1e-9 < d["Qty"]:
                return _env(409, loi="LOGISTICS_STOCK_INSUFFICIENT", cau="%s tại %s còn %s, cần %s." % (
                    d["ItemCode"], d["WarehouseCode"], v[0], d["Qty"]))
        n, lines = _so(), []
        for d in body["Lines"]:
            v = GIA.ton[(d["WarehouseCode"], d["ItemCode"])]
            v[0] -= d["Qty"]
            lines.append({"itemCode": d["ItemCode"], "warehouseCode": d["WarehouseCode"], "qty": d["Qty"], "unitCost": v[1],
                          "amount": round(d["Qty"] * v[1], 2)})
        kq = {"documentId": 9000 + n, "documentNo": "PXK-THU-%d" % n, "sourceRef": key, "purpose": body["Purpose"],
              "objectCode": body.get("ObjectCode"), "lines": lines, "replayed": False}
        GIA.phieu_kho[key] = kq
        return _env(201, kq)
    if duong == KQ_.DUONG + "/stock-issues/cancel":
        sr = body["SourceRef"]
        kq = GIA.phieu_kho.pop(sr, None)
        if kq is None:
            return 404, {"Success": False, "Code": 404, "Message": "không thấy", "ErrorDetail": {"ErrorCode": "LOGISTICS_STOCK_NOT_FOUND"}}
        for x in kq["lines"]:
            GIA.ton[(x["warehouseCode"], x["itemCode"])][0] += x["qty"]
        return _env(200, dict(kq, state="CANCELLED"))
    return 404, {"Success": False, "Code": 404, "Message": "giả: không có đường %s" % duong}


def _cam_kho_tam(*a, **k):
    raise AssertionError("kho tạm 8031 đã bỏ — bài không được gọi goi_ke_toan.goi %s" % (a[:2],))


def _cai_bo_gia():
    from services import chi_tune as CHI
    from services import goi_ke_toan as KT
    from services import gui_but_toan_tune as GBT
    from services import kho_qlsx as KQ_
    CHI._goi, GBT._goi, KQ_._goi, KT.goi = gia_ke_toan, gia_but_toan, gia_kho, _cam_kho_tam


# ================================================================ bộ đệm báo cáo
THANG_THU = []                                          # ['YYYY-MM'] của bài đang chạy


def _khong_dem(db, viec, theo_ngay=False, tinh_lo=None):
    """Thay DEM.lay_nhieu: tính thẳng, không đọc / ghi bao_cao_dem (kết nối riêng ngoài giao dịch)."""
    kq = tinh_lo(list(range(len(viec)))) if tinh_lo is not None else [t() for _, _, t in viec]
    return [json.loads(json.dumps(v, default=str)) for v in kq]


def _loc_khoa(session):
    """Trước DEM._truoc_commit: chỉ giữ khoá phiên bản của THÁNG THỬ. Khoá chung ('*', 'tx', 'the'…) → khoá tháng thử."""
    session.flush()
    k = session.info.get("_thang_doi")
    if not k or not THANG_THU:
        return
    giu = {x for x in k if x.startswith(THANG_THU[0])}
    if len(giu) < len(k):
        giu.add(THANG_THU[0])
    session.info["_thang_doi"] = giu


# ================================================================ khung
class Khung:
    """TestClient trên _d7: một kết nối, một giao dịch ngoài, phiên chạy savepoint; hết bài ROLLBACK."""

    def __enter__(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine, event, text
        from sqlalchemy.orm import Session
        import models as M
        from database import get_db
        from main import app
        from services import bao_mat as BM
        from services import dem_bao_cao as DEM
        _cai_bo_gia()
        DEM.lay_nhieu = _khong_dem
        self.M, self.app, self.BM = M, app, BM
        self.eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
        self.conn = self.eng.connect()
        self.ngoai = self.conn.begin()
        self.conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint", autoflush=False)
        co = {d.strftime("%Y-%m") for (d,) in self.db.query(M.Trip.doc_date).filter(M.Trip.doc_date.isnot(None)).distinct()}
        nam, th = 2026, 9
        while "%04d-%02d" % (nam, th) in co:
            nam, th = (nam, th - 1) if th > 1 else (nam - 1, 12)
        self.nam, self.th = nam, th
        self.thang = "%04d-%02d" % (nam, th)
        THANG_THU[:] = [self.thang]
        event.listen(Session, "before_commit", _loc_khoa, insert=True)
        self._event = event

        def _db():
            try:
                yield self.db
            finally:
                self.db.rollback()
        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[BM.may_qlsx_goi] = lambda: "qlsx"       # kho QLSX gọi sang (bộ giả) — không đụng khoá thật
        self.c = TestClient(app, raise_server_exceptions=False)
        self.tk = {}
        return self

    def __exit__(self, *a):
        from sqlalchemy.orm import Session
        self.app.dependency_overrides.clear()
        try:
            self._event.remove(Session, "before_commit", _loc_khoa)
        except Exception:                               # noqa: BLE001
            pass
        self.db.close()
        self.ngoai.rollback()
        self.conn.close()
        self.eng.dispose()
        THANG_THU[:] = []
        return False

    # ------------------------------------------------------------ gọi API
    def ngay(self, d=1):
        return dt.date(self.nam, self.th, d)

    def phien(self, u):
        if u not in self.tk:
            self.tk[u] = self.BM.ky_phien(u)
        return self.tk[u]

    def goi(self, duong, du_lieu=None, vai=None, method=None):
        """(mã HTTP, thân JSON) — cùng chữ ký hàm `goi` của các bài cũ (kiem/_quy_trinh.py dùng được)."""
        r = self.c.request(method or ("POST" if du_lieu is not None else "GET"), duong, json=du_lieu,
                           headers={"Authorization": "Bearer " + self.phien(vai)} if vai else {})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, r.content

    def gui_tep(self, duong, ten, du, kieu, vai, them=None):
        r = self.c.post(duong, files={"tep": (ten, du, kieu)}, data=them or {},
                        headers={"Authorization": "Bearer " + self.phien(vai)} if vai else {})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, r.content

    def tai(self, url, vai=None):
        """GET thô (tệp, ảnh) — `vai` thì kèm ?tk= như trình duyệt mở tệp."""
        r = self.c.get(url + (("&" if "?" in url else "?") + "tk=" + self.phien(vai) if vai else ""))
        return r.status_code, r.content

    # ------------------------------------------------------------ dữ liệu thử (dòng MỚI, rollback là mất)
    def commit(self):
        self.db.commit()

    def chu_xe(self, ten="ເຈົ້າຂອງລົດ ທົດລອງ", **k):
        o = self.M.Owner(name=ten, **k)
        self.db.add(o); self.db.flush()
        return o

    def xe(self, so, loai="EPL", chu=None, **k):
        v = self.M.Vehicle(truck_no=so, owner_type=loai, status="available", active=True,
                           owner_id=chu.id if chu is not None else None,
                           owner_name=chu.name if chu is not None else None, plate_head=k.pop("plate_head", "ທລ " + so[-4:]), **k)
        self.db.add(v); self.db.flush()
        return v

    def tai_xe(self, ten, tai_khoan=False):
        """Tài xế thử; `tai_khoan=True` thì kèm tài khoản vai driver (tên đăng nhập trả về ở .username)."""
        d = self.M.Driver(name=ten, name_latin="Thu " + ten[-6:], status="available")
        self.db.add(d); self.db.flush()
        d.username = None
        if tai_khoan:
            u = self.M.User(username="thu_tx_" + d.id, password_hash="khong-dang-nhap-bang-mat-khau", full_name=ten,
                            role="driver", driver_id=d.id, active=True)
            self.db.add(u); self.db.flush()
            d.username = u.username
        return d

    def khach(self, ten="ລູກຄ້າ ທົດລອງ", **k):
        c = self.M.Customer(name=ten, active=True, **k)
        self.db.add(c); self.db.flush()
        return c

    def diem_do(self, ma_, ten, **k):
        p = self.M.FuelPlace(code=ma_, name=ten, **k)
        self.db.add(p); self.db.flush()
        return p

    def diem_kho(self, ma_="KHO-TB"):
        return self.db.query(self.M.FuelPlace).filter(self.M.FuelPlace.code == ma_).one()
