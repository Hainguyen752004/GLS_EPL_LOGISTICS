# -*- coding: utf-8 -*-
"""Khung chạy TRONG TIẾN TRÌNH cho các bài kiểm nối hệ anh Tune (06/10 — máy thử 8013 / 8014 / 8015 / 8095 / 8096 không còn bật;
anh Hải đang bấm tay trên 8011 / Web 5014 / API 5090).

LUẬT (anh Hải duyệt 06/10):
  · KHÔNG ghi gì sang DB demo, KHÔNG gọi 5090: mọi lời gọi mạng bị chặn (urllib.request.urlopen) — trừ máy giả trong bài ở
    127.0.0.1 khi bài cho phép (cho_phep_may_gia); chi_tune._goi thay bằng GiaKeToan (API phiếu thu / chi giả, có trạng thái);
    kho QLSX / kho tạm / SO nhiên liệu không có bộ giả thì gọi là bài hỏng.
  · KHÔNG dừng / bật máy nào: FastAPI TestClient trên app, không chạy sự kiện khởi động (không có luồng đồng bộ nền).
  · d7: mỗi ca MỘT giao dịch ngoài (SET LOCAL lock_timeout 5s), phiên chạy savepoint, cuối ROLLBACK. Chỉ ghi lên DỮ LIỆU THỬ MỚI
    tạo trong giao dịch (tài xế, chủ xe, xe, khách — du_lieu_thu); không xoá / sửa dòng sẵn có. Tăng phiên bản báo cáo
    (phien_ban_thang — dòng dùng chung theo tháng / ngày, máy 8011 cũng ghi) TẮT cho tiến trình bài kiểm, để giao dịch thử không
    giữ khoá dòng nào anh Hải đang dùng.

Dùng:
    import _tien_trinh_tune as TT
    gia = TT.GiaKeToan(); TT.gan_ke_toan(gia)
    with TT.Ca(("admin", "ketoan")) as ca:
        d = TT.du_lieu_thu(ca.db, "CMT")
        s, g = ca.goi("/api/trips", {...}, "admin")
"""
import datetime as dt
import json
import os
import sys
import urllib.request
import uuid

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
URL = open(os.path.join(GOC, ".may_thu", "url_epl_lao_d7.txt"), encoding="utf-8").read().strip()
if "_d7" not in URL.rsplit("/", 1)[-1]:
    sys.exit("Chuỗi nối không trỏ bản sao _d7 — bài chỉ chạy trên bản sao.")
os.environ["DATABASE_URL"] = URL
sys.path.insert(0, os.path.join(GOC, "backend", "app"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# ---------------------------------------------------------------- chặn mạng (trước khi nạp app)
MANG = []                     # URL đã định gọi ra ngoài (bị chặn)
_MAY_GIA = set()              # "127.0.0.1:<cổng>" máy giả trong bài được phép
_URLOPEN = urllib.request.urlopen


def _cam_mang(yc, *a, **k):
    url = getattr(yc, "full_url", str(yc))
    if any(("//%s/" % h) in url or url.endswith("//" + h) for h in _MAY_GIA):
        return _URLOPEN(yc, *a, **k)
    MANG.append(url)
    raise OSError("bài kiểm chặn mạng: %s" % url)


urllib.request.urlopen = _cam_mang


def cho_phep_may_gia(cong):
    _MAY_GIA.add("127.0.0.1:%d" % cong)


def bo_may_gia(cong):
    _MAY_GIA.discard("127.0.0.1:%d" % cong)


from fastapi import HTTPException                       # noqa: E402
from fastapi.testclient import TestClient               # noqa: E402
from sqlalchemy import create_engine, event, text       # noqa: E402
from sqlalchemy.orm import Session                      # noqa: E402

import models as M                                      # noqa: E402
from database import get_db                             # noqa: E402
from main import app                                    # noqa: E402
from services import chi_tune as CHI                    # noqa: E402
from services import dem_bao_cao as DEM                 # noqa: E402
from services import goi_ke_toan as KT                  # noqa: E402
from services import gui_tune as GT                     # noqa: E402
from services import kho_qlsx as KQ                     # noqa: E402
from services import so_nhien_lieu as NL                # noqa: E402
from services.bao_mat import ky_phien                   # noqa: E402

# Biến môi trường SAU khi database.py nạp .env (load_dotenv không ghi đè, nên đặt lại ở đây mới chắc).
os.environ["KHO_NGUON"] = "qlsx"
for _k in ("QLSX_GUI_BUT_TOAN", "EPL_CHI_TAM_UNG", "QLSX_WEB_URL", "EPL_DONG_BO_CHI_LUONG"):
    os.environ.pop(_k, None)

# Phiên bản báo cáo: tắt cho tiến trình bài kiểm (xem đầu tệp). Phần GOM vẫn chạy, chỉ không UPSERT phien_ban_thang lúc commit.
if event.contains(Session, "before_commit", DEM._truoc_commit):
    event.remove(Session, "before_commit", DEM._truoc_commit)

GT.cau_hinh = lambda dang_nhap=True: ("http://ke-toan-gia.local", "token-gia")


def _tinh_thang(db, viec, theo_ngay=False, tinh_lo=None):
    """Bộ đệm báo cáo (dem_bao_cao.lay_nhieu) đọc / ghi bao_cao_dem bằng KẾT NỐI RIÊNG — ngoài giao dịch thử (ghi thật vào d7) và
    không thấy dữ liệu thử chưa commit. Trong bài: tính thẳng mỗi lần, cùng dạng JSON như bản lưu, không đọc / ghi bao_cao_dem."""
    if tinh_lo is not None:
        kq = tinh_lo(list(range(len(viec))))
    else:
        kq = [t() for _, _, t in viec]
    return [json.loads(json.dumps(v, default=str)) for v in kq]


DEM.lay_nhieu = _tinh_thang


def _cam(ten):
    def _f(*a, **k):
        raise AssertionError("bài kiểm không được gọi %s: %s" % (ten, [str(x)[:80] for x in a[:3]]))
    return _f


# bản thật (đi qua urllib — bị chặn, trừ máy giả cho phép): bài dùng máy giả HTTP trong bài thì gắn lại các hàm này
CHI_GOI_THAT, KQ_GOI_THAT = CHI._goi, KQ._goi
CHI._goi = _cam("hệ kế toán (chi_tune._goi) khi chưa gắn GiaKeToan")
KQ._goi = _cam("kho QLSX (kho_qlsx._goi)")
KT.goi = _cam("kho tạm 8031 (goi_ke_toan.goi)")
NL._goi = _cam("SO nhiên liệu / cấn trừ (so_nhien_lieu._goi)")

KQUA = []


def dung(dk, ten, ct=""):
    KQUA.append(bool(dk))
    print(("  ✓ " if dk else "  SAI ") + ten + ((" — " + str(ct)[:300]) if ct != "" else ""))
    sys.stdout.flush()
    return bool(dk)


def ket_thuc(ten):
    print("\n%s: %s (%d/%d đạt) — đã ROLLBACK, bản sao d7 không đổi; %d lời gọi mạng bị chặn%s" % (
        ten, "ĐẠT" if all(KQUA) else "SAI %d" % KQUA.count(False), sum(KQUA), len(KQUA), len(MANG),
        (" (" + ", ".join(MANG[:3]) + ")") if MANG else ""))
    sys.exit(0 if all(KQUA) and KQUA else 1)


def ma(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return d.get("ma") if isinstance(d, dict) else None


def cau(g):
    d = (g or {}).get("detail") if isinstance(g, dict) else None
    return (d.get("loi") if isinstance(d, dict) else "") or ""


# ---------------------------------------------------------------- API phiếu thu / chi bên kế toán GIẢ
class GiaKeToan:
    """chi_tune._goi giả: tiền, kỳ, danh mục đối tượng, phiếu thu / chi (lưu · đọc · danh sách · xoá) + thao tác người bên kế
    toán trong bài (ghi_so, xoa_tay). Phiếu mang đúng thân save-and-commit đã gửi để bài soát định khoản / đối tượng / số."""

    def __init__(self):
        self.phieu = {}          # RealId → {body, st, xoa, so, post_at}
        self.obj = {}            # ObjectNo → ObjId
        self.duong = {}          # ObjectNo → danh mục (staff · suppliers · customers)
        self.nhan = []           # (method, đường, thân)
        self.n = 0

    def goi(self, method, duong, body=None):
        d = duong.split("?")[0]
        self.nhan.append((method, d, body))
        if d.endswith("/common/GetAllCurrency"):
            return [{"CUR_AUTOID": 26, "CUR_NAME": "LAK"}, {"CUR_AUTOID": 2, "CUR_NAME": "USD"}, {"CUR_AUTOID": 1, "CUR_NAME": "VND"},
                    {"CUR_AUTOID": 5, "CUR_NAME": "THB"}]
        if d.endswith("/common/GetFinancyCicle"):
            return [{"FICI_AUTOID": 77, "FICI_NAME": "2026", "FICI_DATEFROM": "2026-01-01", "FICI_DATETO": "2026-12-31",
                     "FICI_ISACTIVE": True, "FICI_ISCLOSE": False}]
        if "/master-data/" in d and d.endswith("/list"):
            so = (body or {}).get("ObjKey")
            return {"Data": [{"ObjId": self.obj[so], "ObjectNo": so}] if so in self.obj else []}
        if "/master-data/" in d and d.endswith("/upsert"):
            so = body["ObjectNo"]
            if so not in self.obj:
                self.obj[so] = 70000 + len(self.obj) + 1
                self.duong[so] = d.split("/")[-2]
            return self.obj[so]
        if d.endswith("/cmpayment-receipt/save-and-commit"):
            self.n += 1
            rid = 880000 + self.n
            vt, h = body["VoucherType"], body["Header"]
            loai = {59: "CTR", 60: "CKH", 17: "TK"}.get(h.get("DotyAutoId"), "PH")
            self.phieu[rid] = {"body": body, "st": 1, "xoa": False, "so": "GIA-%s-%04d" % (loai, self.n), "post_at": None}
            return {"RealId": rid, "TmpId": 0, "DocumentNo": self.phieu[rid]["so"], "VoucherType": vt}
        if d.endswith("/cmpayment-receipt/list"):
            vt = (body or {}).get("VoucherType")
            return {"Rows": [{"DOC_DOCUMENTID": k, "DOC_DOCUMENTNO": v["so"], "DOC_REFDOCUMENTNO": v["body"]["Header"]["RefDocumentNo"],
                              "CM_AMOUNT": v["body"]["Header"]["Amount"], "ST_AUTOID": v["st"]}
                             for k, v in self.phieu.items()
                             if not v["xoa"] and v["body"]["Header"]["ObjectId"] == (body or {}).get("ObjectId")
                             and (vt is None or v["body"]["VoucherType"] == vt)]}
        if d.endswith("/cmpayment-receipt/delete"):
            x = self.phieu.get(int(body["DocumentId"]))
            if x is None or x["xoa"]:
                raise HTTPException(422, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "Hệ kế toán từ chối: không có phiếu %s" % body["DocumentId"],
                                          "http": 200, "code": 404})
            if x["st"] in CHI.DA_GHI_SO:
                raise HTTPException(422, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "Hệ kế toán từ chối: phiếu đã ghi sổ", "http": 200,
                                          "code": 409})
            x["xoa"] = True
            return True
        if "/cmpayment-receipt/" in d and method == "GET":
            x = self.phieu.get(int(d.rsplit("/", 1)[1]))
            if x is None or x["xoa"]:
                return {"Master": None, "Entries": []}       # đúng như API thật với phiếu đã xoá (Success true, Master null)
            h = x["body"]["Header"]
            return {"Master": {"DOCUMENTNO": x["so"], "STATUS": x["st"], "DOTY": h.get("DotyAutoId"), "REFDOCUMENTNO": h.get("RefDocumentNo"),
                               "AMOUNT": h.get("Amount"), "SUPPLIER": h.get("ObjectId"), "OBJECTID": h.get("ObjectId"),
                               "CURRENCYID": h.get("CurrencyId"),
                               "POSTNAME": "thủ quỹ giả" if x["st"] in CHI.DA_GHI_SO else None, "POSTDATE": x["post_at"]},
                    "Entries": [{"ET_DEBTORACCOUNT": e.get("DebitAccount"), "ET_CREDITACCOUNT": e.get("CreditAccount"),
                                 "ET_TOTALAMOUNT": e.get("Amount"), "OBJ_AUTOID": e.get("ObjectId"), "ET_NOTE": e.get("Description")}
                                for e in x["body"].get("Entries") or []]}
        if d.endswith("/sales/debt/customer-detail"):
            return {"Summary": {}, "Debts": [], "Orders": [], "Aging": [], "Collections": []}
        raise HTTPException(502, {"ma": "BEN_KE_TOAN_TU_CHOI", "loi": "giả: bài không cho gọi %s %s" % (method, d), "http": 500})

    # việc của người bên kế toán trong bài
    def ghi_so(self, rid, st=12):
        self.phieu[rid]["st"] = st
        self.phieu[rid]["post_at"] = "2026-10-06T09:00:00"

    def xoa_tay(self, rid):
        self.phieu[rid]["xoa"] = True

    def con(self, obj, ref):
        return [k for k, v in self.phieu.items() if not v["xoa"] and v["body"]["Header"]["ObjectId"] == obj
                and v["body"]["Header"]["RefDocumentNo"] == ref]

    def than(self, rid):
        return self.phieu[rid]["body"]

    def so_doi_tuong(self, oid):
        return next((so for so, i in self.obj.items() if i == oid), None)


def gan_ke_toan(gia):
    CHI._goi = gia.goi
    CHI._BO_NHO.clear() if hasattr(CHI, "_BO_NHO") else None


# ---------------------------------------------------------------- một ca: giao dịch ngoài + phiên savepoint + TestClient
class Ca:
    eng = None

    def __init__(self, nguoi=()):
        self.nguoi = nguoi

    def __enter__(self):
        if Ca.eng is None:
            Ca.eng = create_engine(URL, connect_args={"options": "-c timezone=UTC"})
        self.conn = Ca.eng.connect()
        self.ngoai = self.conn.begin()
        try:
            self.conn.execute(text("SET LOCAL lock_timeout = '5s'"))      # 8011 chạy song song: chờ khoá quá 5 giây thì hỏng, không treo
            M.Base.metadata.create_all(bind=self.conn, checkfirst=True)    # bảng mới d7 chưa có: dựng TRONG giao dịch (ROLLBACK xoá)
            self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint", autoflush=False)
            db = self.db

            def _db():
                try:
                    yield db
                finally:
                    db.rollback()
            app.dependency_overrides[get_db] = _db
            self.c = TestClient(app, raise_server_exceptions=False)
            self.H = {}
            for u in self.nguoi:
                x = db.query(M.User).filter(M.User.username == u, M.User.active.is_(True)).first()
                assert x is not None, "d7 thiếu người dùng %s" % u
                self.H[u] = {"Authorization": "Bearer " + ky_phien(u)}
        except BaseException:
            self.ngoai.rollback()
            self.conn.close()
            raise
        return self

    def goi(self, duong, body=None, u=None, method=None):
        r = self.c.request(method or ("POST" if body is not None else "GET"), duong, json=body, headers=self.H.get(u, {}) if u else {})
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {"_text": r.text[:300]}

    def __exit__(self, *a):
        app.dependency_overrides.clear()
        try:
            self.db.close()
        finally:
            self.ngoai.rollback()
            self.conn.close()
        return False


def du_lieu_thu(db, ten):
    """Danh mục thử MỚI trong giao dịch: khách, chủ xe liên kết (phí 2 %, ngưỡng 40 t, 1 USD/t), xe nhà, xe thuê của chủ đó, hai
    tài xế. Không dùng xe / tài xế sẵn có (đổi trạng thái chạy của họ là sửa dòng anh Hải đang dùng)."""
    tag = "THU-%s-%s" % (ten, uuid.uuid4().hex[:5].upper())
    kh = M.Customer(name="Khách thử %s" % tag)
    chu = M.Owner(name="Chủ xe thử %s" % tag, fee_pct=2, over_limit_t=40, over_price=1, hire_ccy="USD")
    db.add_all([kh, chu])
    db.flush()
    nha = M.Vehicle(truck_no=tag + "-N", owner_type="EPL")
    thue = M.Vehicle(truck_no=tag + "-T", owner_type="joint", owner_id=chu.id)
    db.add_all([nha, thue])
    db.flush()
    tx1 = M.Driver(name="ທ້າວ ທົດລອງ %s 1" % tag, name_latin="Thu %s 1" % tag)
    tx2 = M.Driver(name="ທ້າວ ທົດລອງ %s 2" % tag, name_latin="Thu %s 2" % tag)
    db.add_all([tx1, tx2])
    db.commit()                    # chốt savepoint (giao dịch ngoài vẫn ROLLBACK): get_db của từng yêu cầu rollback phần chưa chốt

    class D:
        pass
    d = D()
    d.tag, d.kh, d.chu, d.nha, d.thue, d.tx1, d.tx2 = tag, kh, chu, nha, thue, tx1, tx2
    d.hom_nay = dt.date.today().isoformat()
    return d
