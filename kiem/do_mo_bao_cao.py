# -*- coding: utf-8 -*-
"""MỞ BÁO CÁO NHƯ NGƯỜI DÙNG — gọi HTTP vào máy chủ đang chạy (không tự bật máy chủ, không xoá bộ đệm), đo thời gian.

    python kiem/do_mo_bao_cao.py [http://127.0.0.1:8012]

DB / cách chạy (ghi 06/10): công cụ ĐO, không phải bộ kiểm đạt / không đạt. Gọi HTTP vào máy chủ ĐANG CHẠY — mặc định 8012 = máy đo
tải trỏ DB epl_lao_tai (kiem/do_tai.py tự bật rồi tắt máy đó; công cụ này KHÔNG tự bật). Chỉ GET, nhưng báo cáo tính xong thì máy
chủ ghi bản lưu vào bảng bao_cao_dem của DB đó. Không trỏ vào 8011 (epl_lao_d7 — đang bấm tay) hay máy thật 8020.
"""
import json
import sys
import time
import urllib.request

GOC = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8012"
tk = json.loads(urllib.request.urlopen(urllib.request.Request(
    GOC + "/api/dang-nhap", data=json.dumps({"username": "admin", "password": "1234"}).encode(),
    headers={"Content-Type": "application/json"}), timeout=60).read())["token"]
nay = time.strftime("%Y-%m")
y, m = int(nay[:4]), int(nay[5:])
truoc = "%04d-%02d" % (y - (m == 1), (m - 2) % 12 + 1)
DS = [("Tổng quan", "/api/bao-cao/tong-quan?thang=%s"), ("Xu hướng", "/api/bao-cao/xu-huong?thang=%s"),
      ("Tiền chuyến tài xế", "/api/bao-cao/tien-tai-xe?thang=%s"), ("Cấn trừ", "/api/bao-cao/can-tru?thang=%s"),
      ("Theo dõi · dòng tổng", "/api/bao-cao/theo-doi/tong?thang=%s"), ("Theo dõi · 1 trang", "/api/bao-cao/theo-doi?thang=%s&trang=1&co=100"),
      ("Nhà cung cấp", "/api/suppliers")]           # Tất toán dời sang trang kế toán (đợt 7c)
print("%-24s %12s %12s" % ("Báo cáo", nay, truoc))
for ten, d in DS:
    kq = []
    for th in (nay, truoc):
        t0 = time.perf_counter()
        urllib.request.urlopen(urllib.request.Request(GOC + (d % th if "%s" in d else d), headers={"Authorization": "Bearer " + tk}), timeout=120).read()
        kq.append(time.perf_counter() - t0)
    print("%-24s %10.2f s %10.2f s" % (ten, kq[0], kq[1]), flush=True)
