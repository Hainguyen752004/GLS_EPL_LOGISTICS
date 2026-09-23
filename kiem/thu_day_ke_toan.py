# -*- coding: utf-8 -*-
"""Thử ĐẨY CHỨNG TỪ sang kế toán — bằng một máy nhận giả đóng vai API anh Khang, chạy ngay trong bộ kiểm.

    python kiem/thu_day_ke_toan.py [http://127.0.0.1:8010]

Máy nhận giả nghe ở cổng 8099, ghi lại từng gói tin nhận được. Bộ kiểm: Sếp đặt địa chỉ API → bấm đẩy
→ gói tin sang đúng dạng hợp đồng → tờ được đánh đã đẩy kèm mã bên kia → máy nhận trả 500 thì tờ giữ
nguyên và ghi lỗi → trả 409 (đã có) thì coi là đã đẩy → chưa cấu hình thì 409 rõ ràng → Bãi không được
bấm đẩy. Cuối cùng trả cấu hình về rỗng để không ảnh hưởng máy thật.
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

GOC = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010").rstrip("/")
CONG_GIA = 8099
TOKEN = {}
NHAN = []                 # gói tin máy giả đã nhận
CHE_DO = {"tra": 201}     # 201 nhận · 500 hỏng · 409 đã có


class MayNhanGia(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        than = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        NHAN.append({"path": self.path, "auth": self.headers.get("Authorization"), "than": than})
        ma = CHE_DO["tra"]
        self.send_response(ma); self.send_header("Content-Type", "application/json"); self.end_headers()
        if ma == 500:
            self.wfile.write(json.dumps({"message": "máy giả cố ý hỏng"}).encode())
        else:
            self.wfile.write(json.dumps({"id": "KT-%04d" % len(NHAN), "status": "accepted"}).encode())


def goi(duong, du_lieu=None, vai=None, method=None):
    dau = {"Content-Type": "application/json"}
    if vai:
        dau["Authorization"] = "Bearer " + TOKEN[vai]
    than = json.dumps(du_lieu).encode() if du_lieu is not None else None
    r = urllib.request.Request(GOC + duong, data=than, headers=dau, method=method or ("POST" if than is not None else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=40) as t:
            return t.status, json.loads(t.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def phai(s, mong, buoc, g=None):
    dt_ = (g or {}).get("detail") if isinstance(g, dict) else None
    ma = dt_.get("ma", "") if isinstance(dt_, dict) else ""
    print("%s %-60s %s %s" % ("  ✓" if s == mong else "  SAI", buoc, s, ma))
    if s != mong:
        raise SystemExit("DỪNG: %s trả %s, mong %s — %s" % (buoc, s, mong, g))


def main():
    for u in ("thabok", "ketoan", "admin"):
        s, g = goi("/api/dang-nhap", {"username": u, "password": "1234"}); TOKEN[u] = g["token"]
    print("✓ đăng nhập 3 vai")

    goc_cau_hinh = _cat_cau_hinh()
    may = HTTPServer(("127.0.0.1", CONG_GIA), MayNhanGia)
    threading.Thread(target=may.serve_forever, daemon=True).start()
    print("✓ máy nhận giả (đóng vai API anh Khang) nghe ở :%d" % CONG_GIA)

    try:
        # 0. chưa cấu hình → đẩy phải báo rõ, không im
        s, g = goi("/api/ke-toan/cau-hinh", {"ke_toan_api": "", "ke_toan_token": "-"}, vai="admin", method="PUT")
        phai(s, 200, "Sếp xoá cấu hình để bắt đầu sạch", g)
        s, g = goi("/api/chung-tu/day", {}, vai="ketoan")
        phai(s, 409, "Đẩy khi CHƯA cấu hình → báo CHUA_CAU_HINH", g)
        s, g = goi("/api/ke-toan/trang-thai", vai="ketoan")
        assert s == 200 and g["cau_hinh"] is False, "trạng thái phải nói chưa nối"

        # 1. Sếp đặt địa chỉ + token; token không được lộ ra
        s, g = goi("/api/ke-toan/cau-hinh", {"ke_toan_api": "http://127.0.0.1:%d" % CONG_GIA, "ke_toan_token": "bi-mat-123"}, vai="admin", method="PUT")
        phai(s, 200, "Sếp đặt địa chỉ API và token", g)
        assert g["co_token"] is True and "bi-mat" not in json.dumps(g), "token không được trả về trình duyệt"
        s, g = goi("/api/ke-toan/cau-hinh", vai="ketoan")
        phai(s, 403, "Kế toán xem cấu hình → bị từ chối (chỉ Sếp)", g)

        # 2. Bãi không được bấm đẩy
        s, g = goi("/api/chung-tu/day", {}, vai="thabok")
        phai(s, 403, "Bãi bấm đẩy → bị từ chối", g)

        # 3. đẩy một tờ chưa đẩy
        s, ds = goi("/api/chung-tu?chua_day=1&limit=5", vai="ketoan")
        assert ds["ds"], "phải còn tờ chưa đẩy để thử (gieo lại DB nếu hết)"
        to = ds["ds"][0]
        s, g = goi("/api/chung-tu/%s/day" % to["id"], {}, vai="ketoan")
        phai(s, 200, "Đẩy một tờ %s" % to["so"], g)
        assert g["da_day"] is True and g["ma_ben_ke_toan"] == "KT-0001", "tờ phải đánh đã đẩy kèm mã bên kia: %s" % g.get("ma_ben_ke_toan")
        gt = NHAN[-1]
        assert gt["path"] == "/api/v1/epl-lao/vouchers", "phải gọi đúng đường hợp đồng: %s" % gt["path"]
        assert gt["auth"] == "Bearer bi-mat-123", "phải gửi token dạng Bearer"
        t = gt["than"]
        for k in ("source", "ref", "type", "group", "date", "party", "amount", "entry", "memo", "lines"):
            assert k in t, "gói tin thiếu trường %s" % k
        assert t["source"] == "EPL_LAO" and t["ref"] == to["so"] and t["type"] == to["loai"], "gói tin phải mang đúng số và loại tờ"
        print("  ✓ gói tin đúng hợp đồng: ref=%s type=%s group=%s amount=%s %s" % (t["ref"], t["type"], t["group"], t["amount"]["value"], t["amount"]["currency"]))

        # 4. máy bên kia hỏng → tờ giữ nguyên, ghi lỗi, đếm lần thử
        CHE_DO["tra"] = 500
        s, ds = goi("/api/chung-tu?chua_day=1&limit=5", vai="ketoan"); to2 = ds["ds"][0]
        s, g = goi("/api/chung-tu/%s/day" % to2["id"], {}, vai="ketoan")
        phai(s, 502, "Bên kia trả 500 → báo DAY_HONG, tờ không bị đánh đã đẩy", g)
        s, g = goi("/api/chung-tu/%s" % to2["id"], vai="ketoan")
        assert g["da_day"] is False and g["loi_day"] and "500" in g["loi_day"] and g["lan_thu"] == 1, "tờ phải giữ chưa đẩy và ghi lỗi: %s" % g
        print("  ✓ tờ %s giữ chưa đẩy, lỗi ghi lại: %s" % (to2["so"], g["loi_day"][:50]))

        # 5. bên kia nói 'đã có rồi' (409) → coi là đã đẩy
        CHE_DO["tra"] = 409
        s, g = goi("/api/chung-tu/%s/day" % to2["id"], {}, vai="ketoan")
        phai(s, 200, "Bên kia trả 409 (đã có) → coi là đã đẩy", g)
        assert g["da_day"] is True and g["loi_day"] is None and g["lan_thu"] == 2, "phải xoá lỗi cũ và tính lần thử thứ 2"

        # 6. đẩy hết
        CHE_DO["tra"] = 201
        truoc = len(NHAN)
        s, g = goi("/api/chung-tu/day", {}, vai="ketoan")
        phai(s, 200, "Đẩy hết tờ chưa đẩy", g)
        assert g["xong"] == g["thu"] and g["loi"] == 0, "đẩy hết phải xong hết: %s" % g
        assert len(NHAN) - truoc == g["xong"], "số gói máy giả nhận phải bằng số tờ đẩy xong"
        s, tt = goi("/api/ke-toan/trang-thai", vai="ketoan")
        assert tt["chua_day"] == 0, "sau đẩy hết phải còn 0 tờ chưa đẩy: %s" % tt
        print("  ✓ đẩy hết %d tờ · máy giả nhận đủ %d gói · còn 0 tờ chưa đẩy" % (g["xong"], len(NHAN) - truoc))

        # 7. đẩy lại một tờ đã đẩy → không gửi lại
        truoc = len(NHAN)
        s, g = goi("/api/chung-tu/%s/day" % to["id"], {}, vai="ketoan")
        phai(s, 200, "Đẩy lại tờ đã đẩy → không gửi trùng", g)
        assert len(NHAN) == truoc, "tờ đã đẩy không được gửi lại"
    finally:
        # trả cấu hình về ĐÚNG NHƯ TRƯỚC (23/09: trước đây trả về rỗng → mất nối 8011 → sổ 8030 mà không ai biết)
        # và mở lại cờ đã đẩy để lần chạy sau còn tờ để thử
        goi("/api/ke-toan/cau-hinh", {"ke_toan_api": "", "ke_toan_token": "-"}, vai="admin", method="PUT")
        _tra_cau_hinh(goc_cau_hinh)
        s, ds = goi("/api/chung-tu?limit=2000", vai="ketoan")
        for c in ds["ds"]:
            if c["da_day"] and (c.get("ma_ben_ke_toan") or "").startswith("KT-"):
                goi("/api/chung-tu/%s/da-day" % c["id"], {"da_day": False}, vai="ketoan")
        may.shutdown()
        print("  · đã xoá cấu hình thử và mở lại các tờ đã đẩy vào máy giả")

    print("\nTHỬ ĐẨY KẾ TOÁN: ĐẠT — cấu hình · gói tin đúng hợp đồng · hỏng thì giữ tờ · 409 coi là xong · đẩy hết · không gửi trùng")


def _cat_cau_hinh():
    """Cất địa chỉ + token đang dùng. Token không bao giờ ra API (đúng thiết kế) nên đọc thẳng DB — bộ kiểm
    chạy trên cùng máy với máy chủ thử. Không in token ra màn hình."""
    try:
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app"))
        from database import SessionLocal
        from services import day_ke_toan as DK
        db = SessionLocal()
        try:
            return {k: DK.cau_hinh(db, k) for k in ("ke_toan_api", "ke_toan_token")}
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001
        print("  · không cất được cấu hình gốc (%s) — sẽ để trống sau bài" % e)
        return None


def _tra_cau_hinh(goc):
    if not goc or not goc.get("ke_toan_api"):
        return
    from database import SessionLocal
    from services import day_ke_toan as DK
    db = SessionLocal()
    try:
        for k, v in goc.items():
            DK.dat_cau_hinh(db, k, v or "", None)
        db.commit()
        print("  · đã trả cấu hình kế toán về như trước: %s (token giữ nguyên)" % goc["ke_toan_api"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
