# -*- coding: utf-8 -*-
"""GIEO BỘ DỮ LIỆU SẠCH cho MÁY THỬ — đi qua HTTP như người thật, MỖI BƯỚC ĐÚNG VAI theo bảng "Nhiệm Vụ" (services/phan_quyen.py).

    python tools/may_thu/gieo_bo_sach.py --chi-in                 in kế hoạch (bước · vai · việc), KHÔNG gọi máy nào
    python tools/may_thu/gieo_bo_sach.py                          gieo thật (máy thử 8011 + kho tạm 8031 + API anh Tune 5090)
    python tools/may_thu/gieo_bo_sach.py --cho-thu-quy 10         như trên, nhưng ở bước xuất phát / xe tới ĐỢI tối đa 10 phút để
                                                                   người thử ghi sổ phiếu chi tạm ứng bên Web anh Tune

Tham số khác: --dx URL (trang điều xe, mặc định EPL_DX hoặc http://127.0.0.1:8011) · --kt URL (kho tạm, mặc định EPL_KT hoặc
http://127.0.0.1:8031) · --ngay YYYY-MM-DD (ngày lập / xe đi / xe về, mặc định hôm nay) · --khong-can-sach (cho chạy khi máy còn
phiếu — mặc định dừng: số PTU trùng thì phiếu chi tạm ứng bên anh Tune bị dùng lại).

TRƯỚC KHI CHẠY (em chính làm): dọn hai DB bản sao (tools/may_thu/don_may_thu.py that), dọn DB demo anh Tune
(20261002_don_du_lieu_thu_epl.sql) và áp hai script SO nhiên liệu / cấn trừ; máy 8011 (QLSX_GUI_BUT_TOAN=1), 8031, 5090, 5014 bật.
Công cụ CHỈ chạy khi cả hai máy báo DB tên bản sao (…_d<số>). Không đụng Web anh Tune: ghi sổ phiếu chi, thu nợ, tất toán tài xế,
lập đề nghị trả đối tác là phần bấm tay.

BỘ CHUYẾN (tháng của --ngay):
  0  Kho tạm: nhập dầu kho Thà Bốc + kho xe VN (có giá) · nhập phụ tùng (thủ kho số lượng, KT Chi phí gõ giá).
  A  Xe nhà GOM mỏ → bãi, TRỌN LUỒNG: tạm ứng NHIỀU DÒNG tiền mặt (phiếu chi "Chi trước" nhiều dòng), dầu kho nội bộ, tài xế khai
     đổ dọc đường ở trạm cho ghi nợ (nợ nhà cung cấp), xe về (hàng vào kho bãi) → khoá → Tạo SO cước → bút toán sang kế toán.
  B  Xe nhà GIAO bãi → cảng, lấy lô của A, dầu hai kho, sửa xe lấy phụ tùng kho (xuất nội bộ 614/1371) → khoá → Tạo SO.
  C  Xe THUÊ (ທ້າວ ຄຳຫລ້າ) lấy dầu kho (XUẤT BÁN, giá bán) + EPL ứng tiền mặt → khoá → Tạo SO (cước + SO nhiên liệu cùng nút).
     KHÔNG lập đề nghị trả — chủ dự án tự bấm màn Tất toán đối tác để thấy cấn trừ.
  D  Xe THUÊ đối tác tự lo hết (dầu mua, khoản đi đường chủ xe tự trả; không ứng, không dầu kho) → khoá → Tạo SO → chờ tất toán
     (trả đủ tiền thuê − phí).
  E  Một DO mới lập, chưa duyệt gì (test tay từ đầu).    F  Một DO đang trên đường (không tạm ứng nên Bãi xuất phát được).
  Tất toán tài xế: để nguyên — A, B có dòng tạm ứng / tài xế tự chi đủ cho bảng tính.

XUẤT PHÁT / XE TỚI khi có tạm ứng tiền mặt: luật trang điều xe chặn Bãi (409 CHUA_NHAN_TAM_UNG) cho tới khi thủ quỹ GHI SỔ phiếu chi
tạm ứng bên anh Tune — đó là bước bấm tay. Công cụ thử vai Bãi trước; bị chặn đúng luật thì (không có --cho-thu-quy) Sếp bấm thay
và in rõ "THAY VAI"; có --cho-thu-quy thì đợi người thử ghi sổ rồi Bãi bấm.

Dừng NGAY ở bước hỏng: in bước · vai · việc · HTTP · mã lỗi · câu lỗi, rồi in bảng những gì đã gieo. Cuối cùng in bảng từng DO:
trạng thái, số chứng từ bên anh Tune (SO cước, PTU → phiếu chi, bút toán, SO nhiên liệu, TCX / TKN) và tất toán dự kiến.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

MAT_KHAU = "1234"
VAI_DX = ("admin", "thabok", "ketoan", "ketoancp", "khonl", "khotb", "khovc", "khopt", "totsua", "quytb", "quyvc", "doanhthu",
          "tx01", "tx02", "tx03")
VAI_KT = ("khonl", "khopt", "ketoancp")
TEN_VAI = {"admin": "Sếp", "thabok": "Admin Thà Bốc (Bãi)", "ketoan": "KT Thu/Chi VC", "ketoancp": "KT Chi phí VC",
           "khonl": "KT kho xăng dầu", "khotb": "Thủ kho dầu Thà Bốc", "khovc": "Thủ kho dầu Viêng Chăn", "khopt": "Thủ kho phụ tùng",
           "totsua": "Tổ sửa chữa", "quytb": "Quỹ tiền mặt Thà Bốc", "quyvc": "Thủ quỹ VC", "doanhthu": "KT doanh thu",
           "tx01": "Tài xế tx01", "tx02": "Tài xế tx02", "tx03": "Tài xế tx03", "—": "máy"}

# ---------------------------------------------------------------- bộ chuyến (danh mục giữ lại sau dọn — đối chiếu theo mã / tên)
TUYEN_GOM = ("ກາສີ", "ທ່າບົກ")                 # ກາສີ → ທ່າບົກ: mỏ → bãi, không phí cao tốc
TUYEN_GIAO = ("ທ່າບົກ", "ທ່າເຮືອກະລໍ")          # ທ່າບົກ → ທ່າເຮືອກະລໍ: bãi → cảng, tuyến có BOT (tự thêm dòng x_toll)
KHACH = "EPLKH-0834a9e9606b"                     # ຄຳຕຸ້ຍ — có mã kế toán, hợp đồng HDVC-2026-001, bảng giá cả hai tuyến
CHU_XE = "0a073ea75bb3"                          # ທ້າວ ຄຳຫລ້າ — xe ຮ່ວມ-07/08/09, hợp đồng thuê HDTX-2026-001
NHAP_DAU = (("KHO-TB", 2000, 26500), ("KHO-XE-VN", 1000, 27000))      # (kho, lít, giá LAK/L)
NHAP_PT = (("12R22.5", 4, 3200000), ("bầu hơi", 4, 520000))           # (chữ trong tên phụ tùng, số lượng, giá LAK)
GIA_IV = {"x_food": 100000, "x_phone": 150000, "x_bridge": 50000, "x_parking": 30000, "x_vn": 430000, "x_water": 60000,
          "x_trip": 1800000}
GIA_BAN_DAU = 33000                              # giá bán dầu kho cho đối tác (KT kho xăng dầu gõ lúc kiểm mục III)

DO = {
    "A": {"ten": "Xe nhà GOM mỏ→bãi, trọn luồng", "kind": "gom", "xe": "341", "tai_xe": "DRV-01", "tk_tai_xe": "tx01",
          "tuyen": TUYEN_GOM, "can_mo": 40, "can_ve": 39.6,
          "dau": [("KHO-TB", 120)], "iv": ["x_food", "x_phone", "x_bridge", "x_parking", "x_water", "x_trip"],
          "do_doc_duong": ("VN-01", 40, 27000)},
    "B": {"ten": "Xe nhà GIAO bãi→cảng, sửa xe lấy phụ tùng kho", "kind": "giao", "xe": "342", "tai_xe": "DRV-02",
          "tuyen": TUYEN_GIAO, "lo": "A", "can_ve": 39.4, "pod": True,
          "dau": [("KHO-TB", 100), ("KHO-XE-VN", 300)], "iv": ["x_food", "x_phone", "x_vn", "x_water", "x_trip"], "sua_pt": ("12R22.5", 1)},
    "C": {"ten": "Xe THUÊ lấy dầu kho (xuất bán) + EPL ứng tiền", "kind": "gom", "xe": "ຮ່ວມ-07", "tai_xe": "DRV-LK-01",
          "tuyen": TUYEN_GOM, "can_mo": 38, "can_ve": 37.8, "dau": [("KHO-TB", 150)], "iv": ["x_food", "x_phone"], "gia_ban": GIA_BAN_DAU},
    "D": {"ten": "Xe THUÊ đối tác tự lo hết", "kind": "gom", "xe": "ຮ່ວມ-08", "tai_xe": "DRV-LK-02", "tuyen": TUYEN_GOM,
          "can_mo": 40, "can_ve": 39.8, "dau_mua_chu_xe": ("LA-02", 200), "iv_chu_xe": ["x_food"]},
    "E": {"ten": "DO mới lập, chưa duyệt (test tay từ đầu)", "kind": "gom", "xe": "343", "tai_xe": "DRV-03", "tuyen": TUYEN_GOM,
          "can_mo": 40, "dau": [("KHO-TB", 100)], "iv": ["x_food", "x_phone", "x_water", "x_trip"]},
    "F": {"ten": "DO đang trên đường", "kind": "gom", "xe": "344", "tai_xe": "DRV-04", "tuyen": TUYEN_GOM, "can_mo": 40,
          "dau": [("KHO-TB", 100)], "iv": ["x_water", "x_trip"]},
}


class Hong(Exception):
    """Một lời gọi trả mã không mong đợi — runner in bước / vai / lỗi rồi dừng."""
    def __init__(self, vai, method, duong, ma, than):
        d = (than or {}).get("detail") if isinstance(than, dict) else None
        d = d if isinstance(d, dict) else ({"loi": str(d or than)[:400]} if d or than else {})
        self.vai, self.http, self.ma, self.loi = vai, ma, d.get("ma"), d.get("loi") or json.dumps(than, ensure_ascii=False)[:400]
        self.duong = "%s %s" % (method, duong)
        super().__init__("%s → HTTP %s %s: %s" % (self.duong, ma, self.ma or "", self.loi))


class May:
    """Một máy (trang điều xe hoặc kho tạm): đăng nhập từng vai, gọi API."""

    def __init__(self, goc, ten):
        self.goc, self.ten, self.token = goc.rstrip("/"), ten, {}

    def tho(self, method, duong, body=None, vai=None, het_gio=180):
        dau = {"Content-Type": "application/json", "Accept": "application/json"}
        if vai:
            dau["Authorization"] = "Bearer " + self.token[vai]
        yc = urllib.request.Request(self.goc + duong, data=json.dumps(body).encode("utf-8") if body is not None else None,
                                    method=method, headers=dau)
        try:
            with urllib.request.urlopen(yc, timeout=het_gio) as t:
                tho = t.read()
                return t.status, (json.loads(tho) if tho else None), dict(t.headers)
        except urllib.error.HTTPError as e:
            tho = e.read()
            try:
                return e.code, (json.loads(tho) if tho else None), dict(e.headers)
            except ValueError:
                return e.code, {"detail": tho.decode("utf-8", "replace")[:400]}, dict(e.headers)

    def vao(self, vai):
        s, g, _ = self.tho("POST", "/api/dang-nhap", {"username": vai, "password": MAT_KHAU})
        if s != 200:
            raise Hong(vai, "POST", "%s/api/dang-nhap" % self.ten, s, g)
        self.token[vai] = g["token"]
        return g.get("user") or {}

    def goi(self, vai, method, duong, body=None, mong=(200,)):
        s, g, _ = self.tho(method, duong, body, vai)
        if s not in mong:
            raise Hong(vai, method, duong, s, g)
        return g


# ================================================================ ngữ cảnh + các bước
class Ngu:
    def __init__(self, a):
        self.a = a
        self.dx, self.kt = May(a.dx, "điều xe"), May(a.kt, "kho tạm")
        self.ngay = a.ngay
        self.ky = a.ngay[:7]
        self.user = {}                  # vai → thông tin người dùng (driver_id, place_id)
        self.dm = {}                    # danh mục đã chọn
        self.do = {}                    # "A" → {"id", "doc_no"}
        self.ghi_chu = []               # dòng ghi chú THAY VAI, cờ…


def dx(n, vai, method, duong, body=None, mong=(200,)):
    return n.dx.goi(vai, method, duong, body, mong)


def kt(n, vai, method, duong, body=None, mong=(200,)):
    return n.kt.goi(vai, method, duong, body, mong)


def phieu(n, k, vai="admin"):
    return dx(n, vai, "GET", "/api/trips/%s" % n.do[k]["id"])


def dong_muc(p, muc):
    return [e for e in (p.get("expenses") or []) if e["section"] == muc]


def can(dk, cau):
    if not dk:
        raise Hong("—", "KIỂM", "", "-", {"detail": {"ma": "KHONG_DUNG_KY_VONG", "loi": cau}})


# ---------------------------------------------------------------- khối 0
def b_kiem_may(n):
    for may in (n.dx, n.kt):
        s, g, _ = may.tho("GET", "/api/suc-khoe")
        if s != 200 or not g or not g.get("ok"):
            raise Hong("—", "GET", "%s /api/suc-khoe" % may.ten, s, g)
        ten = g.get("db") or ""
        if not re.search(r"_d\d+$", ten):
            raise Hong("—", "GET", "%s /api/suc-khoe" % may.ten, s, {"detail": {"ma": "KHONG_PHAI_BAN_SAO",
                       "loi": "%s đang nối DB «%s» — công cụ chỉ gieo vào bản sao của máy thử (tên …_d<số>)." % (may.goc, ten)}})
        print("      %s %s → DB %s" % (may.ten, may.goc, ten))


def b_dang_nhap(n):
    for v in VAI_DX:
        n.user[v] = n.dx.vao(v)
    for v in VAI_KT:
        n.kt.vao(v)
    print("      đăng nhập %d vai ở điều xe, %d vai ở kho tạm (mật khẩu demo)" % (len(VAI_DX), len(VAI_KT)))


def b_may_sach(n):
    s, g, h = n.dx.tho("GET", "/api/trips?co=1", vai="admin")
    tong = int(h.get("X-Tong") or h.get("x-tong") or len(g or []))
    if tong and not n.a.khong_can_sach:
        raise Hong("admin", "GET", "/api/trips", s, {"detail": {"ma": "MAY_CHUA_SACH", "loi": "Máy thử còn %d phiếu — dọn hai DB bản sao "
                   "(tools/may_thu/don_may_thu.py that) và DB demo anh Tune trước, hoặc chạy với --khong-can-sach." % tong}})
    g = dx(n, "ketoan", "GET", "/api/but-toan-cho?gioi_han=1")
    n.dm["gui_bt"] = bool(g.get("co_duong_gui"))
    print("      phiếu đang có: %d · gửi bút toán sang kế toán: %s" % (tong, "BẬT" if n.dm["gui_bt"] else "TẮT (bút toán nằm chờ)"))
    if not n.dm["gui_bt"]:
        n.ghi_chu.append("Máy 8011 chưa bật QLSX_GUI_BUT_TOAN — bút toán khoá phiếu nằm 'chờ gửi', không có số GL.")


def b_danh_muc(n):
    xe = {v["truck_no"]: v for v in dx(n, "admin", "GET", "/api/vehicles")}
    tx = {t.get("driver_code"): t for t in dx(n, "admin", "GET", "/api/drivers")}
    kh = [k for k in dx(n, "admin", "GET", "/api/customers") if (k.get("code") or "") == KHACH]
    tuyen = dx(n, "admin", "GET", "/api/routes")
    diem = {d.get("code"): d for d in dx(n, "admin", "GET", "/api/fuel-places")}
    pt = dx(n, "admin", "GET", "/api/parts")

    def tim_tuyen(di, den):
        song = [t for t in tuyen if t.get("active") is not False]
        r = [t for t in song if (t.get("name") or "").strip() == "%s → %s" % (di, den)] or             [t for t in song if di in (t.get("origin") or "") and den in (t.get("destination") or "")]
        can(r, "không có tuyến %s → %s đang dùng" % (di, den))
        return r[0]

    can(kh, "không có khách mã kế toán %s" % KHACH)
    n.dm.update({"xe": xe, "tx": tx, "khach": kh[0], "gom": tim_tuyen(*TUYEN_GOM), "giao": tim_tuyen(*TUYEN_GIAO), "diem": diem, "pt": pt})
    for k, d in DO.items():
        can(d["xe"] in xe and d["tai_xe"] in tx, "DO %s: không có xe %s hoặc tài xế %s" % (k, d["xe"], d["tai_xe"]))
    for ma in ("KHO-TB", "KHO-XE-VN", "VN-01", "LA-02"):
        can(ma in diem, "không có điểm dầu %s" % ma)
    can(diem["VN-01"].get("supplier_id"), "trạm VN-01 chưa gắn nhà cung cấp — khai đổ ghi nợ trạm sẽ bị chặn")
    for chu, _, _ in NHAP_PT:
        can(any(chu in (p.get("name") or "") for p in pt), "không có phụ tùng tên chứa «%s»" % chu)
    print("      khách %s · tuyến gom %s · tuyến giao %s · %d xe · %d tài xế" % (
        kh[0]["name"], n.dm["gom"]["name"], n.dm["giao"]["name"], len(xe), len(tx)))


def b_nhap_dau(n):
    g = kt(n, "khonl", "GET", "/api/nhien-lieu")
    kho = {k.get("code"): k for k in g.get("kho") or []}
    for ma, lit, gia in NHAP_DAU:
        can(ma in kho, "kho tạm không có kho dầu %s" % ma)
        kt(n, "khonl", "POST", "/api/nhien-lieu", {"kind": "in", "place_id": kho[ma]["id"], "qty_l": lit, "unit_price": gia,
                                                    "currency": "LAK", "move_date": n.ngay, "doc_no": "PN-GIEO-%s" % ma,
                                                    "note": "Gieo bộ sạch — nhập đầu kỳ"})
    g = kt(n, "khonl", "GET", "/api/nhien-lieu")
    print("      " + " · ".join("%s tồn %s L giá bq %s" % (k["code"], k["ton_lit"], k.get("gia_bq")) for k in g["kho"]
                                if k["code"] in dict((m, 1) for m, _, _ in NHAP_DAU)))


def _pt_theo_chu(n, chu):
    return next(p for p in n.dm["pt"] if chu in (p.get("name") or ""))


def b_nhap_pt(n):
    for chu, sl, _ in NHAP_PT:
        p = _pt_theo_chu(n, chu)
        kt(n, "khopt", "POST", "/api/phu-tung/%s/nhap-xuat" % p["id"], {"kind": "in", "qty": sl, "move_date": n.ngay,
                                                                       "note": "Gieo bộ sạch — nhập đầu kỳ"})
        print("      nhập %s × %s (chờ KT Chi phí gõ giá)" % (sl, p["name"]))


def b_gia_pt(n):
    cho = kt(n, "ketoancp", "GET", "/api/phu-tung/cho-gia").get("cho") or []
    for chu, _, gia in NHAP_PT:
        p = _pt_theo_chu(n, chu)
        ds = [m for m in cho if m["part_id"] == p["id"]]
        can(ds, "không thấy dòng nhập chờ giá của %s" % p["name"])
        for m in ds:
            kt(n, "ketoancp", "PUT", "/api/phu-tung/nhap/%s/gia" % m["id"], {"unit_price": gia})
        print("      gõ giá %s LAK cho %d dòng nhập %s" % ("{:,}".format(gia), len(ds), p["name"]))


# ---------------------------------------------------------------- phiếu xuất xe: các bước dùng chung
def _dong_lap(n, k):
    d, diem = DO[k], n.dm["diem"]
    ra = [{"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": diem[ma]["id"]} for ma, lit in d.get("dau", [])]
    if d.get("dau_mua_chu_xe"):
        ma, lit = d["dau_mua_chu_xe"]
        ra.append({"section": "fuel", "item_key": "diesel", "qty": lit, "place_id": diem[ma]["id"], "paid_by_epl": False})
    ra += [{"section": "travel", "item_key": x, "qty": 1} for x in d.get("iv", [])]
    ra += [{"section": "travel", "item_key": x, "qty": 1, "paid_by_epl": False} for x in d.get("iv_chu_xe", [])]
    return ra


def lap(k):
    def f(n):
        d = DO[k]
        xe, tx = n.dm["xe"][d["xe"]], n.dm["tx"][d["tai_xe"]]
        tuyen = n.dm["gom" if d["tuyen"] == TUYEN_GOM else "giao"]
        body = {"kind": d["kind"], "vehicle_id": xe["id"], "driver_id": tx["id"], "customer_id": n.dm["khach"]["id"],
                "route_id": tuyen["id"], "goods_type": "iron_ore", "doc_date": n.ngay, "out_date": n.ngay,
                "odo_out": round(xe.get("odometer_km") or 100000), "expenses": _dong_lap(n, k)}
        if d["kind"] == "gom":
            body["weight_origin"] = d["can_mo"]
        else:
            lo = phieu(n, d["lo"])
            hang = [g for g in lo.get("goods") or [] if g["loai"] == "hang"]
            can(hang, "DO %s chưa có dòng hàng để làm lô" % d["lo"])
            sl = round(lo.get("ton_lo") or DO[d["lo"]]["can_ve"], 3)       # lấy trọn lô: tồn lô = cân bãi lúc A về
            body["goods"] = [{"loai": "hang", "goods_name": hang[0]["goods_name"], "qty_t": sl, "tu_phieu_id": n.do[d["lo"]]["id"]}]
        p = dx(n, "thabok", "POST", "/api/trips", body)
        n.do[k] = {"id": p["id"], "doc_no": p["doc_no"]}
        print("      %s · %s · %s" % (p["doc_no"], d["xe"], ("xe thuê của " + (p.get("owner_name") or "")) if p.get("company") == "joint" else "xe nhà"))
    return f


def gui_kiem(k):
    def f(n):
        p = phieu(n, k)
        muc = ["info", "trans"] + [m for m in ("fuel", "travel", "repair", "other") if dong_muc(p, m)]
        for m in muc:
            if (p["sections"].get(m) or "wait") == "wait" and m != "repair":
                dx(n, "thabok", "POST", "/api/trips/%s/sections/%s/send" % (n.do[k]["id"], m))
        print("      gửi kiểm: %s" % ", ".join(m for m in muc if m != "repair"))
    return f


def kiem_i_ii(k):
    def f(n):
        tid = n.do[k]["id"]
        dx(n, "ketoan", "PUT", "/api/trips/%s" % tid, {"ore_bill_no": "PQ-%s" % n.do[k]["doc_no"].split("/")[0], "ore_bill_date": n.ngay})
        for m in ("info", "trans"):
            dx(n, "ketoan", "POST", "/api/trips/%s/sections/%s/verify" % (tid, m))
        p = phieu(n, k)
        print("      giá cước %s %s/%s%s" % (p.get("price"), p.get("price_ccy"), p.get("price_mode"),
                                           (" · giá thuê %s %s" % (p.get("hire_price"), p.get("hire_ccy"))) if p.get("company") == "joint" else ""))
    return f


def de_nghi_xuat_dau(k):
    def f(n):
        vs = dx(n, "thabok", "POST", "/api/trips/%s/vouchers" % n.do[k]["id"], {"kind": "fuel"})
        n.do[k]["plnl"] = vs
        print("      " + " · ".join("%s %s L" % (v["doc_no"], v["qty_l"]) for v in vs))
    return f


def cap_dau(k):
    def f(n):
        for v in n.do[k]["plnl"]:
            thu_kho = next((u for u, x in n.user.items() if x.get("role") == "depot" and x.get("place_id") == v["place_id"]), "khonl")
            dx(n, thu_kho, "POST", "/api/vouchers/%s/cap" % v["id"], {"qty": v["qty_l"]})
            print("      %s cấp %s L theo %s (kho tạm trừ tồn)" % (thu_kho, v["qty_l"], v["doc_no"]))
    return f


def kiem_ghi_so_iii(k, gia_ban=None):
    def f(n):
        tid = n.do[k]["id"]
        if gia_ban:
            p = phieu(n, k)
            dong = [{"id": e["id"], "section": "fuel", "sale_price": gia_ban} for e in dong_muc(p, "fuel") if e.get("source") == "kho"]
            dx(n, "khonl", "PUT", "/api/trips/%s" % tid, {"expenses": dong})
            print("      giá bán dầu cho đối tác %s LAK/L (%d dòng kho)" % ("{:,}".format(gia_ban), len(dong)))
        dx(n, "khonl", "POST", "/api/trips/%s/sections/fuel/verify" % tid)
        dx(n, "khonl", "POST", "/api/trips/%s/sections/fuel/book" % tid)
    return f


def kiem_ghi_so_iv(k):
    def f(n):
        tid = n.do[k]["id"]
        p = phieu(n, k)
        dong = [{"id": e["id"], "section": "travel", "unit_price": GIA_IV[e["item_key"]], "currency": "LAK"}
                for e in dong_muc(p, "travel") if e.get("paid_by_epl") is not False and e.get("item_key") in GIA_IV]
        if dong:
            dx(n, "ketoancp", "PUT", "/api/trips/%s" % tid, {"expenses": dong})
        dx(n, "ketoancp", "POST", "/api/trips/%s/sections/travel/verify" % tid)
        dx(n, "ketoancp", "POST", "/api/trips/%s/sections/travel/book" % tid)
        c = dx(n, "ketoancp", "GET", "/api/trips/%s/chi-ke-toan" % tid)
        if c.get("status"):
            can(c["status"] in ("da_gui", "da_chi"), "phiếu chi tạm ứng chưa sang được kế toán: %s" % (c.get("error_message") or c.get("error_code")))
            print("      phiếu chi tạm ứng bên kế toán: %s (%s)" % (c.get("document_no"), c.get("status")))
        else:
            print("      không có tiền mặt tài xế cầm đi — không có phiếu chi tạm ứng")
    return f


def kiem_ghi_so_v(k):
    def f(n):
        tid = n.do[k]["id"]
        dx(n, "ketoancp", "POST", "/api/trips/%s/sections/repair/verify" % tid)
        dx(n, "ketoancp", "POST", "/api/trips/%s/sections/repair/book" % tid)
    return f


def sua_xe_pt(k):
    def f(n):
        chu, sl = DO[k]["sua_pt"]
        p = _pt_theo_chu(n, chu)
        dx(n, "totsua", "POST", "/api/trips/%s/events" % n.do[k]["id"], {"kind": "repair", "incident_type": "tire",
                                                                       "note": "Thay lốp dọc đường (gieo bộ sạch)",
                                                                       "repair": {"source": "kho", "part_id": p["id"], "qty": sl}})
        print("      lấy %s × %s từ kho phụ tùng (kho tạm xuất ngay)" % (sl, p["name"]))
    return f


def _doi_thu_quy(n, k):
    """--cho-thu-quy: đợi thủ quỹ ghi sổ phiếu chi tạm ứng bên Web anh Tune (hỏi lại mỗi 15 giây)."""
    het = time.time() + n.a.cho_thu_quy * 60
    while time.time() < het:
        c = dx(n, "ketoancp", "GET", "/api/trips/%s/chi-ke-toan?cap_nhat=1" % n.do[k]["id"])
        if c.get("status") == "da_chi":
            return True
        print("      … chờ thủ quỹ ghi sổ phiếu chi %s bên kế toán (%s)" % (c.get("document_no"), c.get("status")))
        time.sleep(15)
    return False


def doi_trang_thai(k, tt):
    """Bãi bấm xuất phát / xe tới. Bị chặn ĐÚNG LUẬT (chưa nhận tạm ứng) → đợi thủ quỹ (--cho-thu-quy) hoặc Sếp bấm thay."""
    def f(n):
        d, tid = DO[k], n.do[k]["id"]
        body = {"status": tt}
        if tt == "arrived":
            body.update({"back_date": n.ngay, "weight_dest": d["can_ve"]})
            xe = n.dm["xe"][d["xe"]]
            tuyen = n.dm["gom" if d["tuyen"] == TUYEN_GOM else "giao"]
            body["odo_back"] = round((xe.get("odometer_km") or 100000) + 2 * (tuyen.get("total_km") or 100))
            if d["kind"] == "gom":
                body["weight_origin"] = d["can_mo"]
            if d.get("pod"):
                body.update({"pod_no": "POD-%s" % n.do[k]["doc_no"].split("/")[0], "pod_receiver": "ທ້າວ ສົມຊາຍ (cảng)"})
        s, g, _ = n.dx.tho("POST", "/api/trips/%s/transport-status" % tid, body, "thabok")
        ma = ((g or {}).get("detail") or {}).get("ma") if isinstance((g or {}).get("detail"), dict) else None
        if s == 409 and ma == "CHUA_NHAN_TAM_UNG":
            if n.a.cho_thu_quy and _doi_thu_quy(n, k):
                dx(n, "thabok", "POST", "/api/trips/%s/transport-status" % tid, body)
            else:
                dx(n, "admin", "POST", "/api/trips/%s/transport-status" % tid, body)
                cau = "%s %s: Bãi bị chặn đúng luật (phiếu chi tạm ứng chưa ghi sổ bên kế toán — bấm tay) → Sếp bấm thay" % (
                    n.do[k]["doc_no"], "xuất phát" if tt == "transit" else "xe tới")
                n.ghi_chu.append("THAY VAI · " + cau)
                print("      ! THAY VAI — " + cau)
                return
        elif s != 200:
            raise Hong("thabok", "POST", "/api/trips/%s/transport-status" % tid, s, g)
        print("      %s (Bãi)" % ("xuất phát" if tt == "transit" else "xe tới — %s" % ("hàng vào kho bãi" if d["kind"] == "gom" else "chốt hao hụt")))
    return f


def do_doc_duong(k):
    def f(n):
        ma, lit, gia = DO[k]["do_doc_duong"]
        tk = DO[k]["tk_tai_xe"]
        p = dx(n, tk, "POST", "/api/trips/%s/bao-nhien-lieu" % n.do[k]["id"], {"qty_l": lit, "place_id": n.dm["diem"][ma]["id"],
                                                                             "currency": "VND", "note": "Đổ chiều về (gieo bộ sạch)"})
        e = [x for x in p.get("events") or [] if x["kind"] == "refuel" and x.get("status") == "reported"]
        can(e, "không thấy khai đổ vừa gửi")
        n.do[k]["khai_do"] = e[-1]["id"]
        print("      %s khai đổ %s L ở %s" % (tk, lit, ma))
    return f


def duyet_do_ghi_no(k):
    def f(n):
        ma, lit, gia = DO[k]["do_doc_duong"]
        tid = n.do[k]["id"]
        dx(n, "khonl", "POST", "/api/trips/%s/events/%s/duyet" % (tid, n.do[k]["khai_do"]),
           {"qty_l": lit, "unit_price": gia, "currency": "VND", "ghi_no": "1"})
        dx(n, "khonl", "POST", "/api/trips/%s/sections/fuel/verify" % tid)
        dx(n, "khonl", "POST", "/api/trips/%s/sections/fuel/book" % tid)
        print("      duyệt: trạm cho ghi nợ (Có 4021, nhà cung cấp của trạm) · %s VND/L · mục III kiểm + ghi sổ lại" % "{:,}".format(gia))
    return f


def khoa(k):
    def f(n):
        p = dx(n, "ketoan", "POST", "/api/trips/%s/khoa" % n.do[k]["id"], {"xac_nhan": True})
        cb = [c.get("ma") for c in p.get("canh_bao") or []]
        print("      đã khoá%s" % ((" — cảnh báo đã xác nhận: " + ", ".join(cb)) if cb else ""))
    return f


def tao_so(k):
    def f(n):
        g = dx(n, "ketoan", "POST", "/api/trips/%s/tao-so" % n.do[k]["id"])
        so = (g.get("trang_thai") or {}).get("order_code")
        nl = ((g.get("nhien_lieu") or {}).get("trang_thai") or {}).get("order_code") if g.get("nhien_lieu") else None
        can(so, "không có số SO cước")
        if DO[k].get("gia_ban"):
            can(nl, "xe thuê có xuất bán mà không có SO nhiên liệu")
        print("      SO cước %s%s" % (so, (" · SO nhiên liệu %s" % nl) if nl else ""))
    return f


def but_toan(k):
    def f(n):
        tid = n.do[k]["id"]
        ds = dx(n, "ketoan", "GET", "/api/but-toan-cho?trip_id=%s" % tid)["ds"]
        if n.dm.get("gui_bt") and any(b["status"] == "cho_gui" or b.get("can_dao") for b in ds):
            dx(n, "ketoan", "POST", "/api/but-toan-cho/gui-het")
            ds = dx(n, "ketoan", "GET", "/api/but-toan-cho?trip_id=%s" % tid)["ds"]
        if n.dm.get("gui_bt"):
            hong = [b for b in ds if b["status"] == "cho_gui"]
            can(not hong, "bút toán chưa sang kế toán: %s" % "; ".join("%s: %s" % (b["nguon"], b.get("loi_gui") or b.get("error_code"))
                                                                    for b in hong))
        print("      " + (" · ".join("%s %s %s" % (b["nguon"], b["status"], b.get("so_ben_ke_toan") or "") for b in ds if b["status"] != "huy")
                          or "không có bút toán"))
    return f


# ---------------------------------------------------------------- kế hoạch
def ke_hoach():
    """[(mã bước, vai, việc, hàm)] — thứ tự chạy. Vai ghi đúng người làm theo bảng Nhiệm Vụ; "thabok→admin" = Bãi trước, bị chặn
    đúng luật tạm ứng thì Sếp bấm thay (hoặc đợi thủ quỹ với --cho-thu-quy)."""
    K = [("0.1", "—", "kiểm hai máy đang nối DB bản sao (…_d<số>)", b_kiem_may),
         ("0.2", "—", "đăng nhập mọi vai ở trang điều xe và kho tạm (mật khẩu 1234)", b_dang_nhap),
         ("0.3", "admin", "máy sạch (chưa có phiếu) · cờ gửi bút toán", b_may_sach),
         ("0.4", "admin", "đọc danh mục: xe, tài xế, khách, tuyến, điểm dầu, phụ tùng", b_danh_muc),
         ("0.5", "khonl", "kho tạm: nhập dầu KHO-TB 2.000 L × 26.500 · KHO-XE-VN 1.000 L × 27.000 (phiếu nhập PNK_NL)", b_nhap_dau),
         ("0.6", "khopt", "kho tạm: nhập phụ tùng — lốp 12R22.5 × 4, bầu hơi × 4 (thủ kho chỉ ghi số lượng)", b_nhap_pt),
         ("0.7", "ketoancp", "kho tạm: gõ giá các dòng nhập phụ tùng chờ giá (lốp 3.200.000 · bầu hơi 520.000)", b_gia_pt)]

    def chuyen(k, viec):
        return [("%s.%d" % (k, i), v, t, f) for i, (v, t, f) in enumerate(viec, 1)]

    K += chuyen("A", [
        ("thabok", "lập DO-A gom ກາສີ→ທ່າບົກ, xe 341 / DRV-01: cân mỏ 40 t · dầu kho TB 120 L · mục IV: ăn, điện thoại, cầu, đỗ xe "
                   "(tiền mặt) + tiền nước, tiền chuyến (cùng lương)", lap("A")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("A")),
        ("ketoan", "nhập số / ngày phiếu quặng · kiểm mục I, II (giá cước theo bảng giá hợp đồng)", kiem_i_ii("A")),
        ("thabok", "in phiếu đề nghị xuất kho nhiên liệu", de_nghi_xuat_dau("A")),
        ("khotb", "cấp dầu ở kho Thà Bốc theo phiếu đề nghị", cap_dau("A")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_ghi_so_iii("A")),
        ("ketoancp", "nhập đơn giá mục IV · kiểm · ghi sổ → phiếu chi tạm ứng NHIỀU DÒNG sang hệ anh Tune", kiem_ghi_so_iv("A")),
        ("thabok→admin", "xuất phát", doi_trang_thai("A", "transit")),
        ("tx01", "tài xế khai đổ dọc đường 40 L ở trạm VN-01", do_doc_duong("A")),
        ("khonl", "duyệt khai đổ: trạm cho ghi nợ, 27.000 VND/L → mục III mở lại · kiểm + ghi sổ lại", duyet_do_ghi_no("A")),
        ("thabok→admin", "xe về tới bãi: cân bãi 39,6 t, km về → hàng vào kho bãi (kho tạm)", doi_trang_thai("A", "arrived")),
        ("ketoan", "khoá phiếu → bút toán xuất kho nội bộ 625/1371 + ghi nợ NCC trạm VN-01 625/4021", khoa("A")),
        ("ketoan", "Tạo SO bên kế toán (SO cước)", tao_so("A")),
        ("ketoan", "bút toán của phiếu đã sang kế toán (còn chờ thì Gửi hết)", but_toan("A"))])
    K += chuyen("B", [
        ("thabok", "lập DO-B giao ທ່າບົກ→ທ່າເຮືອກະລໍ, xe 342 / DRV-02: lấy lô của DO-A · dầu kho TB 100 L + kho xe VN 300 L · mục IV: ăn, "
                   "điện thoại, sang VN (tiền mặt) + tiền nước, tiền chuyến (cùng lương) · cao tốc tự thêm theo tuyến", lap("B")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("B")),
        ("ketoan", "số phiếu quặng · kiểm mục I, II", kiem_i_ii("B")),
        ("thabok", "in phiếu đề nghị xuất kho nhiên liệu (hai kho)", de_nghi_xuat_dau("B")),
        ("khotb·khonl", "cấp dầu: thủ kho Thà Bốc 100 L · KT kho xăng dầu 300 L ở kho xe VN", cap_dau("B")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_ghi_so_iii("B")),
        ("ketoancp", "đơn giá mục IV · kiểm · ghi sổ → phiếu chi tạm ứng", kiem_ghi_so_iv("B")),
        ("thabok→admin", "xuất phát", doi_trang_thai("B", "transit")),
        ("totsua", "khai sửa xe: thay 1 lốp lấy kho phụ tùng (kho tạm trừ tồn, PXK_PT)", sua_xe_pt("B")),
        ("ketoancp", "kiểm + ghi sổ mục V", kiem_ghi_so_v("B")),
        ("thabok→admin", "xe tới cảng: cân 39,4 t · số POD · người nhận", doi_trang_thai("B", "arrived")),
        ("ketoan", "khoá phiếu → bút toán xuất nội bộ (dầu hai kho 625/1371, phụ tùng 614/1371)", khoa("B")),
        ("ketoan", "Tạo SO bên kế toán (SO cước)", tao_so("B")),
        ("ketoan", "bút toán đã sang kế toán", but_toan("B"))])
    K += chuyen("C", [
        ("thabok", "lập DO-C gom, xe thuê ຮ່ວມ-07 (ທ້າວ ຄຳຫລ້າ) / DRV-LK-01: cân mỏ 38 t · dầu kho TB 150 L (xuất bán) · mục IV: ăn, "
                   "điện thoại (EPL ứng tiền mặt)", lap("C")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("C")),
        ("ketoan", "số phiếu quặng · kiểm mục I, II (giá cước + giá thuê theo bảng giá, hợp đồng thuê)", kiem_i_ii("C")),
        ("thabok", "in phiếu đề nghị xuất kho nhiên liệu", de_nghi_xuat_dau("C")),
        ("khotb", "cấp dầu ở kho Thà Bốc", cap_dau("C")),
        ("khonl", "gõ giá bán dầu cho đối tác 33.000 LAK/L · kiểm + ghi sổ mục III", kiem_ghi_so_iii("C", GIA_BAN_DAU)),
        ("ketoancp", "đơn giá mục IV · kiểm · ghi sổ → phiếu chi tạm ứng (ghi công nợ chủ xe)", kiem_ghi_so_iv("C")),
        ("thabok→admin", "xuất phát", doi_trang_thai("C", "transit")),
        ("thabok→admin", "xe về tới bãi: cân bãi 37,8 t", doi_trang_thai("C", "arrived")),
        ("ketoan", "khoá phiếu → bút toán thuê xe 621/4022 + giá vốn xuất bán 607/1371", khoa("C")),
        ("ketoan", "Tạo SO bên kế toán: SO cước + SO NHIÊN LIỆU cho đối tác (cùng nút)", tao_so("C")),
        ("ketoan", "bút toán đã sang kế toán — KHÔNG lập đề nghị trả (chủ dự án bấm Tất toán đối tác)", but_toan("C"))])
    K += chuyen("D", [
        ("thabok", "lập DO-D gom, xe thuê ຮ່ວມ-08 / DRV-LK-02: cân mỏ 40 t · dầu mua ở trạm LA-02 200 L CHỦ XE TỰ TRẢ · tiền ăn chủ xe "
                   "tự trả (không ứng, không dầu kho)", lap("D")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("D")),
        ("ketoan", "số phiếu quặng · kiểm mục I, II", kiem_i_ii("D")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_ghi_so_iii("D")),
        ("ketoancp", "kiểm + ghi sổ mục IV (không có tạm ứng)", kiem_ghi_so_iv("D")),
        ("thabok", "xuất phát (không tạm ứng → không bị chặn)", doi_trang_thai("D", "transit")),
        ("thabok", "xe về tới bãi: cân bãi 39,8 t", doi_trang_thai("D", "arrived")),
        ("ketoan", "khoá phiếu → bút toán thuê xe 621/4022", khoa("D")),
        ("ketoan", "Tạo SO bên kế toán (SO cước) — để chờ tất toán đối tác (trả đủ tiền thuê − phí)", tao_so("D")),
        ("ketoan", "bút toán đã sang kế toán", but_toan("D"))])
    K += chuyen("E", [
        ("thabok", "lập DO-E gom, xe 343 / DRV-03: dầu kho TB 100 L · ăn, điện thoại, tiền nước, tiền chuyến — CHƯA DUYỆT GÌ (test tay)",
         lap("E"))])
    K += chuyen("F", [
        ("thabok", "lập DO-F gom, xe 344 / DRV-04: dầu kho TB 100 L · tiền nước, tiền chuyến (cùng lương — không tạm ứng)", lap("F")),
        ("thabok", "gửi kiểm mục I, II, III, IV", gui_kiem("F")),
        ("ketoan", "số phiếu quặng · kiểm mục I, II", kiem_i_ii("F")),
        ("thabok", "in phiếu đề nghị xuất kho nhiên liệu", de_nghi_xuat_dau("F")),
        ("khotb", "cấp dầu ở kho Thà Bốc", cap_dau("F")),
        ("khonl", "kiểm + ghi sổ mục III", kiem_ghi_so_iii("F")),
        ("ketoancp", "đơn giá mục IV · kiểm · ghi sổ (không có phiếu chi tạm ứng)", kiem_ghi_so_iv("F")),
        ("thabok", "xuất phát → DO đang trên đường", doi_trang_thai("F", "transit"))])
    return K


# ---------------------------------------------------------------- bảng cuối
def bang_cuoi(n):
    if not n.do:
        return
    print("\n" + "=" * 132)
    print("BẢNG BỘ CHUYẾN — máy %s · kỳ %s" % (n.a.dx, n.ky))
    print("%-3s %-16s %-6s %-26s %-20s %-36s %-18s" % ("DO", "Số phiếu", "Loại", "Trạng thái", "SO cước", "Tạm ứng PTU → phiếu chi", "SO nhiên liệu"))
    for k, x in n.do.items():
        try:
            p = phieu(n, k)
            vs = [v for v in dx(n, "admin", "GET", "/api/trips/%s/vouchers" % x["id"]) if v["kind"] == "advance" and v["status"] != "huy"]
            so = (p.get("so_ke_toan") or {}).get("order_code") or "—"
            ct = p.get("chi_tam_ung") or {}
            tu = ("%s → %s (%s)" % (vs[0]["doc_no"], ct.get("document_no") or "—", ct.get("status") or "chưa gửi")) if vs else "—"
            nl = "—"
            if p.get("company") == "joint":
                ts = dx(n, "admin", "GET", "/api/trips/%s/tao-so" % x["id"]).get("nhien_lieu") or {}
                nl = ((ts.get("trang_thai") or {}).get("order_code")) or ("chưa tạo" if ts.get("can") else "không có")
            tt = "%s%s · %s" % (p["transport_status"], " · KHOÁ" if p.get("locked") else "",
                                "".join({"wait": "○", "entered": "◐", "verified": "◑", "booked": "●", "paid": "✓"}.get(p["sections"].get(m), "?")
                                        for m in ("info", "trans", "fuel", "travel", "repair", "other")))
            print("%-3s %-16s %-6s %-26s %-20s %-36s %-18s" % (k, p["doc_no"], ("thuê " if p.get("company") == "joint" else "nhà ") + p["kind"],
                                                             tt, so, tu, nl))
            bt = [b for b in (p.get("but_toan_cho") or []) if b["status"] != "huy"]
            if bt:
                print("      bút toán: " + " · ".join("%s %s %s" % (b["nguon"], b["status"], b.get("so_ben_ke_toan") or "") for b in bt))
        except Hong as e:
            print("%-3s %-16s (không đọc được: %s)" % (k, x.get("doc_no"), e))
    print("      mục I II III IV V VI: ○ chờ · ◐ đã gửi kiểm · ◑ đã kiểm · ● đã ghi sổ · ✓ đã chi")
    try:
        if any(k in n.do for k in ("C", "D")):
            b = dx(n, "ketoan", "GET", "/api/tat-toan-doi-tac?ky=%s&owner_id=%s&cap_nhat=1" % (n.ky, CHU_XE))
            for d in b.get("doi_tac") or []:
                print("\nTẤT TOÁN ĐỐI TÁC (chưa lập đề nghị — chủ dự án bấm): %s %s · tiền thuê %s · phí %s · tạm ứng %s · nợ NCC %s · "
                      "SO nhiên liệu còn nợ %s · CÒN TRẢ %s %s · trạng thái %s" % (
                          d["ten"], d["ma_ke_toan"], d["tien_thue"], d["phi"], d["tam_ung"], d["no_ncc"], d["nhien_lieu_con_no"],
                          d["con_tra"], d["tien_te"], d["trang_thai"]))
                print("      TCX / TKN: %s" % (", ".join("%s (%s)" % (r["so"], r["trang_thai"]) for r in d.get("de_nghi") or []) or "chưa có"))
            for c in b.get("chi_tiet") or []:
                print("      %s · thuê %s − phí %s − ứng %s · cấn trừ SO nhiên liệu %s (%s) → còn trả %s %s" % (
                    c["doc_no"], c["tien_thue"], c["phi"], c["tam_ung"]["tien"], c.get("can_tru"), (c["nhien_lieu"] or {}).get("order_code") or "—",
                    c["con_tra"], c["tien_te"]))
        for k in ("A", "B"):
            if k in n.do:
                p = phieu(n, k)
                t = dx(n, "ketoancp", "GET", "/api/tat-toan/%s?ky=%s" % (p["driver_id"], n.ky))
                x = next((y for y in t.get("phieu") or [] if y["trip_id"] == n.do[k]["id"]), {})
                print("TẤT TOÁN TÀI XẾ %s (để nguyên — bấm tay): %s · đã ứng %s · đã chi thật %s · chênh %s (%d dòng)" % (
                    p.get("driver_name"), p["doc_no"], x.get("da_ung_lak"), x.get("da_chi_that_lak"), x.get("chenh_lak"), len(x.get("dong") or [])))
    except Hong as e:
        print("  (không đọc được tất toán: %s)" % e)
    for c in n.ghi_chu:
        print("  ! " + c)


def main():
    ap = argparse.ArgumentParser(description="Gieo bộ dữ liệu sạch cho máy thử (đi HTTP, đúng vai).")
    ap.add_argument("--chi-in", action="store_true", help="in kế hoạch, không gọi máy nào")
    ap.add_argument("--dx", default=os.getenv("EPL_DX", "http://127.0.0.1:8011"))
    ap.add_argument("--kt", default=os.getenv("EPL_KT", "http://127.0.0.1:8031"))
    ap.add_argument("--ngay", default=dt.date.today().isoformat())
    ap.add_argument("--cho-thu-quy", type=float, default=0, metavar="PHUT",
                    help="đợi tối đa PHUT phút ở bước xuất phát / xe tới cho thủ quỹ ghi sổ phiếu chi tạm ứng bên Web anh Tune")
    ap.add_argument("--khong-can-sach", action="store_true", help="cho chạy khi máy còn phiếu")
    a = ap.parse_args()
    dt.date.fromisoformat(a.ngay)
    K = ke_hoach()
    if a.chi_in:
        print("KẾ HOẠCH GIEO — %d bước (không gọi máy nào). Máy: điều xe %s · kho tạm %s · ngày %s" % (len(K), a.dx, a.kt, a.ngay))
        khoi = None
        for ma, vai, viec, _ in K:
            k = ma.split(".")[0]
            if k != khoi:
                khoi = k
                print("\n%s" % ("0  CHUẨN BỊ (kho tạm, danh mục)" if k == "0" else "%s  %s" % (k, DO[k]["ten"])))
            ten = " / ".join(TEN_VAI.get(v, v) for v in re.split(r"[·→]", vai))
            print("  %-5s %-14s %-34s %s" % (ma, vai, "(" + ten + ")", viec))
        print("\n«thabok→admin»: Bãi bấm trước; bị chặn ĐÚNG LUẬT vì phiếu chi tạm ứng chưa ghi sổ bên anh Tune (bước bấm tay) thì Sếp bấm thay"
              " và in «THAY VAI» — hoặc chạy với --cho-thu-quy PHUT để đợi người thử ghi sổ.")
        return
    n = Ngu(a)
    try:
        for ma, vai, viec, ham in K:
            print("· %-5s [%s] %s" % (ma, vai, viec))
            sys.stdout.flush()
            try:
                ham(n)
            except Hong as e:
                print("\nDỪNG ở bước %s — vai %s (%s) — %s" % (ma, e.vai if e.vai != "—" else vai, TEN_VAI.get(e.vai if e.vai != "—" else vai, vai), viec))
                print("      %s → HTTP %s · mã %s\n      %s" % (e.duong, e.http, e.ma or "—", e.loi))
                raise SystemExit(1)
            except (urllib.error.URLError, OSError) as e:
                print("\nDỪNG ở bước %s — vai %s — %s\n      không gọi được máy: %s" % (ma, vai, viec, e))
                raise SystemExit(1)
        print("\nXONG — gieo đủ %d bước." % len(K))
    finally:
        try:
            bang_cuoi(n)
        except Exception as e:                                  # noqa: BLE001 — bảng cuối hỏng không che lỗi chính
            print("  (không in được bảng cuối: %s)" % e)


if __name__ == "__main__":
    main()
