# -*- coding: utf-8 -*-
"""Thử KHÔNG CÒN ĐẨY CHỨNG TỪ sang trang kế toán tạm (01/10) + cấu hình KHO riêng vẫn nối được kho tạm.

    python kiem/thu_day_ke_toan.py [http://127.0.0.1:8011]

Chủ dự án chốt 01/10: trang kế toán tạm (EPL_KETOAN) bỏ phần tiền, chỉ còn làm KHO TẠM; việc tiền đi qua hệ anh Tune.
Trước đây bài này dựng máy nhận giả đóng vai API kế toán và thử đẩy — nay đổi thành thử "không còn đẩy":

  A. Trong tiến trình (không mạng, không DB — DB giả trong bộ nhớ): `day_hang_loat` (còn giữ cho công cụ gieo mẫu) không
     gọi ra ngoài, trả đúng kiểu cũ; `day_mot` / `trang_thai` đã xoá (dọn dẹp 01/10); mã nguồn backend không còn lời gọi
     `/api/v1/epl-lao/vouchers`. Cấu hình kho:
     khoá mới `kho_api` / `kho_token` / `kho_web`, chưa từng lưu thì đọc khoá cũ `ke_toan_*`; đã lưu (kể cả để trống) thì
     không đọc khoá cũ nữa; `dat_kho` không đụng khoá cũ.
  B. Qua máy chủ đang chạy: `/api/ke-toan/trang-thai` và đường đẩy một tờ đã xoá (404); đường "Đẩy hết" còn trả tóm tắt
     rỗng, đúng quyền như cũ; tờ giữ nguyên; trang kế toán tạm không nhận thêm tờ nào. Cấu hình kho đọc được ở
     cả đường mới `/api/kho-tam/cau-hinh` lẫn đường cũ, không lộ khoá. Kho tạm vẫn nối: Kiểm kết nối, địa chỉ mở, Xem
     kho có giá dầu.

Bài KHÔNG đổi cấu hình trên DB (DB bản sao dùng chung với máy thử khác) — PUT chỉ gửi thân rỗng.
Địa chỉ kho tạm để đối chiếu: biến EPL_KT (mặc định 8031) — xem kiem/_ke_toan.py.
"""
import ast
import glob
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011").rstrip("/")
DU_AN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(DU_AN, "backend", "app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ke_toan as K       # noqa: E402 — kho tạm (EPL_KETOAN)

TOKEN = {}
DEM = {"dat": 0}


def phai(dung, buoc):
    DEM["dat"] += 1
    print("%s %s" % ("  ✓" if dung else "  SAI", buoc))
    if not dung:
        raise SystemExit("DỪNG: " + buoc)


# ================================================================ A. trong tiến trình
def phan_a():
    print("A. Trong tiến trình — không mạng, DB giả")
    # Không bao giờ chạm DB thật: địa chỉ DB giả (engine chỉ dựng, không nối), khoá cấu hình qua biến môi trường để trống
    # (load_dotenv không ghi đè biến đã có).
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://kiem@127.0.0.1:1/khong_co"
    for k in ("KHO_API", "KHO_TOKEN", "KHO_WEB", "KE_TOAN_API", "KE_TOAN_TOKEN", "KE_TOAN_WEB"):
        os.environ["EPL_" + k] = ""
    sys.path.insert(0, APP)
    from models import CauHinh
    from services import day_ke_toan as DK
    from services import goi_ke_toan as KT
    from services import kho_ke_toan as KK
    from services import mang as MANG

    ra_ngoai = []

    def chan(*a, **k):
        ra_ngoai.append(a[0] if a else k)
        raise AssertionError("có lời gọi mạng đi ra")
    goc_mo = urllib.request.urlopen, MANG.mo
    urllib.request.urlopen, MANG.mo = chan, chan
    try:
        _phan_a(DK, KT, KK, CauHinh, ra_ngoai)
    finally:
        urllib.request.urlopen, MANG.mo = goc_mo          # phần B cần mạng thật


def _phan_a(DK, KT, KK, CauHinh, ra_ngoai):
    phai(not hasattr(DK, "day_mot") and not hasattr(DK, "trang_thai"), "day_mot / trang_thai đã xoá (không còn ai gọi)")
    k = DK.day_hang_loat(None)
    phai(all(k[x] == 0 for x in ("thu", "xong", "loi")) and k["chi_tiet_loi"] == [], "day_hang_loat trả tóm tắt rỗng đúng kiểu cũ")
    phai(not ra_ngoai, "không có lời gọi mạng nào đi ra")

    # mã nguồn: đường nhận phong bì của trang tạm chỉ còn nhắc trong chú thích đầu tệp day_ke_toan.py
    dung = []
    for f in glob.glob(os.path.join(APP, "**", "*.py"), recursive=True):
        s = io.open(f, encoding="utf-8").read()
        if "epl-lao/vouchers" not in s:
            continue
        cay = ast.parse(s)
        chu_thich = ast.get_docstring(cay) or ""
        if s.count("epl-lao/vouchers") > chu_thich.count("epl-lao/vouchers"):
            dung.append(os.path.relpath(f, DU_AN))
    phai(not dung, "backend không còn mã nào gọi /api/v1/epl-lao/vouchers %s" % (dung or ""))
    s = io.open(os.path.join(APP, "services", "day_ke_toan.py"), encoding="utf-8").read()
    phai("urllib" not in s and "MANG" not in s, "services/day_ke_toan.py không còn mở kết nối nào")

    # cấu hình kho: khoá mới · khoá cũ
    class DbGia:
        def __init__(self, **dong):
            self.dong = {k: CauHinh(khoa=k, gia_tri=v) for k, v in dong.items()}
            self.info = {}

        def get(self, _lop, k):
            return self.dong.get(k)

        def add(self, r):
            self.dong[r.khoa] = r

    cu = dict(ke_toan_api="http://kho-cu:8030/", ke_toan_token="khoa-cu", ke_toan_web="http://web-cu:8030")
    db = DbGia(**cu)
    phai(KT.cau_hinh(db) == ("http://kho-cu:8030", "khoa-cu") and KK.web_ke_toan(db) == "http://web-cu:8030",
         "chỉ có khoá cũ (máy 8020 hiện nay) → kho vẫn đọc khoá cũ")
    db = DbGia(kho_api="http://kho-moi:8031", **cu)
    phai(KT.cau_hinh(db) == ("http://kho-moi:8031", "khoa-cu"), "đặt kho_api → địa chỉ mới; kho_token chưa lưu → vẫn khoá cũ")
    db = DbGia(kho_api="http://kho-moi:8031", kho_token="", **cu)
    phai(KT.cau_hinh(db)[1] == "", "kho_token đã lưu RỖNG (Sếp xoá) → khoá cũ không sống lại")
    try:
        KT.goi(db, "GET", "/api/lien-thong/kiem")
        phai(False, "thiếu khoá kho phải chặn")
    except Exception as e:  # noqa: BLE001
        phai(getattr(e, "status_code", None) == 503 and e.detail["ma"] == "CHUA_NOI_KE_TOAN" and not ra_ngoai,
             "thiếu khoá kho → 503 CHUA_NOI_KE_TOAN, không gọi ra ngoài")
    db = DbGia(kho_api="http://kho-moi:8031", kho_web="", ke_toan_api="http://kho-cu:8030")
    phai(KK.web_ke_toan(db) == "http://kho-moi:8031", "kho_web để trống → địa chỉ mở là kho_api (như ke_toan_web trước đây)")
    os.environ["EPL_KHO_API"] = "http://kho-env:8031"
    db = DbGia(**cu)
    phai(KT.cau_hinh(db)[0] == "http://kho-env:8031", "biến EPL_KHO_API thắng khoá cũ")
    os.environ["EPL_KHO_API"] = ""
    db = DbGia(**cu)
    KT.dat_kho(db, "api", "http://kho-moi:8031")
    KT.dat_kho(db, "token", "")
    phai({k: db.dong[k].gia_tri for k in cu} == cu and db.dong["kho_api"].gia_tri == "http://kho-moi:8031",
         "dat_kho ghi khoá mới, KHÔNG đụng khoá cũ (quay về mã cũ vẫn chạy)")
    phai(KT.cau_hinh(db) == ("http://kho-moi:8031", ""), "đọc lại sau khi lưu trong cùng phiên → số mới (bộ nhớ phiên được xoá)")

    # đường PUT cấu hình: giao diện cũ gửi tên cũ ke_toan_* → ghi vào khoá kho mới; tên mới thắng nếu gửi cả hai
    from routes import chung_tu as RCT
    DbGia.commit = lambda self: None
    db = DbGia(**cu)
    g = RCT.dat_cau_hinh({"ke_toan_api": "http://kho-moi:8031", "ke_toan_web": "", "ke_toan_token": ""}, db=db, user=None)
    phai(db.dong["kho_api"].gia_tri == "http://kho-moi:8031" and db.dong["kho_web"].gia_tri == "" and "kho_token" not in db.dong
         and {k: db.dong[k].gia_tri for k in cu} == cu,
         "PUT tên cũ (màn Tài khoản hiện nay) → ghi kho_api / kho_web, khoá rỗng = giữ, khoá cũ không đụng")
    phai(g["kho_api"] == g["ke_toan_api"] == "http://kho-moi:8031" and g["co_token_kho"] is True and g["co_token"] is True
         and not any(k in g for k in ("kho_token", "ke_toan_token")), "trả cả tên mới lẫn tên cũ, không lộ khoá")
    g = RCT.dat_cau_hinh({"kho_token": "-"}, db=db, user=None)
    phai(db.dong["kho_token"].gia_tri == "" and g["co_token_kho"] is False, "PUT kho_token \"-\" → xoá khoá kho (khoá cũ không sống lại)")
    RCT.dat_cau_hinh({"kho_api": "http://moi:1", "ke_toan_api": "http://cu:1"}, db=db, user=None)
    phai(db.dong["kho_api"].gia_tri == "http://moi:1", "gửi cả tên mới lẫn tên cũ → tên mới thắng")


# ================================================================ B. qua máy chủ
def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau, method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=120) as t:
            return t.status, json.loads(t.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, {}


def phan_b():
    print("B. Qua máy chủ %s (kho tạm đối chiếu: %s)" % (GOC, K.KT))
    for u in ("thabok", "ketoan", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TOKEN[u] = g["token"]

    s, tt = goi("/api/ke-toan/trang-thai", vai="ketoan")
    phai(s == 404, "đường trạng thái đẩy đã xoá → 404 (giao diện không còn nút Đẩy)")

    s, ds = goi("/api/chung-tu?chua_day=1&limit=1", vai="ketoan")
    to = (ds.get("ds") or [None])[0] if s == 200 else None
    truoc_kt = None
    if to:
        s, kt = K.kt("/api/chung-tu?limit=1000&q=" + urllib.parse.quote(to["so"]), vai="ketoan")
        truoc_kt = sorted(json.dumps(v, sort_keys=True) for v in (kt or []) if v.get("source") == "EPL_LAO" and v.get("ref") == to["so"])

    s, g = goi("/api/chung-tu/day", {}, vai="thabok")
    phai(s == 403, "Bãi bấm Đẩy hết → 403 như cũ")
    s, g = goi("/api/chung-tu/day", {}, vai="ketoan")
    phai(s == 200 and g["thu"] == g["xong"] == g["loi"] == 0 and g.get("khong_day_nua") is True,
         "Đẩy hết → 200 tóm tắt rỗng (không đẩy tờ nào)")
    if to:
        s, g = goi("/api/chung-tu/%s/day" % to["id"], {}, vai="ketoan")
        phai(s == 404, "Đẩy một tờ (%s) → 404, đường đã xoá" % to["so"])
        s, sau = goi("/api/chung-tu/%s" % to["id"], vai="ketoan")
        phai(all(sau[k] == to[k] for k in ("da_day", "lan_thu", "loi_day", "day_luc", "ma_ben_ke_toan")), "tờ giữ nguyên sau khi bấm đẩy")
        s, kt = K.kt("/api/chung-tu?limit=1000&q=" + urllib.parse.quote(to["so"]), vai="ketoan")
        sau_kt = sorted(json.dumps(v, sort_keys=True) for v in (kt or []) if v.get("source") == "EPL_LAO" and v.get("ref") == to["so"])
        phai(s == 200 and sau_kt == truoc_kt, "kho tạm không nhận thêm / không đổi tờ %s nào từ trang điều xe" % to["so"])
    else:
        print("  · không còn tờ chưa đánh dấu — bỏ qua phần đẩy một tờ")

    s, moi = goi("/api/kho-tam/cau-hinh", vai="admin")
    s2, cu = goi("/api/ke-toan/cau-hinh", vai="admin")
    phai(s == s2 == 200 and moi == cu, "cấu hình đọc được ở đường mới /api/kho-tam/cau-hinh lẫn đường cũ")
    phai(moi["kho_api"] == moi["ke_toan_api"] and moi["kho_web"] == moi["ke_toan_web"] and moi["co_token_kho"] == moi["co_token"],
         "tên mới kho_* và tên cũ ke_toan_* trả cùng số (giao diện cũ còn đọc)")
    phai(moi["kho_api"] and moi["co_token_kho"], "máy thử có địa chỉ + khoá kho (đọc từ khoá cũ nếu chưa lưu khoá mới): %s" % moi["kho_api"])
    phai(not any(k in moi for k in ("kho_token", "ke_toan_token")), "khoá kho không ra trình duyệt")
    s, g = goi("/api/kho-tam/cau-hinh", vai="ketoan")
    phai(s == 403, "Kế toán xem cấu hình kho → 403 (chỉ Sếp)")
    s, g = goi("/api/kho-tam/cau-hinh", {}, vai="ketoan", method="PUT")
    phai(s == 403, "Kế toán đặt cấu hình kho → 403")
    s, g = goi("/api/kho-tam/cau-hinh", {}, vai="admin", method="PUT")
    phai(s == 200 and g == moi, "Sếp lưu thân rỗng → 200, cấu hình không đổi")

    s, g = goi("/api/lien-thong/thu", vai="admin")
    phai(s == 200 and g.get("ok") is True, "Kiểm kết nối kho tạm (đây → %s) → nối được, bên kia nhận ra %s" % (g.get("api"), (g.get("ben_kia") or {}).get("nguoi")))
    s, g = goi("/api/lien-thong/dia-chi", vai="thabok")
    phai(s == 200 and g.get("kho_web") == g.get("ke_toan_web") == (moi["kho_web"] or moi["kho_api"]).rstrip("/"),
         "địa chỉ mở kho tạm (nút Cấp phát, QR) = kho_web, trống thì kho_api — trả cả tên mới kho_web lẫn tên cũ ke_toan_web")
    s, g = goi("/api/kho-xem", vai="ketoan")
    dau = (g or {}).get("nhien_lieu") or []
    phai(s == 200 and dau and any(k.get("gia_bq") for k in dau), "Xem kho hỏi kho tạm: %d kho dầu, có giá bình quân" % len(dau))


def main():
    phan_a()
    phan_b()
    print("\nTHỬ KHÔNG CÒN ĐẨY: ĐẠT %d bước — không lời gọi đẩy nào đi ra · đường đẩy cũ đã xoá / trả rỗng · cấu hình kho riêng"
          " (khoá cũ vẫn đọc khi chưa lưu khoá mới) · kho tạm vẫn nối" % DEM["dat"])


if __name__ == "__main__":
    main()
